"""
WebSocket authentication example matching the working implementation.

This example shows how agents actually connect to ArtCafe:
1. Generate a challenge
2. Sign it with SSH private key
3. Connect via WebSocket with challenge/signature in URL params
"""

import asyncio
import json
import logging
import websockets
import uuid
import base64
from urllib.parse import urlencode
from pathlib import Path
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleWebSocketAgent:
    """Example of actual WebSocket authentication used by ArtCafe agents."""
    
    def __init__(self, agent_id: str, organization_id: str, private_key_path: str):
        self.agent_id = agent_id
        self.organization_id = organization_id  # Called tenant_id in API
        self.private_key_path = Path(private_key_path).expanduser()
        
        # Configuration
        self.ws_endpoint = "wss://ws.artcafe.ai"
        
        # Load private key
        self.private_key = self._load_private_key()
        
        # Connection state
        self.websocket = None
        self.connected = False
    
    def _load_private_key(self):
        """Load SSH private key from file."""
        with open(self.private_key_path, 'rb') as f:
            # Try OpenSSH format first
            key_data = f.read()
            if b'-----BEGIN OPENSSH PRIVATE KEY-----' in key_data:
                return serialization.load_ssh_private_key(key_data, password=None)
            else:
                # Try PEM format
                return serialization.load_pem_private_key(key_data, password=None)
    
    def _sign_challenge(self, challenge: str) -> str:
        """
        Sign a challenge using the exact method the server expects.
        
        Returns:
            Base64-encoded signature
        """
        # Create SHA256 hash of the challenge
        message = challenge.encode('utf-8')
        digest = hashes.Hash(hashes.SHA256())
        digest.update(message)
        digest_bytes = digest.finalize()
        
        # Sign with PKCS1v15 padding (matching server expectation)
        signature = self.private_key.sign(
            digest_bytes,
            padding.PKCS1v15(),
            Prehashed(hashes.SHA256())
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    async def connect(self):
        """Connect to WebSocket with challenge-response authentication."""
        try:
            # Generate a fresh challenge
            challenge = str(uuid.uuid4())
            
            # Sign the challenge
            signature = self._sign_challenge(challenge)
            
            # Build WebSocket URL with auth parameters
            params = {
                "challenge": challenge,
                "signature": signature,
                "tenant_id": self.organization_id  # API uses tenant_id
            }
            
            ws_url = f"{self.ws_endpoint}/api/v1/ws/agent/{self.agent_id}?{urlencode(params)}"
            
            logger.info(f"Connecting to WebSocket...")
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(ws_url)
            self.connected = True
            
            logger.info(f"Connected successfully!")
            
            # Send initial presence
            await self.publish("agents.presence.online", {
                "agent_id": self.agent_id,
                "status": "online",
                "capabilities": ["example", "demo"]
            })
            
            # Start listening for messages
            await self._listen()
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            raise
    
    async def publish(self, subject: str, data: dict):
        """Publish a message to a subject."""
        if not self.connected:
            raise RuntimeError("Not connected")
        
        message = {
            "type": "publish",
            "subject": subject,
            "data": data
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info(f"Published to {subject}")
    
    async def _listen(self):
        """Listen for incoming messages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get("type", "message")
                
                if msg_type == "message":
                    subject = data.get("subject")
                    payload = data.get("data")
                    logger.info(f"Received message on {subject}: {payload}")
                    
                    # Example: respond to hello messages
                    if subject == "hello":
                        await self.publish("hello.response", {
                            "from": self.agent_id,
                            "message": "Hello back!"
                        })
                
                elif msg_type == "ack":
                    logger.debug(f"Acknowledgment: {data}")
                
                elif msg_type == "pong":
                    logger.debug(f"Pong received")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in message handler: {e}")


async def main():
    """Run the WebSocket example."""
    # Configuration from environment or defaults
    agent_id = os.environ.get("ARTCAFE_AGENT_ID", "example-agent-001")
    organization_id = os.environ.get("ARTCAFE_ORGANIZATION_ID")
    private_key_path = os.environ.get("ARTCAFE_PRIVATE_KEY_PATH", "~/.ssh/artcafe_agent_key")
    
    if not organization_id:
        print("Error: Please set ARTCAFE_ORGANIZATION_ID environment variable")
        print("You can find your organization ID in the ArtCafe.ai dashboard")
        return
    
    # Create and connect agent
    agent = SimpleWebSocketAgent(agent_id, organization_id, private_key_path)
    
    try:
        await agent.connect()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Failed to connect: {e}")


if __name__ == "__main__":
    print("""
WebSocket Connection Example
===========================
This example shows the actual authentication flow used by ArtCafe agents:
1. Generate a challenge
2. Sign with SSH private key (PKCS1v15 + SHA256)
3. Connect with challenge/signature in URL params

No JWT tokens or separate auth endpoints needed!

Press Ctrl+C to stop.
""")
    
    asyncio.run(main())