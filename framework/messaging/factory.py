#!/usr/bin/env python3

import logging
from typing import Dict, Any, Optional

from ..core.config import AgentConfig
from .provider import MessagingProvider
from .memory_provider import MemoryMessagingProvider

# Conditionally import AWS IoT provider
try:
    from .aws_iot_provider import AWSIoTMessagingProvider
    AWS_IOT_AVAILABLE = True
except ImportError:
    AWS_IOT_AVAILABLE = False

# Conditionally import NATS provider
try:
    from .nats_provider import NATSProvider
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False

logger = logging.getLogger("AgentFramework.Messaging.Factory")

class MessagingProviderFactory:
    """
    Factory for creating messaging provider instances.
    
    This factory creates and manages messaging provider instances based on the
    configuration. It supports different provider types (e.g., in-memory, AWS IoT)
    and ensures only one instance of each type is created.
    
    Attributes:
        _config (AgentConfig): Configuration for messaging providers
        _providers (Dict[str, MessagingProvider]): Cache of provider instances
        _default_provider (str): Name of the default provider
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize a new messaging provider factory.
        
        Args:
            config: Configuration for messaging providers
        """
        self._config = config
        self._providers = {}
        self._default_provider = config.get("messaging.provider", "memory")
        
        logger.debug(f"Initialized messaging provider factory with default: {self._default_provider}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> MessagingProvider:
        """
        Get a messaging provider instance.
        
        Args:
            provider_name: Name of the provider to get, or None for the default
            
        Returns:
            MessagingProvider: The messaging provider instance
            
        Raises:
            ValueError: If the provider type is unknown or cannot be created
        """
        provider_name = provider_name or self._default_provider
        
        # Return cached provider if available
        if provider_name in self._providers:
            return self._providers[provider_name]
        
        # Create a new provider based on the name
        if provider_name == "memory":
            provider = self._create_memory_provider()
        elif provider_name == "aws_iot":
            provider = self._create_aws_iot_provider()
        elif provider_name == "nats":
            provider = self._create_nats_provider()
        else:
            raise ValueError(f"Unknown messaging provider type: {provider_name}")
        
        # Cache and return the provider
        self._providers[provider_name] = provider
        return provider
    
    def _create_memory_provider(self) -> MemoryMessagingProvider:
        """
        Create a memory-based messaging provider.
        
        Returns:
            MemoryMessagingProvider: The new provider instance
        """
        use_ipc = self._config.get("messaging.memory.use_ipc", True)
        ipc_dir = self._config.get("messaging.memory.ipc_dir", None)
        
        provider = MemoryMessagingProvider(use_ipc=use_ipc, ipc_dir=ipc_dir)
        provider.start()
        
        logger.info("Created memory messaging provider")
        return provider
    
    def _create_aws_iot_provider(self) -> MessagingProvider:
        """
        Create an AWS IoT messaging provider.
        
        Returns:
            AWSIoTMessagingProvider: The new provider instance
            
        Raises:
            ValueError: If AWS IoT is not available or configuration is missing
        """
        if not AWS_IOT_AVAILABLE:
            raise ValueError(
                "AWS IoT provider is not available. Please install the required dependencies: "
                "pip install awsiotsdk boto3"
            )
        
        # Get AWS IoT configuration
        endpoint = self._config.get("messaging.aws_iot.endpoint")
        cert_path = self._config.get("messaging.aws_iot.cert_path")
        key_path = self._config.get("messaging.aws_iot.key_path")
        ca_path = self._config.get("messaging.aws_iot.ca_path")
        region = self._config.get("messaging.aws_iot.region", "us-east-1")
        client_id = self._config.get("messaging.aws_iot.client_id", None)
        
        # Validate required configuration
        if not endpoint:
            raise ValueError("Missing required AWS IoT endpoint in configuration")
        if not cert_path:
            raise ValueError("Missing required certificate path in AWS IoT configuration")
        if not key_path:
            raise ValueError("Missing required private key path in AWS IoT configuration")
        if not ca_path:
            raise ValueError("Missing required CA certificate path in AWS IoT configuration")
        
        # Create and start the provider
        provider = AWSIoTMessagingProvider(
            endpoint=endpoint,
            cert_path=cert_path,
            key_path=key_path,
            ca_path=ca_path,
            client_id=client_id,
            region=region
        )
        provider.start()
        
        logger.info(f"Created AWS IoT messaging provider for endpoint {endpoint}")
        return provider
    
    def _create_nats_provider(self) -> MessagingProvider:
        """
        Create a NATS messaging provider.
        
        Returns:
            NATSProvider: The new provider instance
            
        Raises:
            ValueError: If NATS is not available
        """
        if not NATS_AVAILABLE:
            raise ValueError(
                "NATS provider is not available. Please install the required dependencies: "
                "pip install nats-py"
            )
        
        provider = NATSProvider(self._config)
        provider.start()
        
        logger.info("Created NATS messaging provider")
        return provider
    
    def shutdown(self) -> None:
        """
        Shutdown all messaging providers.
        
        This method stops all providers that have been created by this factory.
        """
        for name, provider in self._providers.items():
            try:
                provider.stop()
                logger.info(f"Stopped messaging provider: {name}")
            except Exception as e:
                logger.error(f"Error stopping messaging provider {name}: {e}")
        
        self._providers = {}