"""
Orchestrator Workflow - Dynamic task orchestration with workers.

Implements the orchestrator-workers pattern where a central orchestrator
dynamically breaks down tasks and delegates to specialized workers.
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass
from .base import Workflow, WorkflowStep, WorkflowResult, StepStatus


@dataclass
class WorkerTask:
    """A task to be executed by a worker."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class OrchestratorWorkflow(Workflow):
    """
    A workflow that orchestrates dynamic task execution with workers.
    
    The orchestrator analyzes the input, breaks it into subtasks,
    manages dependencies, and coordinates worker execution.
    
    Example:
        ```python
        workflow = OrchestratorWorkflow("document_processing")
        
        # Register worker types
        workflow.register_worker("extract", extract_text)
        workflow.register_worker("analyze", analyze_content)
        workflow.register_worker("summarize", create_summary)
        
        # Define task breakdown logic
        @workflow.task_planner
        def plan_tasks(context):
            return [
                WorkerTask("t1", "extract", {"doc": context["document"]}),
                WorkerTask("t2", "analyze", {"ref": "t1"}, dependencies=["t1"]),
                WorkerTask("t3", "summarize", {"ref": "t2"}, dependencies=["t2"])
            ]
        
        result = await workflow.execute({"document": "report.pdf"})
        ```
    """
    
    def __init__(
        self,
        name: str,
        max_workers: int = 5,
        worker_timeout: Optional[float] = None
    ):
        """
        Initialize an orchestrator workflow.
        
        Args:
            name: Workflow name
            max_workers: Maximum concurrent workers
            worker_timeout: Timeout for individual worker tasks
        """
        super().__init__(name, [])
        self.workers: Dict[str, Callable] = {}
        self.task_planner: Optional[Callable] = None
        self.max_workers = max_workers
        self.worker_timeout = worker_timeout
        self.task_results: Dict[str, Any] = {}
    
    def register_worker(self, worker_type: str, handler: Callable):
        """
        Register a worker handler for a specific task type.
        
        Args:
            worker_type: Type of tasks this worker handles
            handler: Function to handle the task
        """
        self.workers[worker_type] = handler
    
    def set_task_planner(self, planner: Callable[[Dict[str, Any]], List[WorkerTask]]):
        """
        Set the task planning function.
        
        Args:
            planner: Function that takes context and returns list of tasks
        """
        self.task_planner = planner
    
    def task_planner(self, func: Callable) -> Callable:
        """Decorator to set task planner."""
        self.task_planner = func
        return func
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the orchestrator workflow.
        
        Args:
            context: Input context
            
        Returns:
            WorkflowResult with outputs from all workers
        """
        result = WorkflowResult(
            workflow_name=self.name,
            status=StepStatus.RUNNING
        )
        
        # Plan tasks
        if not self.task_planner:
            result.error = "No task planner defined"
            result.status = StepStatus.FAILED
            result.complete()
            return result
        
        try:
            tasks = self.task_planner(context)
            result.metadata["total_tasks"] = len(tasks)
        except Exception as e:
            result.error = f"Task planning failed: {str(e)}"
            result.status = StepStatus.FAILED
            result.complete()
            return result
        
        # Create task dependency graph
        task_map = {task.task_id: task for task in tasks}
        completed_tasks: Set[str] = set()
        running_tasks: Dict[str, asyncio.Task] = {}
        
        # Worker semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_workers)
        
        # Execute tasks respecting dependencies
        while len(completed_tasks) < len(tasks):
            # Find tasks ready to run
            ready_tasks = []
            for task in tasks:
                if task.task_id not in completed_tasks and \
                   task.task_id not in running_tasks and \
                   all(dep in completed_tasks for dep in task.dependencies):
                    ready_tasks.append(task)
            
            if not ready_tasks and not running_tasks:
                # No tasks can run - circular dependency or error
                result.error = "Circular dependency detected or all tasks failed"
                result.status = StepStatus.FAILED
                break
            
            # Start ready tasks
            for task in ready_tasks:
                if task.task_type not in self.workers:
                    # No worker for this task type
                    step_result = StepResult(
                        step_name=f"{task.task_type}:{task.task_id}",
                        status=StepStatus.FAILED,
                        error=f"No worker registered for type: {task.task_type}"
                    )
                    step_result.complete()
                    result.steps.append(step_result)
                    completed_tasks.add(task.task_id)
                else:
                    # Start worker task
                    worker_task = asyncio.create_task(
                        self._execute_worker(task, semaphore, context)
                    )
                    running_tasks[task.task_id] = worker_task
            
            # Wait for at least one task to complete
            if running_tasks:
                done, pending = await asyncio.wait(
                    running_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed tasks
                for task in done:
                    # Find which task this was
                    task_id = None
                    for tid, t in running_tasks.items():
                        if t == task:
                            task_id = tid
                            break
                    
                    if task_id:
                        try:
                            step_result = await task
                            result.steps.append(step_result)
                            
                            # Store result for dependent tasks
                            if step_result.status == StepStatus.COMPLETED:
                                self.task_results[task_id] = step_result.output
                        except Exception as e:
                            # Task failed
                            step_result = StepResult(
                                step_name=f"task:{task_id}",
                                status=StepStatus.FAILED,
                                error=str(e)
                            )
                            step_result.complete()
                            result.steps.append(step_result)
                        
                        completed_tasks.add(task_id)
                        del running_tasks[task_id]
        
        # Set final output
        result.output = self.task_results
        result.metadata["completed_tasks"] = len(completed_tasks)
        result.complete()
        self.result = result
        return result
    
    async def _execute_worker(
        self,
        task: WorkerTask,
        semaphore: asyncio.Semaphore,
        context: Dict[str, Any]
    ) -> StepResult:
        """Execute a single worker task."""
        async with semaphore:
            worker = self.workers[task.task_type]
            
            # Prepare task context with dependency results
            task_context = {
                **context,
                "task": task.payload,
                "dependencies": {
                    dep: self.task_results.get(dep)
                    for dep in task.dependencies
                }
            }
            
            # Create step for this task
            step = WorkflowStep(
                name=f"{task.task_type}:{task.task_id}",
                func=worker,
                timeout=self.worker_timeout
            )
            
            return await self.execute_step(step, task_context)
    
    @classmethod
    def create_simple(
        cls,
        name: str,
        worker_map: Dict[str, Callable],
        planner: Callable
    ) -> "OrchestratorWorkflow":
        """
        Create a simple orchestrator workflow.
        
        Args:
            name: Workflow name
            worker_map: Dictionary mapping worker types to handlers
            planner: Task planning function
            
        Returns:
            OrchestratorWorkflow instance
        """
        workflow = cls(name)
        
        for worker_type, handler in worker_map.items():
            workflow.register_worker(worker_type, handler)
        
        workflow.set_task_planner(planner)
        return workflow


# Import at end to avoid circular dependency
from .base import StepResult