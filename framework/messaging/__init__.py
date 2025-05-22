#!/usr/bin/env python3

from .provider import MessagingProvider
from .memory_provider import MemoryMessagingProvider
from .factory import MessagingProviderFactory
from .interface import MessagingInterface

# Conditionally import NATS provider
try:
    from .nats_provider import NATSProvider
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False

__all__ = [
    'MessagingProvider',
    'MemoryMessagingProvider',
    'MessagingProviderFactory',
    'MessagingInterface',
    'get_messaging',
    'create_token',
    'subscribe',
    'publish',
    'unsubscribe'
]

if NATS_AVAILABLE:
    __all__.append('NATSProvider')

# Global factory and default interface for simplified access
_factory = None
_default_interface = None

def initialize(config=None):
    """
    Initialize the messaging system.
    
    Args:
        config: Configuration object or None to use environment
    """
    from ..core.config import AgentConfig, DEFAULT_CONFIG
    
    global _factory, _default_interface
    
    # Create configuration if needed
    if config is None:
        config = AgentConfig(defaults=DEFAULT_CONFIG)
    
    # Create factory
    _factory = MessagingProviderFactory(config)
    
    # Create default interface
    _default_interface = MessagingInterface(config, "framework")
    _default_interface.authenticate(["*"])  # Full permissions for framework

def get_messaging(agent_id=None, permissions=None):
    """
    Get a messaging interface for an agent.
    
    Args:
        agent_id: ID of the agent, or None for default
        permissions: List of permissions to request, or None for default
        
    Returns:
        MessagingInterface: A messaging interface
    """
    global _factory, _default_interface
    
    if _factory is None:
        initialize()
    
    if agent_id is None:
        return _default_interface
    
    # Create a new interface for the agent
    from ..core.config import AgentConfig, DEFAULT_CONFIG
    config = AgentConfig(defaults=DEFAULT_CONFIG)
    
    interface = MessagingInterface(config, agent_id)
    
    if permissions:
        interface.authenticate(permissions)
    
    return interface

def create_token(agent_id, permissions):
    """
    Create an authentication token for an agent.
    
    Args:
        agent_id: The ID of the agent
        permissions: List of permissions to grant
        
    Returns:
        str: The authentication token
    """
    if _factory is None:
        initialize()
    
    return _factory.get_provider().create_token(agent_id, permissions)

def subscribe(token, topic, callback):
    """
    Subscribe to a topic with a callback function.
    
    Args:
        token: The authentication token
        topic: The topic to subscribe to
        callback: Function to call when a message is received
        
    Returns:
        bool: True if the subscription was successful, False otherwise
    """
    if _factory is None:
        initialize()
    
    return _factory.get_provider().subscribe(token, topic, callback)

def publish(token, topic, message):
    """
    Publish a message to a topic.
    
    Args:
        token: The authentication token
        topic: The topic to publish to
        message: The message to publish
        
    Returns:
        bool: True if the message was published successfully, False otherwise
    """
    if _factory is None:
        initialize()
    
    return _factory.get_provider().publish(token, topic, message)

def unsubscribe(token, topic):
    """
    Unsubscribe from a topic.
    
    Args:
        token: The authentication token
        topic: The topic to unsubscribe from
        
    Returns:
        bool: True if the unsubscription was successful, False otherwise
    """
    if _factory is None:
        initialize()
    
    return _factory.get_provider().unsubscribe(token, topic)