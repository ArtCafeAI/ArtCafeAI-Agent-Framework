"""
Routing Workflow - Route to different handlers based on conditions.

Implements the routing pattern where inputs are classified and
directed to appropriate handlers.
"""

from typing import Any, Dict, List, Callable, Optional
from .base import Workflow, WorkflowStep, WorkflowResult, StepStatus


class RoutingWorkflow(Workflow):
    """
    A workflow that routes inputs to different handlers based on conditions.
    
    Example:
        ```python
        workflow = RoutingWorkflow("customer_support")
        
        # Add routes
        workflow.add_route(
            condition=lambda ctx: "billing" in ctx.get("query", "").lower(),
            handler=handle_billing_query
        )
        workflow.add_route(
            condition=lambda ctx: "technical" in ctx.get("query", "").lower(),
            handler=handle_technical_query
        )
        workflow.set_default(handle_general_query)
        
        result = await workflow.execute({"query": "billing question"})
        ```
    """
    
    def __init__(self, name: str, routes: Optional[List[tuple]] = None):
        """
        Initialize a routing workflow.
        
        Args:
            name: Workflow name
            routes: Optional list of (condition, handler) tuples
        """
        super().__init__(name, [])
        self.routes = routes or []
        self.default_handler = None
    
    def add_route(
        self,
        condition: Callable[[Dict[str, Any]], bool],
        handler: Callable,
        name: Optional[str] = None
    ):
        """
        Add a route to the workflow.
        
        Args:
            condition: Function that returns True if this route should be taken
            handler: Function to handle the request
            name: Optional name for the route
        """
        route_name = name or f"route_{len(self.routes)}"
        self.routes.append((condition, handler, route_name))
    
    def set_default(self, handler: Callable, name: str = "default"):
        """
        Set the default handler for unmatched routes.
        
        Args:
            handler: Default handler function
            name: Name for the default route
        """
        self.default_handler = (handler, name)
    
    async def execute(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute the routing workflow.
        
        Args:
            context: Input context
            
        Returns:
            WorkflowResult with the output from the selected handler
        """
        result = WorkflowResult(
            workflow_name=self.name,
            status=StepStatus.RUNNING
        )
        
        # Find matching route
        selected_route = None
        for condition, handler, route_name in self.routes:
            try:
                if condition(context):
                    selected_route = (handler, route_name)
                    break
            except Exception as e:
                # Log condition error but continue checking other routes
                result.metadata[f"{route_name}_condition_error"] = str(e)
        
        # Use default if no route matched
        if selected_route is None and self.default_handler:
            selected_route = self.default_handler
        
        if selected_route is None:
            # No matching route and no default
            result.error = "No matching route found"
            result.status = StepStatus.FAILED
            result.complete()
            self.result = result
            return result
        
        # Execute the selected handler
        handler, route_name = selected_route
        step = WorkflowStep(name=route_name, func=handler)
        step_result = await self.execute_step(step, context)
        result.steps.append(step_result)
        
        # Set workflow output
        if step_result.status == StepStatus.COMPLETED:
            result.output = step_result.output
            result.metadata["selected_route"] = route_name
        else:
            result.error = step_result.error
        
        result.complete()
        self.result = result
        return result
    
    @classmethod
    def from_dict(
        cls,
        name: str,
        routes_dict: Dict[str, tuple]
    ) -> "RoutingWorkflow":
        """
        Create a routing workflow from a dictionary.
        
        Args:
            name: Workflow name
            routes_dict: Dictionary mapping route names to (condition, handler) tuples
            
        Returns:
            RoutingWorkflow instance
            
        Example:
            ```python
            workflow = RoutingWorkflow.from_dict(
                "classifier",
                {
                    "high_priority": (
                        lambda ctx: ctx.get("priority") == "high",
                        handle_high_priority
                    ),
                    "low_priority": (
                        lambda ctx: ctx.get("priority") == "low",
                        handle_low_priority
                    )
                }
            )
            ```
        """
        workflow = cls(name)
        for route_name, (condition, handler) in routes_dict.items():
            workflow.add_route(condition, handler, route_name)
        return workflow