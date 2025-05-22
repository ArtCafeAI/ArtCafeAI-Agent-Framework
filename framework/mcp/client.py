#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("AgentFramework.MCP.Client")

class MCPClient:
    """
    Client for Model Context Protocol (MCP) servers.
    
    This client connects to MCP servers to access tools and capabilities
    exposed through the Model Context Protocol standard. It supports both
    subprocess-based and socket-based MCP servers.
    """
    
    def __init__(self, 
                server_command: Optional[str] = None, 
                server_args: Optional[List[str]] = None,
                socket_path: Optional[str] = None,
                host: Optional[str] = None,
                port: Optional[int] = None):
        """
        Initialize an MCP client.
        
        The client can connect to a server in one of three ways:
        1. Launch a subprocess with the given command and args
        2. Connect to a Unix socket at the given path
        3. Connect to a TCP socket at the given host and port
        
        Args:
            server_command: Command to launch the MCP server
            server_args: Arguments for the server command
            socket_path: Path to Unix socket for existing server
            host: Hostname for TCP socket connection
            port: Port for TCP socket connection
        """
        self.server_command = server_command
        self.server_args = server_args or []
        self.socket_path = socket_path
        self.host = host
        self.port = port
        
        self.process = None
        self.reader = None
        self.writer = None
        self.connected = False
        
        # Tools registry
        self.tools = {}
    
    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        This method establishes a connection to the MCP server using the
        connection method specified in the constructor.
        
        Returns:
            bool: True if connection succeeded, False otherwise
        """
        # Check if already connected
        if self.connected:
            return True
        
        try:
            # Determine connection method
            if self.server_command:
                # Launch subprocess and connect to its stdio
                await self._connect_subprocess()
            elif self.socket_path:
                # Connect to Unix socket
                await self._connect_unix_socket()
            elif self.host and self.port:
                # Connect to TCP socket
                await self._connect_tcp_socket()
            else:
                logger.error("No connection method specified")
                return False
            
            # Initialize MCP connection
            await self._initialize_connection()
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {str(e)}")
            await self.disconnect()
            return False
    
    async def disconnect(self) -> None:
        """
        Disconnect from the MCP server.
        
        This method closes the connection and cleans up resources.
        """
        try:
            # Close writer if it exists
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
                self.writer = None
                self.reader = None
            
            # Terminate process if it exists
            if self.process:
                self.process.terminate()
                try:
                    # Wait for process to terminate
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if timeout
                    self.process.kill()
                
                self.process = None
            
            self.connected = False
            logger.debug("Disconnected from MCP server")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server: {str(e)}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.
        
        Returns:
            List[Dict[str, Any]]: List of tool specifications
        """
        if not self.connected:
            if not await self.connect():
                return []
        
        try:
            # Send list_tools request
            request = {
                "type": "list_tools",
                "id": "list-tools-request"
            }
            
            await self._send_request(request)
            response = await self._receive_response()
            
            if response.get("status") == "success":
                tool_specs = response.get("result", [])
                
                # Cache tools
                self.tools = {tool["name"]: tool for tool in tool_specs}
                
                return tool_specs
            else:
                logger.error(f"Error listing tools: {response.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing tools: {str(e)}")
            return []
    
    async def call_tool(self, 
                      tool_name: str, 
                      arguments: Dict[str, Any],
                      tool_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            tool_id: Optional ID for the tool call
            
        Returns:
            Dict[str, Any]: Tool result
        """
        if not self.connected:
            if not await self.connect():
                return {"status": "error", "error": "Not connected to MCP server"}
        
        try:
            # Send call_tool request
            request = {
                "type": "call_tool",
                "id": tool_id or f"tool-call-{tool_name}",
                "name": tool_name,
                "arguments": arguments
            }
            
            await self._send_request(request)
            response = await self._receive_response()
            
            if response.get("status") == "success":
                result = response.get("result", {})
                
                # Format result for agent framework
                return {
                    "toolUseId": tool_id or request["id"],
                    "status": "success",
                    "data": result
                }
            else:
                error_msg = response.get("error", "Unknown error")
                logger.error(f"Error calling tool {tool_name}: {error_msg}")
                
                return {
                    "toolUseId": tool_id or request["id"],
                    "status": "error",
                    "error": error_msg
                }
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            
            return {
                "toolUseId": tool_id or f"tool-call-{tool_name}",
                "status": "error",
                "error": str(e)
            }
    
    def get_tool_specs(self) -> List[Dict[str, Any]]:
        """
        Get the cached tool specifications.
        
        Returns:
            List[Dict[str, Any]]: List of tool specifications
        """
        return list(self.tools.values())
    
    async def _connect_subprocess(self) -> None:
        """Launch and connect to an MCP server subprocess."""
        if not self.server_command:
            raise ValueError("Server command not specified")
        
        # Launch subprocess
        self.process = await asyncio.create_subprocess_exec(
            self.server_command, 
            *self.server_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        if not self.process.stdin or not self.process.stdout:
            raise RuntimeError("Failed to create pipes for subprocess")
        
        # Create streams
        self.reader = self.process.stdout
        self.writer = self.process.stdin
        
        logger.debug(f"Started MCP subprocess: {self.server_command}")
    
    async def _connect_unix_socket(self) -> None:
        """Connect to an MCP server via Unix socket."""
        if not self.socket_path:
            raise ValueError("Socket path not specified")
        
        # Connect to Unix socket
        self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)
        
        logger.debug(f"Connected to MCP server via Unix socket: {self.socket_path}")
    
    async def _connect_tcp_socket(self) -> None:
        """Connect to an MCP server via TCP socket."""
        if not self.host or not self.port:
            raise ValueError("Host and port not specified")
        
        # Connect to TCP socket
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        
        logger.debug(f"Connected to MCP server via TCP socket: {self.host}:{self.port}")
    
    async def _initialize_connection(self) -> None:
        """Initialize the MCP connection with handshake."""
        # Send initialization message
        init_request = {
            "type": "initialize",
            "id": "init-request",
            "version": "1.0"
        }
        
        await self._send_request(init_request)
        response = await self._receive_response()
        
        if response.get("status") != "success":
            raise RuntimeError(f"MCP initialization failed: {response.get('error')}")
        
        self.connected = True
        logger.debug("MCP connection initialized successfully")
    
    async def _send_request(self, request: Dict[str, Any]) -> None:
        """Send a request to the MCP server."""
        if not self.writer:
            raise RuntimeError("Not connected to MCP server")
        
        # Convert request to JSON
        request_json = json.dumps(request)
        request_bytes = f"{request_json}\n".encode("utf-8")
        
        # Send request
        self.writer.write(request_bytes)
        await self.writer.drain()
    
    async def _receive_response(self) -> Dict[str, Any]:
        """Receive a response from the MCP server."""
        if not self.reader:
            raise RuntimeError("Not connected to MCP server")
        
        # Read response line
        response_line = await self.reader.readline()
        if not response_line:
            raise RuntimeError("MCP server closed connection")
        
        # Parse response
        response_json = response_line.decode("utf-8").strip()
        try:
            response = json.loads(response_json)
            return response
        except json.JSONDecodeError:
            raise RuntimeError(f"Invalid JSON response: {response_json}")
    
    async def __aenter__(self) -> 'MCPClient':
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()