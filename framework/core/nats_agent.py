#!/usr/bin/env python3

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .enhanced_agent import EnhancedAgent
from ..messaging.nats_provider import NATSProvider
from ..mcp.nats_bridge import MCPNATSBridge
from ..protocols.a2a import A2AProtocol
from ..core.config import AgentConfig

logger = logging.getLogger("AgentFramework.Core.NATSAgent")

class NATSAgent(EnhancedAgent):
    """
    Agent implementation that uses NATS as the messaging backbone.
    
    This agent extends EnhancedAgent to provide native NATS support with:
    - Hierarchical topic structure as defined in the guide
    - MCP over NATS support
    - A2A protocol support
    - Message batching and streaming capabilities
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_type: str = "nats",
        config: Optional[AgentConfig] = None
    ):
        """
        Initialize a NATS-enabled agent.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_type: Type of agent
            config: Configuration object
        """
        # Force NATS provider in config
        if config is None:
            config = AgentConfig()
        config.set("messaging.provider", "nats")
        
        super().__init__(agent_id, agent_type, config)
        
        self.mcp_bridge = None
        self.a2a_protocol = None
        self.batch_queue = []
        self.batch_size = config.get("nats.batch_size", 10)
        self.batch_timeout = config.get("nats.batch_timeout", 1.0)
        self._batch_timer = None
        
    def _setup_messaging(self):
        """Set up NATS-specific messaging features."""
        super()._setup_messaging()
        
        # Get NATS provider
        if isinstance(self.messaging._provider, NATSProvider):
            # Set up MCP bridge
            self.mcp_bridge = MCPNATSBridge(self.messaging._provider, self.agent_id)
            self.mcp_bridge.authenticate(self._get_permissions())
            
            # Set up A2A protocol
            self.a2a_protocol = A2AProtocol(
                self.messaging._provider,
                self.agent_id,
                self.capabilities
            )
            self.a2a_protocol.authenticate(self._get_permissions())
            
            logger.info(f"NATS agent {self.agent_id} initialized with MCP and A2A support")
            
    def register_mcp_server(self, server_id: str, mcp_client):
        """
        Register an MCP server to be accessible over NATS.
        
        Args:
            server_id: Unique identifier for the MCP server
            mcp_client: The MCP client instance
        """
        if self.mcp_bridge:
            self.mcp_bridge.register_mcp_server(server_id, mcp_client)
        else:
            logger.warning("MCP bridge not available - using non-NATS provider")
            
    def register_a2a_handler(
        self,
        negotiation_type: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """
        Register a handler for A2A negotiations.
        
        Args:
            negotiation_type: Type of negotiation to handle
            handler: Function to handle the negotiation
        """
        if self.a2a_protocol:
            self.a2a_protocol.register_negotiation_handler(negotiation_type, handler)
        else:
            logger.warning("A2A protocol not available - using non-NATS provider")
            
    async def negotiate_with_agents(
        self,
        target_agents: List[str],
        negotiation_type: str,
        proposal: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Initiate an A2A negotiation with other agents.
        
        Args:
            target_agents: List of agent IDs to negotiate with
            negotiation_type: Type of negotiation
            proposal: The proposal content
            constraints: Optional constraints for the negotiation
            timeout: Timeout in seconds
            
        Returns:
            Dict containing negotiation results
        """
        if self.a2a_protocol:
            return await self.a2a_protocol.initiate_negotiation(
                target_agents,
                negotiation_type,
                proposal,
                constraints,
                timeout
            )
        else:
            raise RuntimeError("A2A protocol not available - using non-NATS provider")
            
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
        """
        if self.mcp_bridge:
            return await self.mcp_bridge.call_mcp_tool(
                server_id,
                tool_name,
                arguments,
                timeout
            )
        else:
            raise RuntimeError("MCP bridge not available - using non-NATS provider")
            
    def enable_batch_processing(self, batch_size: int = 10, batch_timeout: float = 1.0):
        """
        Enable batch processing of messages.
        
        Args:
            batch_size: Maximum number of messages to batch
            batch_timeout: Maximum time to wait before processing a partial batch
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        logger.info(f"Batch processing enabled: size={batch_size}, timeout={batch_timeout}s")
        
    def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Process a message, potentially batching it.
        
        Args:
            topic: The topic the message was received on
            message: The message payload
            
        Returns:
            bool: True if message was processed/queued successfully
        """
        if self.batch_size > 1:
            # Add to batch queue
            self.batch_queue.append((topic, message))
            
            if len(self.batch_queue) >= self.batch_size:
                # Process full batch
                self._process_batch()
            else:
                # Start/reset batch timer
                if self._batch_timer:
                    self._batch_timer.cancel()
                self._batch_timer = asyncio.create_task(self._batch_timeout_handler())
                
            return True
        else:
            # Process immediately
            return super().process_message(topic, message)
            
    def _process_batch(self):
        """Process all messages in the batch queue."""
        if not self.batch_queue:
            return
            
        batch = self.batch_queue.copy()
        self.batch_queue.clear()
        
        # Cancel timer if running
        if self._batch_timer:
            self._batch_timer.cancel()
            self._batch_timer = None
            
        # Process all messages
        self.logger.info(f"Processing batch of {len(batch)} messages")
        
        for topic, message in batch:
            try:
                super().process_message(topic, message)
            except Exception as e:
                self.logger.error(f"Error processing batched message: {e}")
                
    async def _batch_timeout_handler(self):
        """Handle batch timeout."""
        await asyncio.sleep(self.batch_timeout)
        self._process_batch()
        
    async def stream_response(
        self,
        task_id: str,
        response_generator,
        chunk_size: int = 1024
    ):
        """
        Stream a response over NATS.
        
        Args:
            task_id: ID of the task this is responding to
            response_generator: Async generator yielding response chunks
            chunk_size: Maximum size of each chunk
        """
        sequence = 0
        
        async for chunk in response_generator:
            stream_msg = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().timestamp(),
                "version": "1.0",
                "type": "stream",
                "source": {
                    "id": self.agent_id,
                    "type": "agent"
                },
                "correlationId": task_id,
                "context": {
                    "conversationId": task_id
                },
                "payload": {
                    "sequenceNumber": sequence,
                    "isFirst": sequence == 0,
                    "isFinal": False,
                    "chunk": chunk[:chunk_size] if isinstance(chunk, str) else chunk
                },
                "routing": {
                    "priority": 5
                }
            }
            
            # Publish stream chunk
            stream_topic = f"agents/stream/response/{task_id}"
            self.publish(stream_topic, stream_msg)
            sequence += 1
            
        # Send final message
        final_msg = stream_msg.copy()
        final_msg["id"] = str(uuid.uuid4())
        final_msg["payload"]["sequenceNumber"] = sequence
        final_msg["payload"]["isFinal"] = True
        final_msg["payload"]["chunk"] = ""
        
        self.publish(stream_topic, final_msg)
        
    def _get_permissions(self) -> List[str]:
        """Get permissions for NATS authentication."""
        permissions = super()._get_permissions()
        
        # Add NATS-specific permissions
        permissions.extend([
            f"publish:agents.*.mcp.{self.agent_id}.*",
            f"subscribe:agents.*.mcp.{self.agent_id}.*",
            f"publish:agents.*.a2a.negotiate.*",
            f"subscribe:agents.*.a2a.negotiate.{self.agent_id}",
            f"publish:agents.*.stream.response.*",
            f"subscribe:agents.*.stream.response.*"
        ])
        
        return permissions