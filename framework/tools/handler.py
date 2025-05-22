#!/usr/bin/env python3

import logging
import asyncio
import traceback
from typing import Any, Callable, Dict, List, Optional, Union

from .registry import ToolRegistry

logger = logging.getLogger("AgentFramework.Tools.Handler")

class ToolHandler:
    """
    Handler for executing agent tools.
    
    This class is responsible for executing tools based on requests from an agent.
    It validates tool requests, executes the tools, and formats the results.
    """
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        Initialize the tool handler.
        
        Args:
            registry: The tool registry to use, or None to create a new one
        """
        self.registry = registry or ToolRegistry()
    
    async def execute_tool(self, 
                          tool_request: Dict[str, Any], 
                          agent_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a tool based on a request.
        
        Args:
            tool_request: The tool request dictionary containing:
                - tool_name: Name of the tool to execute
                - input: Dictionary of input parameters
                - tool_id: Optional ID for tracking the request
            agent_context: Optional context from the agent
            
        Returns:
            Dict[str, Any]: The tool execution result
        """
        # Extract request details
        tool_name = tool_request.get("tool_name")
        tool_input = tool_request.get("input", {})
        tool_id = tool_request.get("tool_id", "unknown")
        
        # Validate request
        if not tool_name:
            logger.error("Missing tool_name in tool request")
            return {
                "tool_id": tool_id,
                "status": "error",
                "error": "Missing tool_name in request"
            }
        
        # Get the tool
        tool_func = self.registry.get_tool(tool_name)
        if not tool_func:
            logger.error(f"Tool not found: {tool_name}")
            return {
                "tool_id": tool_id,
                "status": "error",
                "error": f"Tool not found: {tool_name}"
            }
        
        # Prepare tool execution request
        execution_request = {
            "tool_id": tool_id,
            "input": tool_input
        }
        
        # Execute the tool
        try:
            # Check if tool function is async
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(execution_request)
            else:
                # Run sync function in a thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    lambda: tool_func(execution_request)
                )
            
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            logger.debug(traceback.format_exc())
            return {
                "tool_id": tool_id,
                "status": "error",
                "error": f"Error executing tool: {str(e)}"
            }
    
    async def execute_tools(self, 
                           tool_requests: List[Dict[str, Any]], 
                           agent_context: Optional[Dict[str, Any]] = None,
                           parallel: bool = True) -> List[Dict[str, Any]]:
        """
        Execute multiple tools, optionally in parallel.
        
        Args:
            tool_requests: List of tool request dictionaries
            agent_context: Optional context from the agent
            parallel: Whether to execute tools in parallel
            
        Returns:
            List[Dict[str, Any]]: List of tool execution results
        """
        if not tool_requests:
            return []
        
        if parallel:
            # Execute tools in parallel
            tasks = [
                self.execute_tool(request, agent_context)
                for request in tool_requests
            ]
            results = await asyncio.gather(*tasks)
            return results
        else:
            # Execute tools sequentially
            results = []
            for request in tool_requests:
                result = await self.execute_tool(request, agent_context)
                results.append(result)
            return results