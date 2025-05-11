#!/usr/bin/env python3

import logging
import time
import uuid
import threading
from typing import Dict, List, Any, Callable, Optional, Set

from .base_agent import BaseAgent
from .config import AgentConfig, DEFAULT_CONFIG
from ..messaging.interface import MessagingInterface
from ..messaging import get_messaging

logger = logging.getLogger("AgentFramework.Core.EnhancedAgent")

class EnhancedAgent(BaseAgent):
    """
    Enhanced agent implementation with integrated messaging and configuration.
    
    This class extends the base agent class with additional features like
    configuration management, messaging interface integration, and enhanced
    lifecycle management.
    
    Attributes:
        config (AgentConfig): Configuration for this agent
        messaging (MessagingInterface): Messaging interface for communication
        subscriptions (Dict[str, Callable]): Map of topic patterns to handler functions
        resource_authorizations (Dict[str, List[str]]): Map of resource types to allowed actions
    """
    
    def __init__(self, 
                 agent_id: Optional[str] = None, 
                 agent_type: str = "enhanced",
                 config: Optional[AgentConfig] = None,
                 permissions: Optional[List[str]] = None):
        """
        Initialize a new enhanced agent.
        
        Args:
            agent_id: Unique identifier for this agent. If None, a UUID will be generated.
            agent_type: Type of agent, used for categorization and discovery.
            config: Configuration for this agent, or None to use defaults
            permissions: Messaging permissions to request, or None for defaults
        """
        super().__init__(agent_id, agent_type)
        
        # Initialize configuration
        self.config = config or AgentConfig(defaults=DEFAULT_CONFIG)
        
        # Initialize messaging
        self.messaging = get_messaging(self.agent_id)
        self._setup_messaging(permissions)
        
        # Track subscriptions and resource authorizations
        self.subscriptions = {}
        self.resource_authorizations = {}
        
        # Thread control
        self._stop_event = threading.Event()
        self._main_thread = None
        
        logger.debug(f"Initialized enhanced agent {self.agent_id} of type {self.agent_type}")
    
    def _setup_messaging(self, permissions: Optional[List[str]] = None) -> None:
        """
        Set up messaging for this agent.
        
        Args:
            permissions: Messaging permissions to request, or None for defaults
        """
        # Default permissions if none provided
        if permissions is None:
            permissions = [
                f"subscribe:agents/{self.agent_type}/{self.agent_id}/#",
                f"publish:agents/{self.agent_type}/{self.agent_id}/#",
                "subscribe:agents/broadcast/#"
            ]
        
        # Authenticate with the messaging system
        success = self.messaging.authenticate(permissions)
        if not success:
            logger.error(f"Failed to authenticate agent {self.agent_id} with messaging system")
        else:
            logger.debug(f"Authenticated agent {self.agent_id} with messaging system")
    
    def start(self) -> bool:
        """
        Start the agent, initializing resources and subscribing to required topics.
        
        Returns:
            bool: True if the agent was started successfully, False otherwise.
        """
        # Call parent method to update status and metrics
        if not super().start():
            return False
        
        try:
            # Subscribe to control messages
            self._subscribe_to_control_topic()
            
            # Subscribe to additional topics based on configuration
            self._setup_subscriptions()
            
            # Start main processing thread if needed
            if hasattr(self, 'run') and callable(self.run):
                self._stop_event.clear()
                self._main_thread = threading.Thread(target=self._run_wrapper)
                self._main_thread.daemon = True
                self._main_thread.start()
                logger.debug(f"Started main thread for agent {self.agent_id}")
            
            # Update status
            self.status = self.STATUS_RUNNING
            logger.info(f"Started agent {self.agent_id} of type {self.agent_type}")
            
            # Announce agent presence
            self._announce_presence()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting agent {self.agent_id}: {e}", exc_info=True)
            self.status = self.STATUS_ERROR
            self._record_error(e)
            return False
    
    def _run_wrapper(self) -> None:
        """Wrapper for the main run method to handle exceptions."""
        try:
            self.run()
        except Exception as e:
            logger.error(f"Error in agent {self.agent_id} main thread: {e}", exc_info=True)
            self.status = self.STATUS_ERROR
            self._record_error(e)
    
    def stop(self) -> bool:
        """
        Stop the agent, cleaning up resources and unsubscribing from topics.
        
        Returns:
            bool: True if the agent was stopped successfully, False otherwise.
        """
        # Call parent method to update status and metrics
        if not super().stop():
            return False
        
        try:
            # Signal the main thread to stop
            self._stop_event.set()
            
            # Wait for main thread to finish
            if self._main_thread and self._main_thread.is_alive():
                self._main_thread.join(timeout=5.0)
                if self._main_thread.is_alive():
                    logger.warning(f"Main thread for agent {self.agent_id} did not stop gracefully")
            
            # Unsubscribe from all topics
            for topic in list(self.subscriptions.keys()):
                self.unsubscribe(topic)
            
            # Announce agent departure
            self._announce_departure()
            
            # Update status
            self.status = self.STATUS_STOPPED
            logger.info(f"Stopped agent {self.agent_id} of type {self.agent_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping agent {self.agent_id}: {e}", exc_info=True)
            self._record_error(e)
            return False
    
    def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Process a message received from a topic.
        
        Args:
            topic: The topic the message was received on.
            message: The message data as a dictionary.
            
        Returns:
            bool: True if the message was processed successfully, False otherwise.
        """
        # Call parent method for basic processing (e.g., deduplication)
        if not super().process_message(topic, message):
            return False
        
        try:
            # Extract message data
            data = message.get("data", {})
            
            # Handle control messages
            if topic.startswith(f"agents/control/{self.agent_id}"):
                return self._handle_control_message(topic, data)
            
            # Handle discovery messages
            if topic == "agents/discovery/requests" and self.status == self.STATUS_RUNNING:
                self._respond_to_discovery(data)
                return True
            
            # Default processing for other messages
            self._metrics["messages_processed"] += 1
            logger.debug(f"Processed message from topic {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing message from topic {topic}: {e}", exc_info=True)
            self._record_error(e)
            return False
    
    def _handle_control_message(self, topic: str, data: Dict[str, Any]) -> bool:
        """
        Handle a control message for this agent.
        
        Args:
            topic: The control topic
            data: The message data
            
        Returns:
            bool: True if the message was handled successfully, False otherwise
        """
        command = data.get("command")
        
        if not command:
            logger.warning(f"Received control message without command on topic {topic}")
            return False
        
        if command == "stop":
            logger.info(f"Received stop command for agent {self.agent_id}")
            threading.Thread(target=self.stop).start()
            return True
            
        elif command == "restart":
            logger.info(f"Received restart command for agent {self.agent_id}")
            def restart():
                self.stop()
                time.sleep(1)
                self.start()
            threading.Thread(target=restart).start()
            return True
            
        elif command == "status":
            logger.info(f"Received status request for agent {self.agent_id}")
            self._publish_status()
            return True
            
        elif command == "configure":
            logger.info(f"Received configuration update for agent {self.agent_id}")
            config_update = data.get("config", {})
            self.config.merge(config_update)
            return True
            
        else:
            logger.warning(f"Received unknown control command: {command}")
            return False
    
    def subscribe(self, topic: str, handler: Optional[Callable] = None) -> bool:
        """
        Subscribe to a topic with a handler function.
        
        Args:
            topic: The topic to subscribe to
            handler: Function to call when a message is received, or None to use process_message
            
        Returns:
            bool: True if the subscription was successful, False otherwise
        """
        # Use process_message as default handler
        if handler is None:
            handler = lambda message: self.process_message(topic, message)
        
        # Subscribe to the topic
        success = self.messaging.subscribe(topic, handler)
        
        if success:
            self.subscriptions[topic] = handler
            logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to subscribe to topic: {topic}")
        
        return success
    
    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: The topic to unsubscribe from
            
        Returns:
            bool: True if the unsubscription was successful, False otherwise
        """
        # Unsubscribe from the topic
        success = self.messaging.unsubscribe(topic)
        
        if success and topic in self.subscriptions:
            del self.subscriptions[topic]
            logger.info(f"Unsubscribed from topic: {topic}")
        else:
            logger.error(f"Failed to unsubscribe from topic: {topic}")
        
        return success
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to a topic.
        
        Args:
            topic: The topic to publish to
            message: The message to publish
            
        Returns:
            bool: True if the message was published successfully, False otherwise
        """
        success = self.messaging.publish(topic, message)
        
        if success:
            self._metrics["messages_sent"] += 1
            logger.debug(f"Published message to topic: {topic}")
        else:
            logger.error(f"Failed to publish message to topic: {topic}")
        
        return success
    
    def _subscribe_to_control_topic(self) -> None:
        """Subscribe to the control topic for this agent."""
        control_topic = f"agents/control/{self.agent_id}/#"
        self.subscribe(control_topic)
        
        # Also subscribe to broadcast control messages
        broadcast_topic = "agents/control/broadcast/#"
        self.subscribe(broadcast_topic)
        
        # Subscribe to discovery requests
        discovery_topic = "agents/discovery/requests"
        self.subscribe(discovery_topic)
    
    def _setup_subscriptions(self) -> None:
        """Set up subscriptions based on configuration."""
        # This can be extended in subclasses to add more subscriptions
        pass
    
    def _announce_presence(self) -> None:
        """Announce the agent's presence on the network."""
        presence_message = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "capabilities": self.capabilities,
            "timestamp": time.time()
        }
        
        # Publish to the presence topic
        self.publish("agents/presence/online", presence_message)
    
    def _announce_departure(self) -> None:
        """Announce the agent's departure from the network."""
        departure_message = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.STATUS_STOPPING,
            "timestamp": time.time()
        }
        
        # Publish to the presence topic
        self.publish("agents/presence/offline", departure_message)
    
    def _publish_status(self) -> None:
        """Publish the agent's current status."""
        status_message = self.get_status()
        
        # Publish to the status topic
        self.publish(f"agents/status/{self.agent_id}", status_message)
    
    def _respond_to_discovery(self, request_data: Dict[str, Any]) -> None:
        """
        Respond to a discovery request.
        
        Args:
            request_data: The discovery request data
        """
        # Check if the request is for this agent type
        requested_type = request_data.get("agent_type")
        if requested_type and requested_type != self.agent_type:
            return
        
        # Check if the request is for specific capabilities
        requested_capabilities = request_data.get("capabilities", [])
        if requested_capabilities:
            # Check if this agent has all the requested capabilities
            if not all(cap in self.capabilities for cap in requested_capabilities):
                return
        
        # Respond to the discovery request
        response = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "capabilities": self.capabilities,
            "request_id": request_data.get("request_id"),
            "timestamp": time.time()
        }
        
        # Publish to the discovery response topic
        self.publish("agents/discovery/responses", response)
    
    def authorize_resource(self, resource_type: str, resource_id: str, action: str) -> bool:
        """
        Check if the agent is authorized to perform an action on a resource.
        
        Args:
            resource_type: Type of resource (e.g., 'finding', 'alert')
            resource_id: ID of the resource
            action: Action to perform (e.g., 'read', 'write')
            
        Returns:
            bool: True if the action is authorized, False otherwise
        """
        # Check if the resource type is in authorizations
        if resource_type not in self.resource_authorizations:
            logger.warning(f"Resource type not in authorizations: {resource_type}")
            return False
        
        # Check if the action is allowed for this resource type
        if action not in self.resource_authorizations[resource_type]:
            logger.warning(f"Action not allowed for resource type: {action} on {resource_type}")
            return False
        
        # Additional checks can be added here (e.g., checking specific resource IDs)
        
        return True
    
    def add_resource_authorization(self, resource_type: str, actions: List[str]) -> None:
        """
        Add authorization for actions on a resource type.
        
        Args:
            resource_type: Type of resource (e.g., 'finding', 'alert')
            actions: List of actions to allow (e.g., ['read', 'write'])
        """
        if resource_type not in self.resource_authorizations:
            self.resource_authorizations[resource_type] = []
        
        for action in actions:
            if action not in self.resource_authorizations[resource_type]:
                self.resource_authorizations[resource_type].append(action)
        
        logger.debug(f"Added resource authorization for {resource_type}: {actions}")
    
    def remove_resource_authorization(self, resource_type: str, actions: Optional[List[str]] = None) -> None:
        """
        Remove authorization for actions on a resource type.
        
        Args:
            resource_type: Type of resource (e.g., 'finding', 'alert')
            actions: List of actions to remove, or None to remove all
        """
        if resource_type not in self.resource_authorizations:
            return
        
        if actions is None:
            # Remove all authorizations for this resource type
            del self.resource_authorizations[resource_type]
            logger.debug(f"Removed all resource authorizations for {resource_type}")
        else:
            # Remove specific actions
            for action in actions:
                if action in self.resource_authorizations[resource_type]:
                    self.resource_authorizations[resource_type].remove(action)
            
            # If no actions left, remove the resource type
            if not self.resource_authorizations[resource_type]:
                del self.resource_authorizations[resource_type]
            
            logger.debug(f"Removed resource authorization for {resource_type}: {actions}")
    
    def run(self) -> None:
        """
        Main processing loop for the agent.
        
        This method can be overridden by subclasses to implement custom behavior.
        It will be called in a separate thread when the agent is started.
        """
        logger.info(f"Agent {self.agent_id} main thread started")
        
        try:
            # Main processing loop
            while not self._stop_event.is_set():
                # Perform periodic tasks
                self._periodic_tasks()
                
                # Sleep to avoid high CPU usage
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error in agent {self.agent_id} main thread: {e}", exc_info=True)
            self._record_error(e)
        
        logger.info(f"Agent {self.agent_id} main thread stopped")
    
    def _periodic_tasks(self) -> None:
        """
        Perform periodic tasks.
        
        This method can be overridden by subclasses to implement custom periodic tasks.
        """
        # Example: Publish heartbeat every 60 seconds
        current_time = time.time()
        last_heartbeat = self._metrics.get("last_heartbeat", 0)
        
        if current_time - last_heartbeat > 60:
            self._publish_heartbeat()
            self._metrics["last_heartbeat"] = current_time
    
    def _publish_heartbeat(self) -> None:
        """Publish a heartbeat message."""
        heartbeat_message = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "timestamp": time.time(),
            "uptime": (time.time() - self._metrics["start_time"]) if self._metrics["start_time"] else 0
        }
        
        # Publish to the heartbeat topic
        self.publish("agents/heartbeat", heartbeat_message)