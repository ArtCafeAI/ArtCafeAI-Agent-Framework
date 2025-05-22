"""
Chained Workflow - Sequential execution of steps.

Implements the prompt chaining pattern where each step's output
becomes the input for the next step.
"""

from typing import Any, Dict, List, Optional
from .base import Workflow, WorkflowStep, WorkflowResult, StepStatus


class ChainedWorkflow(Workflow):
    """
    A workflow that executes steps sequentially, passing output to input.
    
    Example:
        ```python
        workflow = ChainedWorkflow("process_data", [
            WorkflowStep("load", load_data),
            WorkflowStep("validate", validate_data),
            WorkflowStep("transform", transform_data),
            WorkflowStep("save", save_data)
        ])
        
        result = await workflow.execute({"file": "data.csv"})
        ```
    """
    
    def __init__(
        self,
        name: str,
        steps: List[WorkflowStep],
        stop_on_error: bool = True
    ):
        """
        Initialize a chained workflow.
        
        Args:
            name: Workflow name
            steps: Sequential steps to execute
            stop_on_error: Stop execution if a step fails
        """
        super().__init__(name, steps)
        self.stop_on_error = stop_on_error
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute steps sequentially, chaining outputs to inputs.
        
        Args:
            context: Initial context
            
        Returns:
            WorkflowResult with final output
        """
        result = WorkflowResult(
            workflow_name=self.name,
            status=StepStatus.RUNNING
        )
        
        current_context = context.copy()
        
        for i, step in enumerate(self.steps):
            # Execute step
            step_result = await self.execute_step(step, current_context)
            result.steps.append(step_result)
            
            # Handle step result
            if step_result.status == StepStatus.FAILED:
                if self.stop_on_error:
                    result.complete()
                    self.result = result
                    return result
            
            elif step_result.status == StepStatus.COMPLETED:
                # Chain output to next step's input
                if step_result.output is not None:
                    if isinstance(step_result.output, dict):
                        current_context.update(step_result.output)
                    else:
                        # Store non-dict outputs with step name as key
                        current_context[f"{step.name}_output"] = step_result.output
                        
                    # Also store in a chain for easy access
                    if "chain" not in current_context:
                        current_context["chain"] = []
                    current_context["chain"].append({
                        "step": step.name,
                        "output": step_result.output
                    })
        
        # Set final output
        result.output = current_context
        result.complete()
        self.result = result
        return result
    
    @classmethod
    def from_functions(
        cls,
        name: str,
        functions: List[tuple],
        stop_on_error: bool = True
    ) -> "ChainedWorkflow":
        """
        Create a workflow from a list of functions.
        
        Args:
            name: Workflow name
            functions: List of (name, function) tuples
            stop_on_error: Stop on error flag
            
        Returns:
            ChainedWorkflow instance
            
        Example:
            ```python
            workflow = ChainedWorkflow.from_functions(
                "pipeline",
                [
                    ("parse", parse_input),
                    ("process", process_data),
                    ("format", format_output)
                ]
            )
            ```
        """
        steps = [
            WorkflowStep(name=name, func=func)
            for name, func in functions
        ]
        return cls(name, steps, stop_on_error)