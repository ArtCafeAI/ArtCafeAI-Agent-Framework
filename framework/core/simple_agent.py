"""
Simple Agent - A minimal agent implementation for quick starts.

This module provides an agent that uses WebSocket connection with
challenge-response authentication, matching the working implementation.
"""

import asyncio
import json
import logging
import base64
import time
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


class SimpleAgent:
    """
    An agent that connects via WebSocket with challenge-response authentication.
    
    Matches the working implementation from artcafe-getting-started.
    
    Example:
        ```python
        agent = SimpleAgent(
            agent_id="my-agent",
            private_key_path="path/to/private_key.pem",
            organization_id="org-123"
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
        websocket_url: str = "wss://ws.artcafe.ai",
        capabilities: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Initialize agent with WebSocket connection parameters.
        
        Args:
            agent_id: Unique identifier for the agent
            private_key_path: Path to RSA private key file
            organization_id: Organization/tenant ID
            websocket_url: WebSocket server URL
            capabilities: List of agent capabilities
            metadata: Additional agent metadata
        """
        self.agent_id = agent_id
        self.organization_id = organization_id
        self.websocket_url = websocket_url
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
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send a message through the WebSocket."""
        if self._websocket:
            await self._websocket.send(json.dumps(message))
    
    async def _receive_messages(self):
        """Receive and process messages from WebSocket."""
        try:
            async for message in self._websocket:
                data = json.loads(message)
                
                # Handle different message types
                if data.get('type') == 'message':
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
                
                elif data.get('type') == 'error':
                    logger.error(f"Received error: {data.get('message')}")
                    
        except websockets.ConnectionClosed:
            logger.info(f"WebSocket connection closed for {self.agent_id}")
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
    
    async def publish(self, channel: str, data: Dict[str, Any]):
        """Publish a message to a channel."""
        await self._send_message({
            'type': 'publish',
            'channel': channel,
            'data': data
        })
    
    async def run(self):
        """Run the agent."""
        self._running = True
        
        try:
            # Connect to WebSocket
            await self._connect()
            
            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_messages())
            
            # Keep running
            await self._receive_task
            
        except KeyboardInterrupt:
            logger.info(f"Agent {self.agent_id} shutting down...")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the agent and clean up resources."""
        self._running = False
        
        # Send offline presence
        if self._websocket:
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