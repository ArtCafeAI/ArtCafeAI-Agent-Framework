#!/usr/bin/env python3

import os
import base64
import logging
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.backends import default_backend

from .auth_provider import AuthProvider

logger = logging.getLogger("AgentFramework.Auth.SSHAuthProvider")

class SSHAuthProvider(AuthProvider):
    """
    SSH key-based authentication provider for ArtCafe.ai PubSub service.
    
    This provider implements the challenge-response authentication flow using
    SSH keys as described in the ArtCafe.ai API documentation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the SSH authentication provider.
        
        Args:
            config: Configuration dictionary containing auth settings
        """
        super().__init__(config)
        
        self.private_key_path = self._resolve_path(config.get("ssh_key", {}).get("private_key_path", "~/.ssh/artcafe_agent"))
        self.key_type = config.get("ssh_key", {}).get("key_type", "agent")
        self.api_endpoint = config.get("api", {}).get("endpoint", "https://api.artcafe.ai")
        
        self.agent_id = config.get("agent_id")
        self.tenant_id = config.get("tenant_id")
        
        if not self.tenant_id:
            logger.warning("No tenant_id provided in configuration. Multi-tenant features will be unavailable.")
            
        # Authentication state
        self.jwt_token = None
        self.jwt_expires_at = None
        self.key_id = None
        
        # Load private key
        self._load_private_key()
    
    def _resolve_path(self, path: str) -> str:
        """Resolve ~ in path to user's home directory."""
        if path.startswith("~"):
            return os.path.expanduser(path)
        return path
    
    def _load_private_key(self) -> None:
        """Load the private key from the specified path."""
        try:
            if not os.path.exists(self.private_key_path):
                raise FileNotFoundError(f"Private key not found at {self.private_key_path}")
            
            with open(self.private_key_path, 'rb') as key_file:
                try:
                    self.private_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=None,
                        backend=default_backend()
                    )
                    logger.debug(f"Successfully loaded private key from {self.private_key_path}")
                except ValueError:
                    # Try again with password prompt if needed
                    logger.info("Private key is password protected. Please enter password:")
                    # In a real implementation, you might want a secure way to get the password
                    # This is just a placeholder for demonstration purposes
                    from getpass import getpass
                    password = getpass("Private key password: ")
                    
                    # Reset file pointer and try again
                    key_file.seek(0)
                    self.private_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=password.encode(),
                        backend=default_backend()
                    )
                    logger.debug("Successfully loaded password-protected private key")
                
        except Exception as e:
            logger.error(f"Failed to load private key: {str(e)}")
            raise
    
    def _sign_challenge(self, challenge: str) -> bytes:
        """
        Sign a challenge string with the private key.
        
        Args:
            challenge: Challenge string to sign
            
        Returns:
            bytes: Signature bytes
        """
        try:
            # Convert challenge to bytes
            message = challenge.encode('utf-8')
            
            # Create digest
            digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
            digest.update(message)
            digest_bytes = digest.finalize()
            
            # Sign the digest
            signature = self.private_key.sign(
                digest_bytes,
                padding.PKCS1v15(),
                Prehashed(hashes.SHA256())
            )
            
            return signature
            
        except Exception as e:
            logger.error(f"Error signing challenge: {str(e)}")
            raise
    
    async def _get_agent_key_id(self) -> Optional[str]:
        """
        Get the agent's SSH key ID by querying the API.
        
        Returns:
            str or None: The SSH key ID if found, None otherwise
        """
        try:
            # Make a temporary JWT for querying (in a real implementation, this would not be secure)
            # This is used just to illustrate the flow
            headers = {"x-tenant-id": self.tenant_id}
            
            # Query for keys associated with this agent
            response = requests.get(
                f"{self.api_endpoint}/api/v1/ssh-keys",
                params={"agent_id": self.agent_id, "key_type": "agent"},
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get SSH keys: {response.text}")
                return None
            
            data = response.json()
            
            if not data.get("ssh_keys"):
                logger.error(f"No SSH keys found for agent {self.agent_id}")
                return None
            
            # Find the first active key
            for key in data["ssh_keys"]:
                if not key.get("revoked", False):
                    return key["key_id"]
            
            logger.error("No active SSH keys found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting agent key ID: {str(e)}")
            return None
    
    async def authenticate(self) -> Tuple[bool, Optional[str]]:
        """
        Authenticate with the ArtCafe.ai platform using SSH key.
        
        Implements the challenge-response authentication flow:
        1. Request a challenge from the server
        2. Sign the challenge with the private key
        3. Send the signature to verify and get a JWT token
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            logger.info("Starting authentication with SSH key")
            
            # Step 1: Get challenge
            response = requests.post(
                f"{self.api_endpoint}/api/v1/auth/challenge",
                json={"agent_id": self.agent_id}
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to get challenge: {response.text}"
                logger.error(error_msg)
                return False, error_msg
            
            challenge_data = response.json()
            challenge = challenge_data["challenge"]
            
            logger.debug(f"Received challenge: {challenge[:10]}...")
            
            # Step 2: Sign challenge
            signature = self._sign_challenge(challenge)
            signature_b64 = base64.b64encode(signature).decode()
            
            # Get key_id from previous auth if available
            key_id = self.key_id
            
            if not key_id:
                # Try to fetch agent info to get associated keys
                key_id = await self._get_agent_key_id()
            
            if not key_id:
                error_msg = "No key ID available for authentication"
                logger.error(error_msg)
                return False, error_msg
            
            # Step 3: Verify signature
            response = requests.post(
                f"{self.api_endpoint}/api/v1/auth/verify",
                json={
                    "tenant_id": self.tenant_id,
                    "key_id": key_id,
                    "challenge": challenge,
                    "response": signature_b64,
                    "agent_id": self.agent_id
                }
            )
            
            if response.status_code != 200:
                error_msg = f"Authentication failed: {response.text}"
                logger.error(error_msg)
                return False, error_msg
            
            auth_result = response.json()
            
            if not auth_result["valid"]:
                error_msg = "Invalid signature"
                logger.error(error_msg)
                return False, error_msg
            
            # Store token and expiration
            self.jwt_token = auth_result["token"]
            payload = self._decode_jwt(self.jwt_token)
            self.jwt_expires_at = datetime.fromtimestamp(payload["exp"])
            self.key_id = key_id
            
            logger.info("Authentication successful")
            return True, None
                
        except Exception as e:
            error_msg = f"Authentication error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _decode_jwt(self, token: str) -> Dict[str, Any]:
        """
        Decode a JWT token without verification.
        
        Args:
            token: JWT token string
            
        Returns:
            Dict[str, Any]: Token payload
        """
        # Split token into parts
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")
        
        # Decode payload (part 1)
        padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload = base64.b64decode(padded)
        return json.loads(payload)
    
    def is_authenticated(self) -> bool:
        """
        Check if the provider is authenticated with a valid token.
        
        Returns:
            bool: True if authenticated with a valid token, False otherwise
        """
        if not self.jwt_token or not self.jwt_expires_at:
            return False
        
        # Check if token expires in the next 5 minutes
        now = datetime.now()
        margin = timedelta(minutes=5)
        return now + margin < self.jwt_expires_at
    
    def get_token(self) -> Optional[str]:
        """
        Get the current authentication token.
        
        Returns:
            str or None: Current token if authenticated, None otherwise
        """
        if self.is_authenticated():
            return self.jwt_token
        return None
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.
        
        Returns:
            Dict[str, str]: Headers containing authentication token and tenant ID
        """
        headers = {}
        
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        if self.tenant_id:
            headers["x-tenant-id"] = self.tenant_id
        
        return headers