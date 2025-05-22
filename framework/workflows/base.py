"""
Base classes for workflow patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    func: Callable
    description: Optional[str] = None
    retry_count: int = 0
    timeout: Optional[float] = None
    condition: Optional[Callable] = None  # Skip if returns False
    
    
@dataclass
class StepResult:
    """Result of executing a workflow step."""
    step_name: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    
    def complete(self, output: Any = None, error: Optional[str] = None):
        """Mark step as complete."""
        self.end_time = datetime.utcnow()
        self.duration = (self.end_time - self.start_time).total_seconds()
        if error:
            self.status = StepStatus.FAILED
            self.error = error
        else:
            self.status = StepStatus.COMPLETED
            self.output = output


@dataclass
class WorkflowResult:
    """Result of executing a workflow."""
    workflow_name: str
    status: StepStatus
    steps: List[StepResult] = field(default_factory=list)
    output: Any = None
    error: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self):
        """Mark workflow as complete."""
        self.end_time = datetime.utcnow()
        self.duration = (self.end_time - self.start_time).total_seconds()
        
        # Determine overall status
        if any(step.status == StepStatus.FAILED for step in self.steps):
            self.status = StepStatus.FAILED
            failed_steps = [s for s in self.steps if s.status == StepStatus.FAILED]
            self.error = f"Failed steps: {', '.join(s.step_name for s in failed_steps)}"
        else:
            self.status = StepStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "metadata": self.metadata,
            "steps": [
                {
                    "name": step.step_name,
                    "status": step.status.value,
                    "error": step.error,
                    "duration": step.duration
                }
                for step in self.steps
            ]
        }


class Workflow(ABC):
    """
    Abstract base class for workflows.
    
    A workflow coordinates multiple steps to accomplish a complex task.
    """
    
    def __init__(self, name: str, steps: List[WorkflowStep]):
        """
        Initialize a workflow.
        
        Args:
            name: Workflow name
            steps: List of workflow steps
        """
        self.name = name
        self.steps = steps
        self.result = None
        
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the workflow.
        
        Args:
            context: Initial context for the workflow
            
        Returns:
            WorkflowResult
        """
        pass
    
    async def execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> StepResult:
        """
        Execute a single step.
        
        Args:
            step: The step to execute
            context: Current context
            
        Returns:
            StepResult
        """
        result = StepResult(step_name=step.name, status=StepStatus.RUNNING)
        
        # Check condition
        if step.condition and not step.condition(context):
            result.status = StepStatus.SKIPPED
            return result
        
        # Execute with retries
        last_error = None
        for attempt in range(step.retry_count + 1):
            try:
                # Execute step function
                if asyncio.iscoroutinefunction(step.func):
                    output = await step.func(context)
                else:
                    output = step.func(context)
                
                result.complete(output=output)
                return result
                
            except Exception as e:
                last_error = str(e)
                if attempt < step.retry_count:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        # All retries failed
        result.complete(error=last_error)
        return result
    
    def add_step(self, step: WorkflowStep):
        """Add a step to the workflow."""
        self.steps.append(step)
    
    def get_result(self) -> Optional[WorkflowResult]:
        """Get the last execution result."""
        return self.result


# Import asyncio here to avoid circular imports
import asyncio