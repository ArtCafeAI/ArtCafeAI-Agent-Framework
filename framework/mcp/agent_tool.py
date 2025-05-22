#!/usr/bin/env python3

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("AgentFramework.MCP.AgentTool")

class MCPAgentTool:
    """
    Tool wrapper for MCP tool specifications.
    
    This class wraps an MCP tool specification and provides a uniform interface
    for agents to use tools from an MCP server.
    """
    
    def __init__(self, 
                tool_spec: Dict[str, Any], 
                mcp_client: 'MCPClient'):
        """
        Initialize an MCP agent tool.
        
        Args:
            tool_spec: Tool specification from MCP server
            mcp_client: MCP client for tool execution
        """
        self.tool_spec = tool_spec
        self.mcp_client = mcp_client
        self.name = tool_spec["name"]
        self.description = tool_spec.get("description", f"Tool {self.name}")
        self.schema = tool_spec.get("schema", {})
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the tool to a dictionary format for the agent framework.
        
        Returns:
            Dict[str, Any]: Tool specification for the agent framework
        """
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema
        }
    
    async def execute(self, 
                    arguments: Dict[str, Any], 
                    tool_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the tool with the given arguments.
        
        Args:
            arguments: Tool arguments
            tool_id: Optional ID for the tool call
            
        Returns:
            Dict[str, Any]: Tool execution result
        """
        return await self.mcp_client.call_tool(
            tool_name=self.name,
            arguments=arguments,
            tool_id=tool_id
        )