"""
Workflow patterns for agent coordination.

Implements industry-standard workflow patterns:
- Prompt Chaining
- Routing
- Parallelization
- Orchestrator-Workers
"""

from .base import Workflow, WorkflowStep, WorkflowResult
from .chained import ChainedWorkflow
from .routing import RoutingWorkflow
from .parallel import ParallelWorkflow
from .orchestrator import OrchestratorWorkflow

__all__ = [
    'Workflow',
    'WorkflowStep',
    'WorkflowResult',
    'ChainedWorkflow',
    'RoutingWorkflow',
    'ParallelWorkflow',
    'OrchestratorWorkflow'
]