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
from datetime import datetime

import nats
from nats.errors import ConnectionClosedError, TimeoutError, NoRespondersError

from .base_agent import BaseAgent
from ..core.config import AgentConfig

logger = logging.getLogger("AgentFramework.Core.NATSAgent")


class NATSAgent(BaseAgent):
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
        config: Optional[AgentConfig] = None
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
        """
        # Initialize base agent
        super().__init__(
            agent_id=client_id,
            agent_type="nats",
            config=config or AgentConfig()
        )
        
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.nkey_seed = nkey_seed
        self.nats_url = nats_url
        self.name = name or client_id
        self.metadata = metadata or {}
        
        # NATS connection
        self.nc: Optional[nats.NATS] = None
        self._subscriptions = {}
        self._message_handlers = {}
        self._is_connected = False
        self._heartbeat_task = None
        
        logger.info(f"NATS Agent initialized: {client_id}")
    
    async def connect(self):
        """Connect to NATS using NKey authentication."""
        try:
            # Handle NKey seed
            if isinstance(self.nkey_seed, str) and os.path.exists(self.nkey_seed):
                # It's a file path
                creds_file = self.nkey_seed
            else:
                # It's the seed string - write to temp file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.nkey') as f:
                    if isinstance(self.nkey_seed, bytes):
                        f.write(self.nkey_seed.decode())
                    else:
                        f.write(self.nkey_seed)
                    creds_file = f.name
            
            # Connect to NATS
            self.nc = await nats.connect(
                self.nats_url,
                credentials=creds_file,
                name=f"{self.name} ({self.client_id})",
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback,
                closed_cb=self._closed_callback,
            )
            
            self._is_connected = True
            logger.info(f"Connected to NATS as {self.client_id}")
            
            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Clean up temp file if created
            if creds_file != self.nkey_seed and os.path.exists(creds_file):
                os.unlink(creds_file)
                
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from NATS."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            
        if self.nc:
            await self.nc.close()
            
        self._is_connected = False
        logger.info("Disconnected from NATS")
    
    async def subscribe(self, subject: str, handler: Optional[Callable] = None):
        """
        Subscribe to a subject pattern.
        
        Args:
            subject: Subject pattern (e.g., "tasks.*", "alerts.>")
            handler: Optional message handler function
        """
        # Add tenant prefix
        full_subject = f"{self.tenant_id}.{subject}"
        
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
        # Add tenant prefix
        full_subject = f"{self.tenant_id}.{subject}"
        
        # Encode data
        if isinstance(data, bytes):
            payload = data
        else:
            payload = json.dumps(data).encode()
        
        # Publish
        await self.nc.publish(full_subject, payload, reply=reply)
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
        # Add tenant prefix
        full_subject = f"{self.tenant_id}.{subject}"
        
        # Encode data
        if isinstance(data, bytes):
            payload = data
        else:
            payload = json.dumps(data).encode()
        
        try:
            # Send request
            response = await self.nc.request(full_subject, payload, timeout=timeout)
            
            # Decode response
            try:
                return json.loads(response.data.decode())
            except:
                return response.data
                
        except TimeoutError:
            logger.error(f"Request timeout for {subject}")
            raise
        except NoRespondersError:
            logger.error(f"No responders for {subject}")
            raise
    
    def on_message(self, subject: str):
        """
        Decorator for message handlers.
        
        Example:
            @agent.on_message("tasks.new")
            async def handle_new_task(subject, data):
                # Process task
                await agent.publish("tasks.result", result)
        """
        def decorator(func):
            asyncio.create_task(self.subscribe(subject, func))
            return func
        return decorator
    
    async def start(self):
        """Start the agent and maintain connection."""
        if not self._is_connected:
            await self.connect()
            
        try:
            await super().start()  # Call parent start method
        finally:
            await self.disconnect()
    
    async def stop(self):
        """Stop the agent."""
        logger.info("Stopping NATS agent")
        self._is_connected = False
        await super().stop()  # Call parent stop method
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
                
                # Remove tenant prefix from subject for handler
                clean_subject = msg.subject.replace(f"{self.tenant_id}.", "", 1)
                
                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(clean_subject, data)
                else:
                    handler(clean_subject, data)
                    
            except Exception as e:
                logger.error(f"Error processing message on {subject}: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self._is_connected:
            try:
                await self.publish("heartbeat", {
                    "client_id": self.client_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": self.metadata
                })
                await asyncio.sleep(30)  # 30 second heartbeat
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    def _error_callback(self, e):
        """Handle NATS errors."""
        logger.error(f"NATS error: {e}")
    
    def _disconnected_callback(self):
        """Handle disconnection."""
        logger.warning("Disconnected from NATS")
        self._is_connected = False
    
    def _reconnected_callback(self):
        """Handle reconnection."""
        logger.info("Reconnected to NATS")
        self._is_connected = True
    
    def _closed_callback(self):
        """Handle connection closed."""
        logger.info("NATS connection closed")
        self._is_connected = False