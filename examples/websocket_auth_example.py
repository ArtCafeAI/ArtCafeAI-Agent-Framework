"""
WebSocket authentication example for ArtCafe agents.

This example demonstrates the authentication flow:
1. Get challenge from the platform
2. Sign challenge with SSH key
3. Connect via WebSocket with signed challenge
"""

import asyncio
import json
import logging
import websockets
from urllib.parse import urlencode
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketAuthExample:
    """Example of WebSocket authentication for agents."""
    
    def __init__(self, agent_id: str, tenant_id: str, private_key_path: str):
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.private_key_path = Path(private_key_path)
        
        # Configuration
        self.api_endpoint = "https://api.artcafe.ai"
        self.ws_endpoint = "wss://ws.artcafe.ai"
        
        # Load private key
        self.private_key = self._load_private_key()
    
    def _load_private_key(self):
        """Load SSH private key from file."""
        with open(self.private_key_path, 'rb') as f:
            return serialization.load_ssh_private_key(
                f.read(),
                password=None
            )
    
    async def get_challenge(self) -> tuple[str, str]:
        """
        Get authentication challenge from the platform.
        
        Returns:
            Tuple of (challenge, signature)
        """
        async with httpx.AsyncClient() as client:
            # Step 1: Get challenge
            response = await client.post(
                f"{self.api_endpoint}/api/v1/auth/agent/challenge",
                json={"key_id": self.agent_id}
            )
            response.raise_for_status()
            
            data = response.json()
            challenge = data['challenge']
            
            # Step 2: Sign challenge
            signature = self.private_key.sign(
                challenge.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            return challenge, signature_b64
    
    async def connect_websocket(self):
        """Connect to WebSocket with authentication."""
        try:
            # Get authentication credentials
            challenge, signature = await self.get_challenge()
            
            # Build WebSocket URL with auth params
            params = {
                "agent_id": self.agent_id,
                "tenant_id": self.tenant_id,
                "challenge": challenge,
                "signature": signature
            }
            
            ws_url = f"{self.ws_endpoint}/api/v1/ws/agent/{self.agent_id}?{urlencode(params)}"
            
            logger.info(f"Connecting to WebSocket...")
            
            # Connect to WebSocket
            async with websockets.connect(ws_url) as websocket:
                logger.info(f"Connected successfully!")
                
                # Subscribe to a topic
                await websocket.send(json.dumps({
                    "type": "subscribe",
                    "subject": "tasks.new"
                }))
                
                # Send a test message
                await websocket.send(json.dumps({
                    "type": "publish",
                    "subject": "agents.status",
                    "data": {
                        "status": "online",
                        "capabilities": ["task_processing", "data_analysis"]
                    }
                }))
                
                # Listen for messages
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    logger.info(f"Received: {data}")
                    
                    # Handle different message types
                    if data.get('type') == 'subscribed':
                        logger.info(f"Successfully subscribed to: {data.get('subject')}")
                    elif data.get('type') == 'message':
                        # Handle incoming messages
                        subject = data.get('subject')
                        payload = data.get('data')
                        logger.info(f"Message on {subject}: {payload}")
        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            raise


async def main():
    """Run the WebSocket authentication example."""
    import os
    
    # Configuration from environment variables or defaults
    # You can find these values in your ArtCafe.ai dashboard:
    # - Organization ID: Dashboard > Settings > Organization
    # - Agent ID: Dashboard > Agents > Your Agent
    agent_id = os.environ.get("ARTCAFE_AGENT_ID", "example-agent-001")
    organization_id = os.environ.get("ARTCAFE_ORGANIZATION_ID")  # Also called tenant_id in API
    private_key_path = os.environ.get("ARTCAFE_PRIVATE_KEY_PATH", "~/.ssh/artcafe_agent_key")
    
    if not organization_id:
        print("Error: Please set ARTCAFE_ORGANIZATION_ID environment variable")
        print("You can find your organization ID in the ArtCafe.ai dashboard under Settings")
        return
    
    # Expand user path
    private_key_path = os.path.expanduser(private_key_path)
    
    if not os.path.exists(private_key_path):
        print(f"Error: Private key not found at {private_key_path}")
        print("Please ensure your SSH private key exists at the specified path")
        return
    
    # Create and run example
    # Note: The API still uses tenant_id internally
    example = WebSocketAuthExample(agent_id, organization_id, private_key_path)
    
    try:
        await example.connect_websocket()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())