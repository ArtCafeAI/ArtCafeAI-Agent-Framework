#!/usr/bin/env python3

import abc
import uuid
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("AgentFramework.Auth.Provider")

class AuthProvider(abc.ABC):
    """
    Abstract base class for authentication providers.
    
    This class defines the interface that all authentication providers must implement,
    allowing the framework to use different authentication mechanisms while maintaining
    a consistent interface.
    """
    
    @abc.abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> Optional[str]:
        """
        Authenticate a user or agent and return a token.
        
        Args:
            credentials: Dictionary of credentials for authentication
            
        Returns:
            Optional[str]: Authentication token if successful, None otherwise
        """
        pass
    
    @abc.abstractmethod
    def validate_token(self, token: str) -> bool:
        """
        Validate an authentication token.
        
        Args:
            token: The token to validate
            
        Returns:
            bool: True if the token is valid, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an authentication token.
        
        Args:
            token: The token to get information about
            
        Returns:
            Optional[Dict[str, Any]]: Token information if valid, None otherwise
        """
        pass
    
    @abc.abstractmethod
    def revoke_token(self, token: str) -> bool:
        """
        Revoke an authentication token.
        
        Args:
            token: The token to revoke
            
        Returns:
            bool: True if the token was revoked, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def get_permissions(self, token: str) -> List[str]:
        """
        Get the permissions associated with a token.
        
        Args:
            token: The authentication token
            
        Returns:
            List[str]: List of permission strings
        """
        pass

class SimpleAuthProvider(AuthProvider):
    """
    Simple in-memory authentication provider for testing and development.
    
    This provider stores tokens and credentials in memory and provides basic
    authentication functionality without external dependencies.
    
    Attributes:
        _tokens (Dict[str, Dict[str, Any]]): Map of tokens to token information
        _credentials (Dict[str, Dict[str, Any]]): Map of usernames to credentials
    """
    
    def __init__(self):
        """Initialize a new simple authentication provider."""
        self._tokens = {}
        self._credentials = {}
        
        logger.debug("Initialized simple authentication provider")
    
    def add_user(self, username: str, password: str, permissions: List[str]) -> bool:
        """
        Add a user to the authentication system.
        
        Args:
            username: The username
            password: The password
            permissions: List of permissions to grant
            
        Returns:
            bool: True if the user was added, False otherwise
        """
        if username in self._credentials:
            logger.warning(f"User already exists: {username}")
            return False
        
        self._credentials[username] = {
            "password": password,
            "permissions": permissions,
            "created_at": time.time()
        }
        
        logger.info(f"Added user: {username}")
        return True
    
    def authenticate(self, credentials: Dict[str, Any]) -> Optional[str]:
        """
        Authenticate a user and return a token.
        
        Args:
            credentials: Dictionary with 'username' and 'password' keys
            
        Returns:
            Optional[str]: Authentication token if successful, None otherwise
        """
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            logger.warning("Missing username or password in credentials")
            return None
        
        if username not in self._credentials:
            logger.warning(f"User not found: {username}")
            return None
        
        if self._credentials[username]["password"] != password:
            logger.warning(f"Invalid password for user: {username}")
            return None
        
        # Generate a new token
        token = str(uuid.uuid4())
        
        # Store token information
        self._tokens[token] = {
            "username": username,
            "permissions": self._credentials[username]["permissions"],
            "created_at": time.time(),
            "expires_at": time.time() + 3600  # 1 hour expiration
        }
        
        logger.info(f"Authenticated user: {username}")
        return token
    
    def validate_token(self, token: str) -> bool:
        """
        Validate an authentication token.
        
        Args:
            token: The token to validate
            
        Returns:
            bool: True if the token is valid, False otherwise
        """
        if token not in self._tokens:
            return False
        
        # Check expiration
        if self._tokens[token]["expires_at"] < time.time():
            logger.info(f"Token expired: {token}")
            del self._tokens[token]
            return False
        
        return True
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an authentication token.
        
        Args:
            token: The token to get information about
            
        Returns:
            Optional[Dict[str, Any]]: Token information if valid, None otherwise
        """
        if not self.validate_token(token):
            return None
        
        return self._tokens[token].copy()
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke an authentication token.
        
        Args:
            token: The token to revoke
            
        Returns:
            bool: True if the token was revoked, False otherwise
        """
        if token not in self._tokens:
            return False
        
        del self._tokens[token]
        logger.info(f"Revoked token: {token}")
        return True
    
    def get_permissions(self, token: str) -> List[str]:
        """
        Get the permissions associated with a token.
        
        Args:
            token: The authentication token
            
        Returns:
            List[str]: List of permission strings
        """
        if not self.validate_token(token):
            return []
        
        return self._tokens[token]["permissions"]