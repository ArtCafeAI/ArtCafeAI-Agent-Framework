"""
Parallel Workflow - Execute multiple steps concurrently.

Implements the parallelization pattern for running multiple
tasks simultaneously to improve performance.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union
from .base import Workflow, WorkflowStep, WorkflowResult, StepStatus, StepResult


class ParallelWorkflow(Workflow):
    """
    A workflow that executes multiple steps in parallel.
    
    Example:
        ```python
        workflow = ParallelWorkflow("data_enrichment", [
            WorkflowStep("fetch_user", fetch_user_data),
            WorkflowStep("fetch_orders", fetch_order_history),
            WorkflowStep("fetch_recommendations", get_recommendations)
        ])
        
        # All three steps run concurrently
        result = await workflow.execute({"user_id": "123"})
        ```
    """
    
    def __init__(
        self,
        name: str,
        steps: List[WorkflowStep],
        max_concurrency: Optional[int] = None,
        fail_fast: bool = False
    ):
        """
        Initialize a parallel workflow.
        
        Args:
            name: Workflow name
            steps: Steps to execute in parallel
            max_concurrency: Maximum number of concurrent executions
            fail_fast: Stop all tasks if one fails
        """
        super().__init__(name, steps)
        self.max_concurrency = max_concurrency
        self.fail_fast = fail_fast
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute all steps in parallel.
        
        Args:
            context: Shared context for all steps
            
        Returns:
            WorkflowResult with outputs from all steps
        """
        result = WorkflowResult(
            workflow_name=self.name,
            status=StepStatus.RUNNING
        )
        
        # Create semaphore for concurrency control
        semaphore = None
        if self.max_concurrency:
            semaphore = asyncio.Semaphore(self.max_concurrency)
        
        # Create tasks for all steps
        tasks = []
        for step in self.steps:
            task = self._execute_with_semaphore(step, context.copy(), semaphore)
            tasks.append(task)
        
        # Execute all tasks
        if self.fail_fast:
            # Use gather with return_exceptions=False to fail fast
            try:
                step_results = await asyncio.gather(*tasks, return_exceptions=False)
            except Exception as e:
                # Cancel remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
                
                # Wait for cancellations
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Add error to result
                result.error = f"Task failed: {str(e)}"
                result.complete()
                self.result = result
                return result
        else:
            # Execute all tasks regardless of failures
            step_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        outputs = {}
        for i, step_result in enumerate(step_results):
            if isinstance(step_result, Exception):
                # Create error result for this step
                error_result = StepResult(
                    step_name=self.steps[i].name,
                    status=StepStatus.FAILED,
                    error=str(step_result)
                )
                error_result.complete()
                result.steps.append(error_result)
            else:
                result.steps.append(step_result)
                if step_result.status == StepStatus.COMPLETED and step_result.output:
                    outputs[step_result.step_name] = step_result.output
        
        # Set combined output
        result.output = outputs
        result.metadata["total_steps"] = len(self.steps)
        result.metadata["successful_steps"] = sum(
            1 for s in result.steps if s.status == StepStatus.COMPLETED
        )
        
        result.complete()
        self.result = result
        return result
    
    async def _execute_with_semaphore(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
        semaphore: Optional[asyncio.Semaphore]
    ) -> StepResult:
        """Execute a step with optional semaphore for concurrency control."""
        if semaphore:
            async with semaphore:
                return await self.execute_step(step, context)
        else:
            return await self.execute_step(step, context)
    
    def add_parallel_group(self, group_name: str, steps: List[WorkflowStep]):
        """
        Add a group of steps to execute in parallel.
        
        Args:
            group_name: Name for this group
            steps: Steps to add
        """
        for step in steps:
            # Prefix step names with group
            step.name = f"{group_name}.{step.name}"
            self.steps.append(step)
    
    @classmethod
    def from_functions(
        cls,
        name: str,
        functions: List[Union[tuple, Callable]],
        max_concurrency: Optional[int] = None,
        fail_fast: bool = False
    ) -> "ParallelWorkflow":
        """
        Create a parallel workflow from functions.
        
        Args:
            name: Workflow name
            functions: List of functions or (name, function) tuples
            max_concurrency: Maximum concurrent executions
            fail_fast: Stop on first failure
            
        Returns:
            ParallelWorkflow instance
            
        Example:
            ```python
            workflow = ParallelWorkflow.from_functions(
                "multi_fetch",
                [
                    ("api1", fetch_from_api1),
                    ("api2", fetch_from_api2),
                    ("api3", fetch_from_api3)
                ],
                max_concurrency=2  # Only 2 APIs called at once
            )
            ```
        """
        steps = []
        for item in functions:
            if isinstance(item, tuple):
                name, func = item
                steps.append(WorkflowStep(name=name, func=func))
            else:
                # Use function name
                steps.append(WorkflowStep(name=item.__name__, func=item))
        
        return cls(name, steps, max_concurrency, fail_fast)