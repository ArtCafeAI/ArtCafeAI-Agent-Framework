#!/usr/bin/env python3

"""
SSH authentication provider for ArtCafe agents.

This provider uses SSH key authentication for secure WebSocket connections.
Authentication happens at connection time using challenge-response.
"""

import os
import base64
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from .auth_provider import AuthProvider

logger = logging.getLogger(__name__)


class SSHAuthProvider(AuthProvider):
    """
    SSH key authentication provider for ArtCafe agents.
    
    This provider implements secure WebSocket authentication using SSH keys.
    Authentication happens during WebSocket connection establishment
    using a challenge-response mechanism.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the SSH authentication provider.
        
        Args:
            config: Configuration dictionary containing auth settings
        """
        super().__init__(config)
        
        # SSH key configuration
        self.private_key_path = self._resolve_path(
            config.get("ssh_key", {}).get("private_key_path", "~/.ssh/artcafe_agent")
        )
        
        # Agent identity
        self.agent_id = config.get("agent_id")
        self.organization_id = config.get("organization_id") or config.get("tenant_id")
        
        if not self.organization_id:
            logger.warning("No organization_id provided. Multi-tenant features will be unavailable.")
        
        # Load private key
        self.private_key = self._load_private_key()
    
    def _resolve_path(self, path: str) -> str:
        """Resolve path with ~ expansion."""
        return os.path.expanduser(path)
    
    def _load_private_key(self):
        """Load SSH private key from file."""
        try:
            key_path = Path(self.private_key_path)
            if not key_path.exists():
                raise FileNotFoundError(f"Private key not found: {self.private_key_path}")
            
            with open(key_path, 'rb') as f:
                private_key = serialization.load_ssh_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            logger.info(f"Loaded SSH private key from {self.private_key_path}")
            return private_key
            
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise
    
    def sign_challenge(self, challenge: str) -> str:
        """
        Sign a challenge string with the SSH private key.
        
        Args:
            challenge: Challenge string to sign
            
        Returns:
            Base64-encoded signature
        """
        try:
            # Sign the challenge
            signature = self.private_key.sign(
                challenge.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Return base64-encoded signature
            return base64.b64encode(signature).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to sign challenge: {e}")
            raise
    
    async def authenticate(self) -> tuple[bool, Optional[str]]:
        """
        Prepare for authentication.
        
        Authentication happens during WebSocket connection establishment.
        
        Returns:
            (True, None) if ready to authenticate, (False, error) otherwise
        """
        # Verify we have the necessary credentials
        if not self.private_key:
            return False, "Private key not loaded"
        return True, None
    
    def is_authenticated(self) -> bool:
        """
        Check if we have necessary credentials for authentication.
        
        Returns:
            True if private key is loaded
        """
        return self.private_key is not None
    
    def get_token(self) -> Optional[str]:
        """
        Get authentication token if available.
        
        Returns:
            None (SSH authentication doesn't use tokens)
        """
        return None
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.
        
        Returns:
            Headers with organization ID if available
        """
        headers = {}
        
        if self.organization_id:
            headers["x-tenant-id"] = self.organization_id  # API still uses tenant_id
        
        return headers
    
    def get_connection_params(self) -> Dict[str, str]:
        """
        Get parameters for WebSocket connection.
        
        Returns:
            Dict with agent_id and organization_id
        """
        params = {
            "agent_id": self.agent_id,
        }
        
        if self.organization_id:
            params["tenant_id"] = self.organization_id  # API uses tenant_id
            
        return params
