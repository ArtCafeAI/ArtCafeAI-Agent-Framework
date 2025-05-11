#!/usr/bin/env python3

import abc
import uuid
import time
from typing import Dict, List, Any, Callable, Optional

class MessagingProvider(abc.ABC):
    """
    Abstract base class for messaging providers.
    
    This class defines the interface that all messaging providers must implement,
    allowing the framework to use different underlying messaging systems (e.g.,
    in-memory, AWS IoT Core, Kafka, etc.) through a consistent interface.
    """
    
    @abc.abstractmethod
    def create_token(self, agent_id: str, permissions: List[str]) -> str:
        """
        Create an authentication token for an agent.
        
        Args:
            agent_id: The ID of the agent
            permissions: List of permission strings defining what the agent can do
            
        Returns:
            str: The authentication token
        """
        pass
    
    @abc.abstractmethod
    def verify_permission(self, token: str, action: str, topic: str) -> bool:
        """
        Verify if a token has permission to perform an action on a topic.
        
        Args:
            token: The authentication token
            action: The action to perform (e.g., 'publish', 'subscribe')
            topic: The topic to perform the action on
            
        Returns:
            bool: True if the action is permitted, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def subscribe(self, token: str, topic: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Subscribe to a topic with a callback function.
        
        Args:
            token: The authentication token
            topic: The topic to subscribe to
            callback: Function to call when a message is received
            
        Returns:
            bool: True if the subscription was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def unsubscribe(self, token: str, topic: str) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            token: The authentication token
            topic: The topic to unsubscribe from
            
        Returns:
            bool: True if the unsubscription was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def publish(self, token: str, topic: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to a topic.
        
        Args:
            token: The authentication token
            topic: The topic to publish to
            message: The message to publish
            
        Returns:
            bool: True if the message was published successfully, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def start(self) -> bool:
        """
        Start the messaging provider, initializing resources.
        
        Returns:
            bool: True if the provider was started successfully, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def stop(self) -> bool:
        """
        Stop the messaging provider, cleaning up resources.
        
        Returns:
            bool: True if the provider was stopped successfully, False otherwise
        """
        pass
    
    def enrich_message(self, topic: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a message with metadata before publishing.
        
        Args:
            topic: The topic the message will be published to
            message: The message payload
            
        Returns:
            Dict[str, Any]: The enriched message with metadata
        """
        # Create a copy of the message to avoid modifying the original
        enriched_message = {
            "data": message,
            "topic": topic,
            "timestamp": time.time(),
            "message_id": str(uuid.uuid4())
        }
        
        return enriched_message