#!/usr/bin/env python3

"""
ArtCafe Agent Framework

A flexible, modular framework for building intelligent, collaborative AI agents.
"""

import logging
import os

from .core.config import AgentConfig, DEFAULT_CONFIG
from .core.base_agent import BaseAgent
from .core.enhanced_agent import EnhancedAgent
from .core.simple_agent import SimpleAgent, create_agent
from .core.augmented_llm_agent import AugmentedLLMAgent, create_llm_agent
from .core.verified_agent import VerifiedAgent, verify_input, verify_output
from .core.budget_aware_agent import BudgetAwareAgent, Budget, CostUnit
from .messaging import initialize as initialize_messaging
from .messaging import get_messaging, create_token, subscribe, publish, unsubscribe
from .workflows import (
    ChainedWorkflow, RoutingWorkflow, ParallelWorkflow, OrchestratorWorkflow,
    Workflow, WorkflowStep, WorkflowResult
)

__version__ = "0.4.0"

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
    # Core agents
    'BaseAgent',
    'EnhancedAgent',
    'SimpleAgent',
    'AugmentedLLMAgent',
    'VerifiedAgent',
    'BudgetAwareAgent',
    # Factory functions
    'create_agent',
    'create_llm_agent',
    # Decorators
    'verify_input',
    'verify_output',
    # Budget management
    'Budget',
    'CostUnit',
    # Workflows
    'Workflow',
    'WorkflowStep',
    'WorkflowResult',
    'ChainedWorkflow',
    'RoutingWorkflow',
    'ParallelWorkflow',
    'OrchestratorWorkflow',
    # Configuration
    'AgentConfig',
    # Framework functions
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
    logger.info(f"Initializing ArtCafe Agent Framework v{__version__}")
    
    # Create configuration
    config = AgentConfig(config_files=config_files, defaults=DEFAULT_CONFIG)
    
    # Initialize messaging system
    initialize_messaging(config)
    
    logger.info("ArtCafe Agent Framework initialized")
    
    return config