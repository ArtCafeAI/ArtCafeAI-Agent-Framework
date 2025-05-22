#!/usr/bin/env python3

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from ..messaging.nats_provider import NATSProvider
from ..core.config import AgentConfig
from .client import MCPClient

logger = logging.getLogger("AgentFramework.MCP.NATSBridge")

class MCPNATSBridge:
    """
    Bridge between NATS pub/sub and MCP protocol.
    
    This bridge allows MCP tools to be exposed over NATS topics, enabling
    agents to call MCP tools through the messaging system rather than
    direct connections.
    """
    
    def __init__(self, nats_provider: NATSProvider, agent_id: str):
        """
        Initialize the MCP-NATS bridge.
        
        Args:
            nats_provider: The NATS messaging provider
            agent_id: ID of the agent using this bridge
        """
        self.nats = nats_provider
        self.agent_id = agent_id
        self.mcp_servers = {}
        self.pending_requests = {}
        self.token = None
        
    def register_mcp_server(self, server_id: str, mcp_client: MCPClient):
        """
        Register an MCP server to be accessible over NATS.
        
        Args:
            server_id: Unique identifier for the MCP server
            mcp_client: The MCP client instance
        """
        self.mcp_servers[server_id] = mcp_client
        
        # Subscribe to MCP requests for this server
        if self.token:
            topic = f"agents/mcp/{server_id}/requests"
            self.nats.subscribe(
                self.token,
                topic,
                lambda msg: self._handle_mcp_request(server_id, msg)
            )
            logger.info(f"Registered MCP server {server_id} on NATS")
            
    def authenticate(self, permissions: List[str]) -> bool:
        """
        Authenticate with the NATS provider.
        
        Args:
            permissions: List of permissions to request
            
        Returns:
            bool: True if authentication was successful
        """
        self.token = self.nats.create_token(self.agent_id, permissions)
        return self.token is not None
        
    def _handle_mcp_request(self, server_id: str, message: Dict[str, Any]):
        """
        Handle an incoming MCP request over NATS.
        
        Args:
            server_id: ID of the MCP server to handle the request
            message: The incoming message
        """
        try:
            # Extract request details
            request_id = message.get("id")
            mcp_method = message.get("payload", {}).get("content", {}).get("method")
            mcp_params = message.get("payload", {}).get("content", {}).get("params", {})
            reply_to = message.get("replyTo")
            
            if not all([request_id, mcp_method, reply_to]):
                logger.error("Invalid MCP request: missing required fields")
                return
                
            # Get the MCP client
            mcp_client = self.mcp_servers.get(server_id)
            if not mcp_client:
                self._send_error(reply_to, request_id, f"MCP server {server_id} not found")
                return
                
            # Execute MCP request asynchronously
            asyncio.create_task(
                self._execute_mcp_request(
                    mcp_client, request_id, mcp_method, mcp_params, reply_to
                )
            )
            
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            if reply_to and request_id:
                self._send_error(reply_to, request_id, str(e))
                
    async def _execute_mcp_request(
        self,
        mcp_client: MCPClient,
        request_id: str,
        method: str,
        params: Dict[str, Any],
        reply_to: str
    ):
        """
        Execute an MCP request and send the response.
        
        Args:
            mcp_client: The MCP client to use
            request_id: ID of the request
            method: MCP method to call
            params: Parameters for the method
            reply_to: Topic to send the response to
        """
        try:
            # Call the MCP method
            if method == "tools/list":
                result = await mcp_client.list_tools()
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = await mcp_client.call_tool(tool_name, tool_args)
            else:
                raise ValueError(f"Unsupported MCP method: {method}")
                
            # Send success response
            self._send_response(reply_to, request_id, result)
            
        except Exception as e:
            logger.error(f"Error executing MCP request: {e}")
            self._send_error(reply_to, request_id, str(e))
            
    def _send_response(self, topic: str, request_id: str, result: Any):
        """
        Send a successful MCP response over NATS.
        
        Args:
            topic: Topic to send the response to
            request_id: ID of the original request
            result: The result data
        """
        response = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().timestamp(),
            "version": "1.0",
            "type": "result",
            "source": {
                "id": self.agent_id,
                "type": "mcp_bridge"
            },
            "correlationId": request_id,
            "context": {
                "conversationId": request_id
            },
            "payload": {
                "content": {
                    "success": True,
                    "result": result
                }
            },
            "routing": {
                "priority": 5
            }
        }
        
        self.nats.publish(self.token, topic, response)
        
    def _send_error(self, topic: str, request_id: str, error: str):
        """
        Send an error response over NATS.
        
        Args:
            topic: Topic to send the response to
            request_id: ID of the original request
            error: Error message
        """
        response = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().timestamp(),
            "version": "1.0",
            "type": "result",
            "source": {
                "id": self.agent_id,
                "type": "mcp_bridge"
            },
            "correlationId": request_id,
            "context": {
                "conversationId": request_id
            },
            "payload": {
                "content": {
                    "success": False,
                    "error": error
                }
            },
            "routing": {
                "priority": 5
            }
        }
        
        self.nats.publish(self.token, topic, response)
        
    async def call_mcp_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Call an MCP tool on a remote server through NATS.
        
        Args:
            server_id: ID of the MCP server
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            timeout: Timeout in seconds
            
        Returns:
            Dict containing the tool result
            
        Raises:
            TimeoutError: If the request times out
            Exception: If the tool call fails
        """
        request_id = str(uuid.uuid4())
        response_topic = f"agents/mcp/{self.agent_id}/responses/{request_id}"
        
        # Set up response handler
        response_future = asyncio.Future()
        
        def handle_response(msg):
            if msg.get("correlationId") == request_id:
                content = msg.get("payload", {}).get("content", {})
                if content.get("success"):
                    response_future.set_result(content.get("result"))
                else:
                    response_future.set_exception(
                        Exception(content.get("error", "Unknown error"))
                    )
                    
        # Subscribe to response topic
        self.nats.subscribe(self.token, response_topic, handle_response)
        
        try:
            # Send the request
            request = {
                "id": request_id,
                "timestamp": datetime.now().timestamp(),
                "version": "1.0",
                "type": "task",
                "source": {
                    "id": self.agent_id,
                    "type": "agent"
                },
                "replyTo": response_topic,
                "context": {
                    "conversationId": request_id
                },
                "payload": {
                    "content": {
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": arguments
                        }
                    }
                },
                "routing": {
                    "priority": 5,
                    "timeout": int(timeout * 1000)
                }
            }
            
            request_topic = f"agents/mcp/{server_id}/requests"
            self.nats.publish(self.token, request_topic, request)
            
            # Wait for response
            result = await asyncio.wait_for(response_future, timeout=timeout)
            return result
            
        finally:
            # Clean up subscription
            self.nats.unsubscribe(self.token, response_topic)