#!/usr/bin/env python3

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

from ..messaging.nats_provider import NATSProvider
from ..core.config import AgentConfig

logger = logging.getLogger("AgentFramework.Protocols.A2A")

class NegotiationState(Enum):
    """States for A2A negotiation."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTER = "counter"
    FINALIZED = "finalized"

class A2AProtocol:
    """
    Agent-to-Agent (A2A) protocol implementation over NATS.
    
    This protocol enables agents to negotiate and coordinate directly
    with each other through structured negotiations.
    """
    
    def __init__(self, nats_provider: NATSProvider, agent_id: str, capabilities: List[str]):
        """
        Initialize the A2A protocol handler.
        
        Args:
            nats_provider: The NATS messaging provider
            agent_id: ID of the agent using this protocol
            capabilities: List of agent capabilities
        """
        self.nats = nats_provider
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.token = None
        self.active_negotiations = {}
        self.negotiation_handlers = {}
        
    def authenticate(self, permissions: List[str]) -> bool:
        """
        Authenticate with the NATS provider.
        
        Args:
            permissions: List of permissions to request
            
        Returns:
            bool: True if authentication was successful
        """
        self.token = self.nats.create_token(self.agent_id, permissions)
        
        if self.token:
            # Subscribe to A2A negotiations for this agent
            topic = f"agents/a2a/negotiate/{self.agent_id}"
            self.nats.subscribe(
                self.token,
                topic,
                self._handle_negotiation
            )
            logger.info(f"A2A protocol initialized for agent {self.agent_id}")
            
        return self.token is not None
        
    def register_negotiation_handler(
        self,
        negotiation_type: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """
        Register a handler for a specific type of negotiation.
        
        Args:
            negotiation_type: Type of negotiation to handle
            handler: Function to handle the negotiation
        """
        self.negotiation_handlers[negotiation_type] = handler
        logger.debug(f"Registered handler for negotiation type: {negotiation_type}")
        
    async def initiate_negotiation(
        self,
        target_agents: List[str],
        negotiation_type: str,
        proposal: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Initiate a negotiation with one or more agents.
        
        Args:
            target_agents: List of agent IDs to negotiate with
            negotiation_type: Type of negotiation
            proposal: The proposal content
            constraints: Optional constraints for the negotiation
            timeout: Timeout in seconds
            
        Returns:
            Dict containing negotiation results
        """
        negotiation_id = str(uuid.uuid4())
        
        # Store negotiation state
        self.active_negotiations[negotiation_id] = {
            "id": negotiation_id,
            "type": negotiation_type,
            "state": NegotiationState.PROPOSED,
            "proposal": proposal,
            "constraints": constraints or {},
            "target_agents": target_agents,
            "responses": {},
            "created_at": datetime.now().timestamp()
        }
        
        # Create negotiation message
        message = {
            "id": negotiation_id,
            "timestamp": datetime.now().timestamp(),
            "version": "1.0",
            "type": "negotiation",
            "source": {
                "id": self.agent_id,
                "type": "agent",
                "capabilities": self.capabilities
            },
            "context": {
                "negotiationId": negotiation_id,
                "negotiationType": negotiation_type
            },
            "payload": {
                "content": {
                    "protocol": "a2a-v1",
                    "action": "propose",
                    "proposal": proposal,
                    "constraints": constraints or {}
                }
            },
            "routing": {
                "priority": 7,
                "timeout": int(timeout * 1000)
            }
        }
        
        # Send to all target agents
        for agent in target_agents:
            topic = f"agents/a2a/negotiate/{agent}"
            self.nats.publish(self.token, topic, message)
            
        # Wait for responses
        try:
            result = await self._wait_for_negotiation_completion(
                negotiation_id,
                len(target_agents),
                timeout
            )
            return result
        except asyncio.TimeoutError:
            return {
                "negotiation_id": negotiation_id,
                "state": "timeout",
                "responses": self.active_negotiations[negotiation_id]["responses"]
            }
            
    def _handle_negotiation(self, message: Dict[str, Any]):
        """
        Handle an incoming negotiation message.
        
        Args:
            message: The negotiation message
        """
        try:
            negotiation_id = message.get("context", {}).get("negotiationId")
            negotiation_type = message.get("context", {}).get("negotiationType")
            action = message.get("payload", {}).get("content", {}).get("action")
            
            if action == "propose":
                self._handle_proposal(message)
            elif action == "accept":
                self._handle_acceptance(negotiation_id, message)
            elif action == "reject":
                self._handle_rejection(negotiation_id, message)
            elif action == "counter":
                self._handle_counter_proposal(negotiation_id, message)
            else:
                logger.warning(f"Unknown negotiation action: {action}")
                
        except Exception as e:
            logger.error(f"Error handling negotiation: {e}")
            
    def _handle_proposal(self, message: Dict[str, Any]):
        """
        Handle an incoming proposal.
        
        Args:
            message: The proposal message
        """
        negotiation_id = message.get("id")
        negotiation_type = message.get("context", {}).get("negotiationType")
        proposal = message.get("payload", {}).get("content", {}).get("proposal")
        constraints = message.get("payload", {}).get("content", {}).get("constraints", {})
        source_agent = message.get("source", {}).get("id")
        
        # Check if we have a handler for this negotiation type
        handler = self.negotiation_handlers.get(negotiation_type)
        if not handler:
            # Reject if no handler
            self._send_rejection(negotiation_id, source_agent, "No handler for negotiation type")
            return
            
        try:
            # Call the handler
            response = handler({
                "proposal": proposal,
                "constraints": constraints,
                "source_agent": source_agent,
                "source_capabilities": message.get("source", {}).get("capabilities", [])
            })
            
            # Send response based on handler result
            if response.get("accept"):
                self._send_acceptance(negotiation_id, source_agent, response.get("terms"))
            elif response.get("counter"):
                self._send_counter_proposal(
                    negotiation_id,
                    source_agent,
                    response.get("counter_proposal")
                )
            else:
                self._send_rejection(
                    negotiation_id,
                    source_agent,
                    response.get("reason", "Proposal not acceptable")
                )
                
        except Exception as e:
            logger.error(f"Error in negotiation handler: {e}")
            self._send_rejection(negotiation_id, source_agent, f"Handler error: {str(e)}")
            
    def _send_acceptance(self, negotiation_id: str, target_agent: str, terms: Optional[Dict[str, Any]] = None):
        """Send an acceptance message."""
        self._send_negotiation_response(
            negotiation_id,
            target_agent,
            "accept",
            {"accepted_terms": terms or {}}
        )
        
    def _send_rejection(self, negotiation_id: str, target_agent: str, reason: str):
        """Send a rejection message."""
        self._send_negotiation_response(
            negotiation_id,
            target_agent,
            "reject",
            {"reason": reason}
        )
        
    def _send_counter_proposal(self, negotiation_id: str, target_agent: str, counter_proposal: Dict[str, Any]):
        """Send a counter proposal."""
        self._send_negotiation_response(
            negotiation_id,
            target_agent,
            "counter",
            {"counter_proposal": counter_proposal}
        )
        
    def _send_negotiation_response(
        self,
        negotiation_id: str,
        target_agent: str,
        action: str,
        content: Dict[str, Any]
    ):
        """
        Send a negotiation response.
        
        Args:
            negotiation_id: ID of the negotiation
            target_agent: Agent to send the response to
            action: Response action (accept/reject/counter)
            content: Response content
        """
        message = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().timestamp(),
            "version": "1.0",
            "type": "negotiation",
            "source": {
                "id": self.agent_id,
                "type": "agent",
                "capabilities": self.capabilities
            },
            "correlationId": negotiation_id,
            "context": {
                "negotiationId": negotiation_id
            },
            "payload": {
                "content": {
                    "protocol": "a2a-v1",
                    "action": action,
                    **content
                }
            },
            "routing": {
                "priority": 7
            }
        }
        
        topic = f"agents/a2a/negotiate/{target_agent}"
        self.nats.publish(self.token, topic, message)
        
    def _handle_acceptance(self, negotiation_id: str, message: Dict[str, Any]):
        """Handle an acceptance response."""
        if negotiation_id in self.active_negotiations:
            source_agent = message.get("source", {}).get("id")
            self.active_negotiations[negotiation_id]["responses"][source_agent] = {
                "action": "accept",
                "terms": message.get("payload", {}).get("content", {}).get("accepted_terms", {})
            }
            
    def _handle_rejection(self, negotiation_id: str, message: Dict[str, Any]):
        """Handle a rejection response."""
        if negotiation_id in self.active_negotiations:
            source_agent = message.get("source", {}).get("id")
            self.active_negotiations[negotiation_id]["responses"][source_agent] = {
                "action": "reject",
                "reason": message.get("payload", {}).get("content", {}).get("reason")
            }
            
    def _handle_counter_proposal(self, negotiation_id: str, message: Dict[str, Any]):
        """Handle a counter proposal."""
        if negotiation_id in self.active_negotiations:
            source_agent = message.get("source", {}).get("id")
            self.active_negotiations[negotiation_id]["responses"][source_agent] = {
                "action": "counter",
                "counter_proposal": message.get("payload", {}).get("content", {}).get("counter_proposal", {})
            }
            
    async def _wait_for_negotiation_completion(
        self,
        negotiation_id: str,
        expected_responses: int,
        timeout: float
    ) -> Dict[str, Any]:
        """
        Wait for a negotiation to complete.
        
        Args:
            negotiation_id: ID of the negotiation
            expected_responses: Number of responses expected
            timeout: Timeout in seconds
            
        Returns:
            Dict containing negotiation results
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            negotiation = self.active_negotiations.get(negotiation_id)
            if not negotiation:
                raise ValueError(f"Negotiation {negotiation_id} not found")
                
            # Check if we have all responses
            if len(negotiation["responses"]) >= expected_responses:
                # Determine overall state
                all_accepted = all(
                    r["action"] == "accept"
                    for r in negotiation["responses"].values()
                )
                
                if all_accepted:
                    negotiation["state"] = NegotiationState.FINALIZED
                else:
                    negotiation["state"] = NegotiationState.REJECTED
                    
                return {
                    "negotiation_id": negotiation_id,
                    "state": negotiation["state"].value,
                    "responses": negotiation["responses"]
                }
                
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise asyncio.TimeoutError()
                
            # Wait a bit before checking again
            await asyncio.sleep(0.1)