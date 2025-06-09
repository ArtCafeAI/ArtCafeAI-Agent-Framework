#!/usr/bin/env python3
"""
NATS Agent with NKey Authentication

This agent provides direct NATS connection using NKey authentication,
bypassing the WebSocket layer for better performance.
"""

import asyncio
import json
import logging
import os
import tempfile
from typing import Any, Callable, Dict, Optional, Union
from datetime import datetime, timezone

import nats
from nats.errors import ConnectionClosedError, TimeoutError, NoRespondersError

from ..core.config import AgentConfig

logger = logging.getLogger("AgentFramework.Core.NATSAgent")


class NATSAgent:
    """
    Agent with direct NATS connection using NKey authentication.
    
    This agent connects directly to NATS without going through WebSocket,
    providing lower latency and better performance.
    """
    
    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        nkey_seed: Union[str, bytes],
        nats_url: str = "nats://nats.artcafe.ai:4222",
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        config: Optional[AgentConfig] = None,
        heartbeat_interval: int = 30,
        enable_metrics: bool = True
    ):
        """
        Initialize a NATS agent with NKey authentication.
        
        Args:
            client_id: Client ID from the ArtCafe dashboard
            tenant_id: Tenant/organization ID
            nkey_seed: NKey seed string or path to seed file
            nats_url: NATS server URL
            name: Optional name for the agent
            metadata: Optional metadata dictionary
            config: Optional configuration object
            heartbeat_interval: Seconds between heartbeats (default 30)
            enable_metrics: Enable metrics reporting (default True)
        """
        self.client_id = client_id
        self.agent_id = client_id
        self.agent_type = "nats"
        self.config = config or AgentConfig()
        self.tenant_id = tenant_id
        self.nkey_seed = nkey_seed
        self.nats_url = nats_url
        self.name = name or client_id
        self.metadata = metadata or {}
        self.heartbeat_interval = heartbeat_interval
        self.enable_metrics = enable_metrics
        
        # NATS connection
        self.nc: Optional[nats.NATS] = None
        self._subscriptions = {}
        self._message_handlers = {}
        self._is_connected = False
        self._heartbeat_task = None
        self._metrics_task = None
        
        # Metrics tracking
        self._message_stats = {
            "sent": {},
            "received": {},
            "bytes_sent": 0,
            "bytes_received": 0
        }
        self._metrics_interval = 10  # Report every 10 seconds
        
        logger.info(f"NATS Agent initialized: {client_id}")
    
    async def connect(self):
        """Connect to NATS using NKey authentication."""
        try:
            # Handle NKey seed
            if isinstance(self.nkey_seed, str) and os.path.exists(self.nkey_seed):
                # It's a file path
                nkeys_seed = self.nkey_seed
                temp_file = None
            else:
                # It's the seed string - write to temp file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.nkey') as f:
                    if isinstance(self.nkey_seed, bytes):
                        f.write(self.nkey_seed.decode())
                    else:
                        f.write(self.nkey_seed)
                    nkeys_seed = f.name
                    temp_file = f.name
            
            # Connect to NATS
            self.nc = await nats.connect(
                self.nats_url,
                nkeys_seed=nkeys_seed,
                name=f"{self.name} ({self.client_id})",
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback,
                closed_cb=self._closed_callback
            )
            
            self._is_connected = True
            logger.info(f"Connected to NATS as {self.client_id}")
            
            # Send connect presence message
            await self._send_presence("connect")
            
            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Start metrics reporting if enabled
            if self.enable_metrics:
                self._metrics_task = asyncio.create_task(self._metrics_loop())
            
            # Clean up temp file if created
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
                
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from NATS."""
        self._is_connected = False
        
        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
                
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        
        # Send disconnect presence
        if self.nc and self.nc.is_connected:
            try:
                await self._send_presence("disconnect")
                await self.nc.flush()
            except:
                pass
            
        # Close connection
        if self.nc:
            await self.nc.close()
            
        logger.info("Disconnected from NATS")
    
    async def subscribe(self, subject: str, handler: Optional[Callable] = None):
        """
        Subscribe to a subject pattern.
        
        Args:
            subject: Subject pattern (e.g., "tasks.*", "alerts.>")
            handler: Optional message handler function
        """
        # Add tenant prefix if not already present
        if not subject.startswith(f"{self.tenant_id}.") and not subject.startswith("tenant."):
            full_subject = f"{self.tenant_id}.{subject}"
        else:
            full_subject = subject
        
        # Create subscription
        sub = await self.nc.subscribe(full_subject)
        self._subscriptions[subject] = sub
        
        if handler:
            self._message_handlers[subject] = handler
            
        logger.info(f"Subscribed to {full_subject}")
        
        # Start message processor if handler provided
        if handler:
            asyncio.create_task(self._process_messages(sub, subject, handler))
    
    async def unsubscribe(self, subject: str):
        """Unsubscribe from a subject."""
        if subject in self._subscriptions:
            await self._subscriptions[subject].unsubscribe()
            del self._subscriptions[subject]
            if subject in self._message_handlers:
                del self._message_handlers[subject]
            logger.info(f"Unsubscribed from {subject}")
    
    async def publish(self, subject: str, data: Any, reply: Optional[str] = None):
        """
        Publish a message to a subject.
        
        Args:
            subject: Target subject
            data: Message data (will be JSON encoded if not bytes)
            reply: Optional reply-to subject
        """
        # Add tenant prefix if not already present
        if not subject.startswith(f"{self.tenant_id}.") and not subject.startswith("tenant.") and not subject.startswith("_"):
            full_subject = f"{self.tenant_id}.{subject}"
        else:
            full_subject = subject
        
        # Encode data
        if isinstance(data, bytes):
            payload = data
        else:
            payload = json.dumps(data).encode()
        
        # Publish
        await self.nc.publish(full_subject, payload, reply=reply)
        
        # Track metrics
        if self.enable_metrics and not full_subject.startswith("_"):
            self._message_stats["sent"][full_subject] = self._message_stats["sent"].get(full_subject, 0) + 1
            self._message_stats["bytes_sent"] += len(payload)
        
        logger.debug(f"Published to {full_subject}")
    
    async def request(self, subject: str, data: Any, timeout: float = 5.0) -> Any:
        """
        Send a request and wait for a response.
        
        Args:
            subject: Target subject
            data: Request data
            timeout: Response timeout in seconds
            
        Returns:
            Response data (JSON decoded if possible)
        """
        # Add tenant prefix if needed
        if not subject.startswith(f"{self.tenant_id}.") and not subject.startswith("tenant."):
            full_subject = f"{self.tenant_id}.{subject}"
        else:
            full_subject = subject
        
        # Encode data
        if isinstance(data, bytes):
            payload = data
        else:
            payload = json.dumps(data).encode()
        
        # Send request
        try:
            msg = await self.nc.request(full_subject, payload, timeout=timeout)
            
            # Track metrics
            if self.enable_metrics:
                self._message_stats["sent"][full_subject] = self._message_stats["sent"].get(full_subject, 0) + 1
                self._message_stats["bytes_sent"] += len(payload)
                self._message_stats["received"][full_subject] = self._message_stats["received"].get(full_subject, 0) + 1
                self._message_stats["bytes_received"] += len(msg.data)
            
            # Decode response
            try:
                return json.loads(msg.data.decode())
            except:
                return msg.data
        except TimeoutError:
            raise TimeoutError(f"Request to {full_subject} timed out")
        except NoRespondersError:
            raise NoRespondersError(f"No responders for {full_subject}")
    
    def on_message(self, subject: str):
        """
        Decorator for registering message handlers.
        
        Usage:
            @agent.on_message("tasks.*")
            async def handle_task(subject, data):
                print(f"Task received: {data}")
        """
        def decorator(handler):
            asyncio.create_task(self.subscribe(subject, handler))
            return handler
        return decorator
    
    async def start(self):
        """Start the agent and wait for messages."""
        logger.info("NATS agent started")
        self._is_connected = True
        
        # Keep running until stopped
        while self._is_connected:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the agent."""
        logger.info("Stopping NATS agent")
        self._is_connected = False
        await self.disconnect()
        logger.info("NATS agent stopped")
    
    # Private methods
    
    async def _process_messages(self, subscription, subject: str, handler: Callable):
        """Process messages for a subscription."""
        async for msg in subscription.messages:
            try:
                # Decode message
                try:
                    data = json.loads(msg.data.decode())
                except:
                    data = msg.data
                
                # Track metrics
                if self.enable_metrics and not msg.subject.startswith("_"):
                    self._message_stats["received"][msg.subject] = self._message_stats["received"].get(msg.subject, 0) + 1
                    self._message_stats["bytes_received"] += len(msg.data)
                
                # Remove tenant prefix from subject for handler
                clean_subject = msg.subject
                if clean_subject.startswith(f"{self.tenant_id}."):
                    clean_subject = clean_subject[len(f"{self.tenant_id}."):]
                elif clean_subject.startswith(f"tenant.{self.tenant_id}."):
                    clean_subject = clean_subject[len(f"tenant.{self.tenant_id}."):]
                
                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(clean_subject, data)
                else:
                    handler(clean_subject, data)
                    
            except Exception as e:
                logger.error(f"Error processing message on {subject}: {e}")
    
    async def _send_presence(self, presence_type: str, metadata: Optional[Dict] = None):
        """Send presence message following ArtCafe protocol."""
        # Use different subjects for different presence types
        if presence_type == "heartbeat":
            subject = f"_heartbeat.{self.tenant_id}.{self.client_id}"
        else:
            subject = f"_PRESENCE.tenant.{self.tenant_id}.client.{self.client_id}"
        
        # Use minimal format for heartbeats, full format for other presence messages
        if presence_type == "heartbeat":
            message = {
                "ts": int(datetime.now(timezone.utc).timestamp()),
                "v": "1.0"
            }
        else:
            message = {
                "client_id": self.client_id,
                "tenant_id": self.tenant_id,
                "type": presence_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {
                    "name": self.name,
                    "version": "1.0.0",
                    "framework": "artcafe-agent-framework",
                    **self.metadata
                }
            }
        
        try:
            await self.nc.publish(subject, json.dumps(message).encode())
            if presence_type != "heartbeat":
                logger.info(f"Sent {presence_type} presence message")
        except Exception as e:
            logger.error(f"Error sending presence: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self._is_connected:
            try:
                await self._send_presence("heartbeat")
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def _metrics_loop(self):
        """Report metrics periodically."""
        while self._is_connected:
            try:
                await asyncio.sleep(self._metrics_interval)
                
                # Only report if there's activity
                if any(self._message_stats["sent"].values()) or any(self._message_stats["received"].values()):
                    await self._report_metrics()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics reporting error: {e}")
    
    async def _report_metrics(self):
        """Send metrics report."""
        subject = f"_METRICS.tenant.{self.tenant_id}.client.{self.client_id}"
        
        report = {
            "client_id": self.client_id,
            "tenant_id": self.tenant_id,
            "period_end": datetime.now(timezone.utc).isoformat(),
            "messages_sent": sum(self._message_stats["sent"].values()),
            "messages_received": sum(self._message_stats["received"].values()),
            "bytes_sent": self._message_stats["bytes_sent"],
            "bytes_received": self._message_stats["bytes_received"],
            "subjects": {
                "sent": dict(self._message_stats["sent"]),
                "received": dict(self._message_stats["received"])
            }
        }
        
        try:
            await self.nc.publish(subject, json.dumps(report).encode())
            logger.debug(f"Reported metrics: {report['messages_sent']} sent, {report['messages_received']} received")
            
            # Reset stats after reporting
            self._message_stats = {
                "sent": {},
                "received": {},
                "bytes_sent": 0,
                "bytes_received": 0
            }
        except Exception as e:
            logger.error(f"Error reporting metrics: {e}")
    
    async def _error_callback(self, e):
        """Handle NATS errors."""
        logger.error(f"NATS error: {e}")
    
    async def _disconnected_callback(self):
        """Handle disconnection."""
        logger.warning("Disconnected from NATS")
        self._is_connected = False
    
    async def _reconnected_callback(self):
        """Handle reconnection."""
        logger.info("Reconnected to NATS")
        self._is_connected = True
        # Send connect presence on reconnect
        await self._send_presence("connect")
    
    async def _closed_callback(self):
        """Handle connection closed."""
        logger.info("NATS connection closed")
        self._is_connected = False