#!/usr/bin/env python3

import abc
import logging
import time
import uuid
from typing import Dict, List, Any, Callable, Optional, Set

class BaseAgent(abc.ABC):
    """
    Abstract base class for all agents in the framework.
    
    This class defines the core functionality and lifecycle methods that all
    agents must implement. It provides a standardized interface for agent
    initialization, starting, stopping, and message handling.
    
    Attributes:
        agent_id (str): Unique identifier for the agent
        agent_type (str): Type of agent, used for categorization and discovery
        capabilities (List[str]): List of capabilities this agent provides
        status (str): Current status of the agent (e.g., "initialized", "running", "stopped")
        _message_handlers (Dict[str, List[Callable]]): Registered message handlers
        _processed_messages (Set[str]): Set of already processed message IDs (for deduplication)
    """
    
    STATUS_INITIALIZED = "initialized"
    STATUS_STARTING = "starting"
    STATUS_RUNNING = "running"
    STATUS_STOPPING = "stopping"
    STATUS_STOPPED = "stopped"
    STATUS_ERROR = "error"
    
    def __init__(self, agent_id: Optional[str] = None, agent_type: str = "base"):
        """
        Initialize a new agent.
        
        Args:
            agent_id: Unique identifier for this agent. If None, a UUID will be generated.
            agent_type: Type of agent, used for categorization and discovery.
        """
        self.agent_id = agent_id or f"{agent_type}-{str(uuid.uuid4())[:8]}"
        self.agent_type = agent_type
        self.capabilities = []
        self.status = self.STATUS_INITIALIZED
        self._message_handlers = {}
        self._processed_messages = set()
        
        # Configure logging
        self.logger = logging.getLogger(f"Agent.{self.agent_type}.{self.agent_id}")
        
        # Metrics for monitoring
        self._metrics = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": None,
            "stop_time": None
        }
    
    @abc.abstractmethod
    def start(self) -> bool:
        """
        Start the agent, initializing resources and subscribing to required topics.
        
        This method must be implemented by subclasses to define the agent's
        startup behavior, such as setting up connections, loading models or
        data, and subscribing to topics.
        
        Returns:
            bool: True if the agent was started successfully, False otherwise.
        """
        self.status = self.STATUS_STARTING
        self._metrics["start_time"] = time.time()
        self.logger.info(f"Starting agent {self.agent_id} of type {self.agent_type}")
        return True
    
    @abc.abstractmethod
    def stop(self) -> bool:
        """
        Stop the agent, cleaning up resources and unsubscribing from topics.
        
        This method must be implemented by subclasses to define the agent's
        shutdown behavior, such as closing connections, saving state,
        and unsubscribing from topics.
        
        Returns:
            bool: True if the agent was stopped successfully, False otherwise.
        """
        self.status = self.STATUS_STOPPING
        self._metrics["stop_time"] = time.time()
        self.logger.info(f"Stopping agent {self.agent_id} of type {self.agent_type}")
        return True
    
    @abc.abstractmethod
    def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Process a message received from a topic.
        
        This method must be implemented by subclasses to define how the agent
        processes messages. It should include logic for message validation,
        business rules, and any actions to be taken.
        
        Args:
            topic: The topic the message was received on.
            message: The message data as a dictionary.
            
        Returns:
            bool: True if the message was processed successfully, False otherwise.
        """
        self._metrics["messages_received"] += 1
        
        # Check for duplicate messages
        message_id = message.get("message_id", None)
        if message_id:
            if message_id in self._processed_messages:
                self.logger.debug(f"Ignoring duplicate message: {message_id}")
                return False
            self._processed_messages.add(message_id)
        
        # Let subclasses implement the actual processing
        return True
    
    def register_handler(self, topic_pattern: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a handler for a specific topic pattern.
        
        Args:
            topic_pattern: The topic pattern to handle (may include wildcards)
            handler: The callback function to invoke when a message is received on this topic
        """
        if topic_pattern not in self._message_handlers:
            self._message_handlers[topic_pattern] = []
        
        self._message_handlers[topic_pattern].append(handler)
        self.logger.debug(f"Registered handler for topic pattern: {topic_pattern}")
    
    def get_capabilities(self) -> List[str]:
        """
        Get the capabilities this agent provides.
        
        Returns:
            List[str]: List of capability strings
        """
        return self.capabilities
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get detailed status information about this agent.
        
        Returns:
            Dict[str, Any]: Status dictionary including status, metrics, etc.
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "capabilities": self.capabilities,
            "metrics": self._metrics,
            "uptime": (time.time() - self._metrics["start_time"]) if self._metrics["start_time"] else 0
        }
    
    def add_capability(self, capability: str) -> None:
        """
        Add a capability to this agent.
        
        Args:
            capability: The capability string to add
        """
        if capability not in self.capabilities:
            self.capabilities.append(capability)
    
    def remove_capability(self, capability: str) -> None:
        """
        Remove a capability from this agent.
        
        Args:
            capability: The capability string to remove
        """
        if capability in self.capabilities:
            self.capabilities.remove(capability)
    
    def _record_error(self, error: Exception) -> None:
        """
        Record an error that occurred in the agent.
        
        Args:
            error: The exception that occurred
        """
        self._metrics["errors"] += 1
        self.logger.error(f"Error in agent {self.agent_id}: {str(error)}", exc_info=True)
        
        # If too many errors occur, transition to error state
        if self._metrics["errors"] > 100:  # Threshold can be configurable
            self.status = self.STATUS_ERROR
            self.logger.critical(f"Agent {self.agent_id} has entered error state due to too many errors")