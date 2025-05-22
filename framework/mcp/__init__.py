#!/usr/bin/env python3

"""
Model Context Protocol (MCP) Integration Module

This module provides integration with Model Context Protocol (MCP) servers,
enabling agents to access a wide range of tools and capabilities through
a standardized protocol.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .client import MCPClient
from .agent_tool import MCPAgentTool

# Conditionally import NATS bridge
try:
    from .nats_bridge import MCPNATSBridge
    NATS_BRIDGE_AVAILABLE = True
except ImportError:
    NATS_BRIDGE_AVAILABLE = False

logger = logging.getLogger("AgentFramework.MCP")

__all__ = [
    'MCPClient',
    'MCPAgentTool',
    'get_client_for_command',
    'get_client_for_socket',
    'get_client_for_tcp'
]

if NATS_BRIDGE_AVAILABLE:
    __all__.append('MCPNATSBridge')

async def get_client_for_command(command: str, args: Optional[List[str]] = None) -> MCPClient:
    """
    Get an MCP client for a command-based server.
    
    This function creates an MCP client that launches and communicates
    with a subprocess.
    
    Args:
        command: Command to execute
        args: Arguments for the command
        
    Returns:
        MCPClient: Initialized MCP client
    """
    client = MCPClient(server_command=command, server_args=args)
    await client.connect()
    return client

async def get_client_for_socket(socket_path: str) -> MCPClient:
    """
    Get an MCP client for a Unix socket-based server.
    
    This function creates an MCP client that communicates through
    a Unix socket.
    
    Args:
        socket_path: Path to the Unix socket
        
    Returns:
        MCPClient: Initialized MCP client
    """
    client = MCPClient(socket_path=socket_path)
    await client.connect()
    return client

async def get_client_for_tcp(host: str, port: int) -> MCPClient:
    """
    Get an MCP client for a TCP socket-based server.
    
    This function creates an MCP client that communicates through
    a TCP socket.
    
    Args:
        host: Hostname or IP address
        port: Port number
        
    Returns:
        MCPClient: Initialized MCP client
    """
    client = MCPClient(host=host, port=port)
    await client.connect()
    return client