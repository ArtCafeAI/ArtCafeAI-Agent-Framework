#!/usr/bin/env python3

import logging
from typing import Dict, Any, Optional

from .llm_provider import LLMProvider
from .anthropic_provider import AnthropicProvider

logger = logging.getLogger("AgentFramework.LLM.Factory")

# Import other providers conditionally to avoid unnecessary dependencies
try:
    from .openai_provider import OpenAIProvider
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.debug("OpenAI provider not available")

try:
    from .bedrock_provider import BedrockProvider
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False
    logger.debug("Bedrock provider not available")

try:
    from .local_provider import LocalProvider
    LOCAL_AVAILABLE = True
except ImportError:
    LOCAL_AVAILABLE = False
    logger.debug("Local provider not available")

def get_llm_provider(config: Dict[str, Any]) -> LLMProvider:
    """
    Factory function to create an appropriate LLM provider.
    
    Args:
        config: LLM configuration dictionary
        
    Returns:
        LLMProvider: Appropriate provider instance based on config
        
    Raises:
        ValueError: If the requested provider is not available
    """
    provider_name = config.get("provider", "anthropic").lower()
    
    if provider_name == "anthropic":
        return AnthropicProvider(config)
    elif provider_name == "openai":
        if not OPENAI_AVAILABLE:
            raise ValueError("OpenAI provider requested but not available. Install with: pip install openai")
        return OpenAIProvider(config)
    elif provider_name == "bedrock":
        if not BEDROCK_AVAILABLE:
            raise ValueError("Bedrock provider requested but not available. Install with: pip install boto3")
        return BedrockProvider(config)
    elif provider_name == "local":
        if not LOCAL_AVAILABLE:
            raise ValueError("Local provider requested but not available.")
        return LocalProvider(config)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")

def register_provider(provider_name: str, provider_class) -> None:
    """
    Register a custom LLM provider.
    
    Args:
        provider_name: Name of the provider for configuration
        provider_class: Class implementing the LLMProvider interface
    """
    global _provider_registry
    _provider_registry[provider_name.lower()] = provider_class
    logger.info(f"Registered custom LLM provider: {provider_name}")

# Registry of custom providers
_provider_registry = {}