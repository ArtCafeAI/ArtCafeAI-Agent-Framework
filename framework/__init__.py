#!/usr/bin/env python3

"""
AURA Agent Framework

A framework for building multi-agent systems with AWS integrations.
"""

import logging
import os

from .core.config import AgentConfig, DEFAULT_CONFIG
from .core.base_agent import BaseAgent
from .core.enhanced_agent import EnhancedAgent
from .messaging import initialize as initialize_messaging
from .messaging import get_messaging, create_token, subscribe, publish, unsubscribe

__version__ = "0.1.0"

# Configure logging based on environment
DEFAULT_LOG_LEVEL = os.environ.get("AGENT_FRAMEWORK_LOG_LEVEL", "INFO")
DEFAULT_LOG_FORMAT = os.environ.get(
    "AGENT_FRAMEWORK_LOG_FORMAT", 
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Setup framework-wide logging
logging.basicConfig(
    level=getattr(logging, DEFAULT_LOG_LEVEL),
    format=DEFAULT_LOG_FORMAT
)

logger = logging.getLogger("AgentFramework")

# Export public API
__all__ = [
    'BaseAgent',
    'EnhancedAgent',
    'AgentConfig',
    'initialize',
    'get_messaging',
    'create_token',
    'subscribe',
    'publish',
    'unsubscribe',
    '__version__'
]

def initialize(config_files=None):
    """
    Initialize the agent framework.
    
    Args:
        config_files: Optional list of configuration file paths
    """
    logger.info(f"Initializing AURA Agent Framework v{__version__}")
    
    # Create configuration
    config = AgentConfig(config_files=config_files, defaults=DEFAULT_CONFIG)
    
    # Initialize messaging system
    initialize_messaging(config)
    
    logger.info("AURA Agent Framework initialized")
    
    return config