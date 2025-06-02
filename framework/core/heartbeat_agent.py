"""
Heartbeat Agent - Enhanced agent with automatic heartbeat support.

This agent automatically sends periodic heartbeats to maintain online status,
ensuring accurate status tracking in the dashboard.
"""

import asyncio
import json
import logging
import base64
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable, List
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric.types import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
import websockets
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class HeartbeatAgent:
    """
    An agent with automatic heartbeat support for accurate status tracking.
    
    This agent extends the simple agent with:
    - Automatic periodic heartbeats
    - Configurable heartbeat interval
    - Connection health monitoring
    - Automatic reconnection on heartbeat timeout
    
    Example:
        ```python
        agent = HeartbeatAgent(
            agent_id="my-agent",
            private_key_path="path/to/private_key.pem",
            organization_id="org-123",
            heartbeat_interval=30  # Send heartbeat every 30 seconds
        )
        
        @agent.on_message("team.updates")
        async def handle_update(subject, data):
            print(f"Received: {data}")
            
        await agent.run()
        ```
    """
    
    def __init__(
        self,
        agent_id: str,
        private_key_path: str,
        organization_id: str,
        websocket_url: str = "wss://api.artcafe.ai",
        heartbeat_interval: int = 30,
        heartbeat_timeout_multiplier: float = 3.0,
        auto_reconnect: bool = True,
        capabilities: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Initialize agent with WebSocket connection and heartbeat parameters.
        
        Args:
            agent_id: Unique identifier for the agent
            private_key_path: Path to RSA private key file
            organization_id: Organization/tenant ID
            websocket_url: WebSocket server URL
            heartbeat_interval: Seconds between heartbeats (default: 30)
            heartbeat_timeout_multiplier: Multiplier for timeout (default: 3.0)
            auto_reconnect: Automatically reconnect on connection loss
            capabilities: List of agent capabilities
            metadata: Additional agent metadata
        """
        self.agent_id = agent_id
        self.organization_id = organization_id
        self.websocket_url = websocket_url
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_interval * heartbeat_timeout_multiplier
        self.auto_reconnect = auto_reconnect
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        
        # Load private key
        with open(private_key_path, 'rb') as key_file:
            self.private_key = load_pem_private_key(
                key_file.read(),
                password=None
            )
        
        self._message_handlers = {}
        self._subscriptions = set()
        self._running = False
        self._websocket = None
        self._receive_task = None
        self._heartbeat_task = None
        self._last_heartbeat_ack = None
        self._connection_healthy = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 5  # seconds
    
    def on_message(self, channel: str):
        """
        Decorator for registering message handlers.
        
        Example:
            ```python
            @agent.on_message("team.updates")
            async def handle_update(subject, data):
                print(f"Received: {data}")
            ```
        """
        def decorator(func: Callable):
            self._message_handlers[channel] = func
            self._subscriptions.add(channel)
            return func
        return decorator
    
    def _sign_challenge(self, challenge: str) -> str:
        """Sign a challenge string with the private key."""
        message = challenge.encode('utf-8')
        digest = hashes.Hash(hashes.SHA256())
        digest.update(message)
        digest_bytes = digest.finalize()
        
        signature = self.private_key.sign(
            digest_bytes,
            padding.PKCS1v15(),
            Prehashed(hashes.SHA256())
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    async def _connect(self):
        """Establish WebSocket connection with authentication."""
        # Get challenge
        import aiohttp
        async with aiohttp.ClientSession() as session:
            challenge_url = f"https://api.artcafe.ai/api/v1/agents/{self.agent_id}/challenge"
            headers = {"X-Tenant-Id": self.organization_id}
            
            async with session.get(challenge_url, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to get challenge: {await resp.text()}")
                challenge_data = await resp.json()
                challenge = challenge_data['challenge']
        
        # Sign challenge
        signature = self._sign_challenge(challenge)
        
        # Connect with auth params
        params = {
            'agent_id': self.agent_id,
            'challenge': challenge,
            'signature': signature
        }
        ws_url = f"{self.websocket_url}/api/v1/ws/agent/{self.agent_id}?{urlencode(params)}"
        
        self._websocket = await websockets.connect(ws_url)
        logger.info(f"Agent {self.agent_id} connected to WebSocket")
        
        # Reset connection state
        self._connection_healthy = True
        self._reconnect_attempts = 0
        self._last_heartbeat_ack = datetime.now(timezone.utc)
        
        # Send presence announcement
        await self._send_message({
            'type': 'presence',
            'agent_id': self.agent_id,
            'status': 'online',
            'capabilities': self.capabilities,
            'metadata': self.metadata
        })
        
        # Subscribe to channels
        for channel in self._subscriptions:
            await self._send_message({
                'type': 'subscribe',
                'channel': channel
            })
            logger.debug(f"Subscribed to channel: {channel}")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send a message through the WebSocket."""
        if self._websocket and not self._websocket.closed:
            try:
                await self._websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                self._connection_healthy = False
    
    async def _send_heartbeat(self):
        """Send a heartbeat message."""
        heartbeat_msg = {
            'type': 'heartbeat',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        await self._send_message(heartbeat_msg)
        logger.debug(f"Sent heartbeat for {self.agent_id}")
    
    async def _heartbeat_loop(self):
        """Background task that sends periodic heartbeats."""
        logger.info(f"Starting heartbeat loop (interval: {self.heartbeat_interval}s)")
        
        while self._running:
            try:
                # Send heartbeat
                await self._send_heartbeat()
                
                # Check connection health
                if self._last_heartbeat_ack:
                    time_since_ack = (datetime.now(timezone.utc) - self._last_heartbeat_ack).total_seconds()
                    if time_since_ack > self.heartbeat_timeout:
                        logger.warning(f"Heartbeat timeout detected ({time_since_ack:.1f}s since last ack)")
                        self._connection_healthy = False
                        
                        if self.auto_reconnect:
                            logger.info("Triggering reconnection due to heartbeat timeout")
                            break
                
                # Wait for next interval
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                logger.debug("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _receive_messages(self):
        """Receive and process messages from WebSocket."""
        try:
            async for message in self._websocket:
                data = json.loads(message)
                msg_type = data.get('type')
                
                # Handle heartbeat acknowledgment
                if msg_type == 'heartbeat_ack':
                    self._last_heartbeat_ack = datetime.now(timezone.utc)
                    self._connection_healthy = True
                    logger.debug("Received heartbeat acknowledgment")
                
                # Handle regular messages
                elif msg_type == 'message':
                    subject = data.get('subject', '')
                    payload = data.get('data', {})
                    
                    # Find matching handler
                    for channel, handler in self._message_handlers.items():
                        if subject.startswith(channel):
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(subject, payload)
                                else:
                                    handler(subject, payload)
                            except Exception as e:
                                logger.error(f"Error in handler for {channel}: {e}")
                
                elif msg_type == 'error':
                    logger.error(f"Received error: {data.get('message')}")
                
                elif msg_type == 'welcome':
                    logger.info(f"Received welcome message: {data}")
                    
        except websockets.ConnectionClosed:
            logger.info(f"WebSocket connection closed for {self.agent_id}")
            self._connection_healthy = False
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            self._connection_healthy = False
    
    async def publish(self, channel: str, data: Dict[str, Any]):
        """Publish a message to a channel."""
        await self._send_message({
            'type': 'publish',
            'channel': channel,
            'data': data
        })
    
    async def _run_with_reconnect(self):
        """Run the agent with automatic reconnection."""
        while self._running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                # Connect to WebSocket
                await self._connect()
                
                # Start heartbeat task
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                # Start receiving messages
                self._receive_task = asyncio.create_task(self._receive_messages())
                
                # Wait for either task to complete
                done, pending = await asyncio.wait(
                    [self._heartbeat_task, self._receive_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # Check if we should reconnect
                if self._running and self.auto_reconnect and not self._connection_healthy:
                    self._reconnect_attempts += 1
                    delay = min(self._reconnect_delay * self._reconnect_attempts, 60)
                    logger.info(f"Reconnecting in {delay}s (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})")
                    await asyncio.sleep(delay)
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error in agent run loop: {e}")
                if self._running and self.auto_reconnect:
                    self._reconnect_attempts += 1
                    delay = min(self._reconnect_delay * self._reconnect_attempts, 60)
                    logger.info(f"Reconnecting after error in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    break
    
    async def run(self):
        """Run the agent with heartbeat support."""
        self._running = True
        logger.info(f"Starting HeartbeatAgent {self.agent_id}")
        
        try:
            if self.auto_reconnect:
                await self._run_with_reconnect()
            else:
                # Single run without reconnection
                await self._connect()
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self._receive_task = asyncio.create_task(self._receive_messages())
                
                # Wait for both tasks
                await asyncio.gather(self._heartbeat_task, self._receive_task)
                
        except KeyboardInterrupt:
            logger.info(f"Agent {self.agent_id} shutting down...")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the agent and clean up resources."""
        logger.info(f"Stopping agent {self.agent_id}")
        self._running = False
        
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Send offline presence
        if self._websocket and not self._websocket.closed:
            try:
                await self._send_message({
                    'type': 'presence',
                    'agent_id': self.agent_id,
                    'status': 'offline'
                })
                await self._websocket.close()
            except:
                pass
        
        # Cancel receive task
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Agent {self.agent_id} stopped")
    
    def get_connection_health(self) -> Dict[str, Any]:
        """Get current connection health status."""
        now = datetime.now(timezone.utc)
        time_since_ack = None
        
        if self._last_heartbeat_ack:
            time_since_ack = (now - self._last_heartbeat_ack).total_seconds()
        
        return {
            'healthy': self._connection_healthy,
            'connected': self._websocket is not None and not self._websocket.closed,
            'last_heartbeat_ack': self._last_heartbeat_ack.isoformat() if self._last_heartbeat_ack else None,
            'seconds_since_ack': time_since_ack,
            'reconnect_attempts': self._reconnect_attempts
        }