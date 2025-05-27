"""
Agent implementation that matches the working ArtCafe platform.

This module provides the agent class that works with the actual
ArtCafe.ai platform implementation.
"""

import asyncio
import json
import logging
import platform
import uuid
import base64
from typing import Dict, Any, Optional, Callable, List, Set
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import websockets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

logger = logging.getLogger(__name__)


class SimplifiedAgent:
    """
    ArtCafe Agent that works with the actual platform implementation.
    
    This class matches the working artcafe-getting-started implementation:
    - Challenge-response authentication in WebSocket URL
    - No JWT tokens
    - Decorator-based message handlers
    - Peer-based messaging (all agents get all messages on subscribed channels)
    """
    
    def __init__(
        self,
        agent_id: str,
        organization_id: str,
        private_key_path: str,
        ws_endpoint: str = "wss://ws.artcafe.ai",
        api_endpoint: str = "https://api.artcafe.ai",
        name: Optional[str] = None,
        description: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        log_level: str = "INFO",
        **kwargs
    ):
        """
        Initialize an ArtCafe agent.
        
        Args:
            agent_id: Unique agent identifier
            organization_id: Organization ID (called tenant_id in API)
            private_key_path: Path to SSH private key
            ws_endpoint: WebSocket endpoint URL
            api_endpoint: REST API endpoint URL
            name: Human-readable name
            description: Agent description
            capabilities: List of agent capabilities
            metadata: Additional metadata
            log_level: Logging level
            **kwargs: Additional configuration
        """
        self.agent_id = agent_id
        self.organization_id = organization_id
        self.tenant_id = organization_id  # API compatibility
        self.ws_endpoint = ws_endpoint
        self.api_endpoint = api_endpoint
        self.name = name or f"Agent-{agent_id[:8]}"
        self.description = description or "ArtCafe Agent"
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        
        # Setup logging
        self.logger = logging.getLogger(f"ArtCafeAgent-{agent_id}")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Load private key
        self.private_key_path = Path(private_key_path).expanduser()
        self.private_key = self._load_private_key()
        
        # Connection state
        self.websocket = None
        self.connected = False
        self._running = False
        self.subscriptions: Set[str] = set()
        
        # Message handlers
        self._message_handlers: Dict[str, Callable] = {}
        self._default_handler: Optional[Callable] = None
        
        # Tasks
        self._tasks: Set[asyncio.Task] = set()
        
        # System info
        self.hostname = platform.node()
        
        self.logger.info(f"Agent initialized: {agent_id} on {self.hostname}")
    
    def _load_private_key(self):
        """Load private key from file."""
        if not self.private_key_path.exists():
            raise FileNotFoundError(f"Private key not found: {self.private_key_path}")
        
        with open(self.private_key_path, 'rb') as f:
            key_data = f.read()
            
        # Try OpenSSH format first
        if b'-----BEGIN OPENSSH PRIVATE KEY-----' in key_data:
            return serialization.load_ssh_private_key(key_data, password=None)
        else:
            # Try PEM format
            return serialization.load_pem_private_key(key_data, password=None)
    
    def _sign_challenge(self, challenge: str) -> str:
        """
        Sign a challenge string with the private key.
        
        Uses PKCS1v15 padding with SHA256 to match server expectations.
        """
        # Create SHA256 hash of the challenge
        message = challenge.encode('utf-8')
        digest = hashes.Hash(hashes.SHA256())
        digest.update(message)
        digest_bytes = digest.finalize()
        
        # Sign with PKCS1v15 padding
        signature = self.private_key.sign(
            digest_bytes,
            padding.PKCS1v15(),
            Prehashed(hashes.SHA256())
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def on_message(self, pattern: str):
        """
        Decorator for registering message handlers.
        
        Example:
            @agent.on_message("tasks.new")
            async def handle_task(subject, data):
                print(f"New task: {data}")
        """
        def decorator(handler: Callable):
            self._message_handlers[pattern] = handler
            self.logger.debug(f"Registered handler for pattern: {pattern}")
            return handler
        return decorator
    
    def default_handler(self, handler: Callable):
        """
        Decorator for setting the default message handler.
        
        Example:
            @agent.default_handler
            async def handle_unknown(subject, data):
                logger.warning(f"Unhandled message: {subject}")
        """
        self._default_handler = handler
        return handler
    
    async def connect(self):
        """
        Connect to the ArtCafe WebSocket server.
        
        Uses challenge-response authentication in URL parameters.
        """
        if self.connected:
            self.logger.warning("Already connected")
            return
        
        try:
            # Generate a fresh challenge
            challenge = str(uuid.uuid4())
            
            # Sign the challenge
            signature = self._sign_challenge(challenge)
            
            # Build WebSocket URL with auth parameters
            params = {
                "challenge": challenge,
                "signature": signature,
                "tenant_id": self.tenant_id  # API uses tenant_id
            }
            
            ws_url = f"{self.ws_endpoint}/api/v1/ws/agent/{self.agent_id}?{urlencode(params)}"
            
            self.logger.info(f"Connecting to WebSocket: {self.ws_endpoint}")
            
            # Connect!
            self.websocket = await websockets.connect(ws_url)
            self.connected = True
            self._running = True
            
            self.logger.info("WebSocket connected and authenticated!")
            
            # Send initial presence
            await self._send_presence("online")
            
            # Start message handler
            self._create_task(self._handle_messages())
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.websocket and self.connected:
            try:
                self._running = False
                
                # Send offline presence
                await self._send_presence("offline")
                
                # Cancel all tasks
                for task in self._tasks:
                    task.cancel()
                
                # Wait for tasks to complete
                if self._tasks:
                    await asyncio.gather(*self._tasks, return_exceptions=True)
                
                # Close connection
                await self.websocket.close()
                
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
            finally:
                self.connected = False
                self.websocket = None
                self.logger.info("Disconnected from WebSocket")
    
    async def publish(self, subject: str, data: Any):
        """
        Publish a message to a subject.
        
        Args:
            subject: The subject/channel to publish to
            data: The message data (will be JSON serialized)
        """
        if not self.connected:
            raise RuntimeError("Not connected")
        
        message = {
            "type": "publish",
            "subject": subject,
            "data": data
        }
        
        await self.websocket.send(json.dumps(message))
        self.logger.debug(f"Published to {subject}")
    
    async def subscribe(self, subject: str):
        """
        Subscribe to a subject pattern.
        
        Args:
            subject: Subject pattern to subscribe to (supports wildcards)
        """
        if not self.connected:
            raise RuntimeError("Not connected")
        
        if subject not in self.subscriptions:
            message = {
                "type": "subscribe",
                "subject": subject
            }
            
            await self.websocket.send(json.dumps(message))
            self.subscriptions.add(subject)
            self.logger.info(f"Subscribed to: {subject}")
    
    async def _handle_messages(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                if not self._running:
                    break
                    
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "message")
                    
                    if msg_type == "message":
                        # Route to appropriate handler
                        subject = data.get("subject", "")
                        payload = data.get("data", {})
                        
                        # Check for specific handlers
                        handled = False
                        for pattern, handler in self._message_handlers.items():
                            if self._matches_pattern(subject, pattern):
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(subject, payload)
                                else:
                                    handler(subject, payload)
                                handled = True
                                break
                        
                        # Use default handler if no specific match
                        if not handled and self._default_handler:
                            if asyncio.iscoroutinefunction(self._default_handler):
                                await self._default_handler(subject, payload)
                            else:
                                self._default_handler(subject, payload)
                    
                    elif msg_type == "ack":
                        self.logger.debug(f"Acknowledgment: {data}")
                    
                    elif msg_type == "pong":
                        self.logger.debug("Pong received")
                    
                    elif msg_type == "subscribed":
                        self.logger.debug(f"Subscription confirmed: {data.get('subject')}")
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON message: {e}")
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            self.logger.error(f"Error in message handler: {e}")
            self.connected = False
    
    def _matches_pattern(self, subject: str, pattern: str) -> bool:
        """Check if a subject matches a pattern (supports wildcards)."""
        if pattern == subject:
            return True
        
        # Simple wildcard matching
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return subject.startswith(prefix)
        
        # Handle '>' wildcard (matches any number of tokens)
        if '>' in pattern:
            pattern_parts = pattern.split('.')
            subject_parts = subject.split('.')
            
            for i, part in enumerate(pattern_parts):
                if part == '>':
                    return True  # Match rest
                if i >= len(subject_parts) or part != subject_parts[i]:
                    return False
            
            return True
        
        return False
    
    async def _send_presence(self, status: str):
        """Send presence announcement."""
        await self.publish("agents.presence.online" if status == "online" else "agents.presence.offline", {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": status,
            "capabilities": self.capabilities,
            "hostname": self.hostname,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def _create_task(self, coro):
        """Create and track an async task."""
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task
    
    async def run_forever(self):
        """
        Run the agent until interrupted.
        
        This method connects and runs until Ctrl+C or disconnect.
        """
        try:
            await self.connect()
            
            # Subscribe to default patterns
            await self.subscribe(f"agents.{self.agent_id}.*")  # Direct messages
            await self.subscribe(f"agents.control.{self.agent_id}.*")  # Control messages
            
            self.logger.info(f"Agent {self.agent_id} running. Press Ctrl+C to stop.")
            
            # Keep running
            while self._running and self.connected:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Agent error: {e}")
        finally:
            await self.disconnect()
    
    async def stop(self):
        """Stop the agent and clean up resources."""
        await self.disconnect()


# Convenience function for quick agent creation
def create_agent(
    agent_id: str,
    organization_id: str,
    private_key_path: str,
    **kwargs
) -> SimplifiedAgent:
    """
    Factory function to create an agent.
    
    Args:
        agent_id: Unique agent identifier
        organization_id: Organization ID (your workspace ID from the dashboard)
        private_key_path: Path to SSH private key
        **kwargs: Additional configuration
        
    Returns:
        Configured agent instance
    """
    return SimplifiedAgent(
        agent_id=agent_id,
        organization_id=organization_id,
        private_key_path=private_key_path,
        **kwargs
    )