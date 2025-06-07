#!/usr/bin/env python3

"""
ArtCafe Agent Framework

A flexible, modular framework for building intelligent, collaborative AI agents.
"""

import logging
import os

from .core.agent import Agent
from .core.config import AgentConfig
from .messaging import initialize as initialize_messaging
from .messaging import get_messaging, subscribe, publish, unsubscribe

__version__ = "0.4.2"

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
    # Main agent class
    'Agent',
    # Configuration
    'AgentConfig',
    # Messaging functions (if needed separately)
    'subscribe',
    'publish',
    'unsubscribe',
    # Version
    '__version__'
]

