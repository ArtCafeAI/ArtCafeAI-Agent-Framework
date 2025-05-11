#!/usr/bin/env python3

import logging
from typing import Dict, List, Any, Callable, Optional

from ..core.config import AgentConfig
from .factory import MessagingProviderFactory
from .provider import MessagingProvider

logger = logging.getLogger("AgentFramework.Messaging.Interface")

class MessagingInterface:
    """
    Interface for agent messaging functionality.
    
    This class provides a simplified, consistent interface for agents to use
    messaging services, abstracting away the details of the underlying provider.
    It handles authentication, permission management, and message routing.
    
    Attributes:
        _config (AgentConfig): Configuration for messaging
        _factory (MessagingProviderFactory): Factory for creating providers
        _provider (MessagingProvider): The active messaging provider
        _token (Optional[str]): Authentication token for this interface
        _agent_id (str): ID of the agent using this interface
    """
    
    def __init__(self, config: AgentConfig, agent_id: str):
        """
        Initialize a new messaging interface.
        
        Args:
            config: Configuration for messaging
            agent_id: ID of the agent using this interface
        """
        self._config = config
        self._agent_id = agent_id
        self._factory = MessagingProviderFactory(config)
        
        # Get the provider based on configuration
        provider_name = config.get("messaging.provider", "memory")
        self._provider = self._factory.get_provider(provider_name)
        
        # Default permissions
        self._permissions = []
        self._token = None
        
        logger.debug(f"Initialized messaging interface for agent {agent_id} using provider {provider_name}")
    
    def authenticate(self, permissions: List[str]) -> bool:
        """
        Authenticate the interface with the messaging provider.
        
        Args:
            permissions: List of permissions to request
            
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            self._token = self._provider.create_token(self._agent_id, permissions)
            self._permissions = permissions
            
            logger.info(f"Authenticated agent {self._agent_id} with {len(permissions)} permissions")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating agent {self._agent_id}: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Subscribe to a topic with a callback function.
        
        Args:
            topic: The topic to subscribe to
            callback: Function to call when a message is received
            
        Returns:
            bool: True if the subscription was successful, False otherwise
            
        Raises:
            ValueError: If the interface is not authenticated
        """
        if not self._token:
            raise ValueError("Messaging interface is not authenticated")
        
        return self._provider.subscribe(self._token, topic, callback)
    
    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: The topic to unsubscribe from
            
        Returns:
            bool: True if the unsubscription was successful, False otherwise
            
        Raises:
            ValueError: If the interface is not authenticated
        """
        if not self._token:
            raise ValueError("Messaging interface is not authenticated")
        
        return self._provider.unsubscribe(self._token, topic)
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to a topic.
        
        Args:
            topic: The topic to publish to
            message: The message to publish
            
        Returns:
            bool: True if the message was published successfully, False otherwise
            
        Raises:
            ValueError: If the interface is not authenticated
        """
        if not self._token:
            raise ValueError("Messaging interface is not authenticated")
        
        return self._provider.publish(self._token, topic, message)
    
    def get_token(self) -> Optional[str]:
        """
        Get the authentication token for this interface.
        
        Returns:
            Optional[str]: The authentication token, or None if not authenticated
        """
        return self._token
    
    def has_permission(self, action: str, topic: str) -> bool:
        """
        Check if the interface has permission to perform an action on a topic.
        
        Args:
            action: The action to perform (e.g., 'publish', 'subscribe')
            topic: The topic to perform the action on
            
        Returns:
            bool: True if the action is permitted, False otherwise
        """
        if not self._token:
            return False
        
        return self._provider.verify_permission(self._token, action, topic)
    
    def close(self) -> None:
        """
        Close the messaging interface and clean up resources.
        
        This method unsubscribes from all topics and resets the authentication state.
        """
        if not self._token:
            return
        
        # Unsubscribe from topics would go here
        # In a real implementation, we would track subscriptions and unsubscribe from them
        
        self._token = None
        logger.info(f"Closed messaging interface for agent {self._agent_id}")