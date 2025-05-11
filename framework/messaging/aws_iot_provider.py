#!/usr/bin/env python3

import uuid
import time
import json
import logging
import threading
from typing import Dict, List, Any, Callable, Optional, Set

try:
    import boto3
    import awsiot
    from awsiot import mqtt_connection_builder
    from awscrt import mqtt, io, auth, http
    AWS_IOT_AVAILABLE = True
except ImportError:
    AWS_IOT_AVAILABLE = False

from .provider import MessagingProvider

logger = logging.getLogger("AgentFramework.Messaging.AWSIoTProvider")

class AWSIoTMessagingProvider(MessagingProvider):
    """
    AWS IoT Core messaging provider implementation.
    
    This provider implements the messaging interface using AWS IoT Core for
    robust, secure, and scalable messaging between agents. It handles authentication,
    topic subscription, and message publishing through AWS IoT's MQTT service.
    
    Attributes:
        _auth_tokens (Dict[str, Dict[str, Any]]): Authentication tokens
        _subscriptions (Dict[str, Dict[str, Any]]): Active subscriptions
        _lock (threading.RLock): Lock for thread safety
        _connection (Optional[mqtt.Connection]): MQTT connection to AWS IoT Core
        _callbacks (Dict[str, List[Callable]]): Registered callbacks for topics
    """
    
    def __init__(self, 
                 endpoint: str, 
                 cert_path: str, 
                 key_path: str, 
                 ca_path: str, 
                 client_id: Optional[str] = None,
                 region: str = "us-east-1"):
        """
        Initialize a new AWS IoT messaging provider.
        
        Args:
            endpoint: AWS IoT Core endpoint URL
            cert_path: Path to the device certificate file
            key_path: Path to the private key file
            ca_path: Path to the CA certificate file
            client_id: Client ID for IoT Core connection, or None to generate one
            region: AWS region name
        
        Raises:
            ImportError: If the AWS IoT device SDK is not available
        """
        if not AWS_IOT_AVAILABLE:
            raise ImportError(
                "AWS IoT Core provider requires the AWS IoT Device SDK. "
                "Please install it with: pip install awsiotsdk"
            )
        
        self._endpoint = endpoint
        self._cert_path = cert_path
        self._key_path = key_path
        self._ca_path = ca_path
        self._client_id = client_id or f"agent-framework-{str(uuid.uuid4())[:8]}"
        self._region = region
        
        self._auth_tokens = {}
        self._subscriptions = {}
        self._callbacks = {}
        self._lock = threading.RLock()
        
        self._connection = None
        self._is_connected = False
        self._running = False
        
        logger.debug(f"Initialized AWS IoT messaging provider with endpoint {endpoint}")
    
    def create_token(self, agent_id: str, permissions: List[str]) -> str:
        """
        Create an authentication token for an agent.
        
        In the AWS IoT provider, this doesn't directly create AWS credentials,
        but rather creates an internal token that maps to IoT Core permissions.
        The actual IoT Core authentication happens via certificates.
        
        Args:
            agent_id: The ID of the agent
            permissions: List of permission strings
            
        Returns:
            str: The authentication token
        """
        token = str(uuid.uuid4())
        
        with self._lock:
            self._auth_tokens[token] = {
                "agent_id": agent_id,
                "permissions": permissions,
                "created_at": time.time()
            }
        
        logger.debug(f"Created token for agent {agent_id} with {len(permissions)} permissions")
        return token
    
    def verify_permission(self, token: str, action: str, topic: str) -> bool:
        """
        Verify if a token has permission to perform an action on a topic.
        
        Args:
            token: The authentication token
            action: The action to perform (e.g., 'publish', 'subscribe')
            topic: The topic to perform the action on
            
        Returns:
            bool: True if the action is permitted, False otherwise
        """
        with self._lock:
            if token not in self._auth_tokens:
                logger.warning(f"Token not found: {token}")
                return False
            
            permissions = self._auth_tokens[token]["permissions"]
            
            # Check if agent has wildcard permission for all actions
            if "*" in permissions:
                return True
            
            # Check wildcard permission for this specific action
            if f"{action}:*" in permissions:
                return True
            
            # Check specific topic permissions
            for permission in permissions:
                if permission.startswith(f"{action}:"):
                    permission_topic = permission[len(action) + 1:]
                    
                    # Check if permission topic matches the requested topic
                    if self._topic_matches(permission_topic, topic):
                        return True
            
            logger.warning(f"Permission denied: {action} on {topic} for token {token}")
            return False
    
    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """
        Check if a topic pattern matches a specific topic.
        
        Args:
            pattern: The topic pattern, which may include wildcards
            topic: The specific topic string
            
        Returns:
            bool: True if the pattern matches the topic, False otherwise
        """
        pattern_parts = pattern.split('/')
        topic_parts = topic.split('/')
        
        # Handle trailing wildcards (#)
        if pattern_parts[-1] == "#":
            if len(pattern_parts) - 1 > len(topic_parts):
                return False
            return pattern_parts[:-1] == topic_parts[:len(pattern_parts) - 1]
        
        # Different number of parts means no match (unless wildcards)
        if len(pattern_parts) != len(topic_parts):
            return False
        
        # Check each part
        for pattern_part, topic_part in zip(pattern_parts, topic_parts):
            if pattern_part != "+" and pattern_part != topic_part:
                return False
        
        return True
    
    def subscribe(self, token: str, topic: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Subscribe to a topic with a callback function.
        
        Args:
            token: The authentication token
            topic: The topic to subscribe to
            callback: Function to call when a message is received
            
        Returns:
            bool: True if the subscription was successful, False otherwise
        """
        if not self.verify_permission(token, "subscribe", topic):
            logger.warning(f"Permission denied: Cannot subscribe to {topic}")
            return False
        
        if not self._is_connected:
            logger.error("Cannot subscribe: not connected to AWS IoT Core")
            return False
        
        with self._lock:
            agent_id = self._auth_tokens[token]["agent_id"]
            
            # Register the callback
            if topic not in self._callbacks:
                self._callbacks[topic] = []
            
            # Add the callback if not already registered
            if callback not in self._callbacks[topic]:
                self._callbacks[topic].append(callback)
            
            # Check if we're already subscribed to this topic
            if topic in self._subscriptions:
                logger.debug(f"Already subscribed to {topic}, adding new callback")
                return True
            
            # Subscribe to the topic in AWS IoT Core
            try:
                subscribe_future, _ = self._connection.subscribe(
                    topic=topic,
                    qos=mqtt.QoS.AT_LEAST_ONCE,
                    callback=self._on_message_received
                )
                subscribe_result = subscribe_future.result(5)  # Wait for 5 seconds
                
                if subscribe_result['qos'] is not None:
                    # Subscription succeeded
                    self._subscriptions[topic] = {
                        "agent_id": agent_id,
                        "qos": subscribe_result['qos'],
                        "time": time.time()
                    }
                    logger.info(f"Subscribed to {topic} with QoS {subscribe_result['qos']}")
                    return True
                else:
                    logger.error(f"Failed to subscribe to {topic}")
                    return False
                
            except Exception as e:
                logger.error(f"Error subscribing to {topic}: {e}")
                return False
    
    def unsubscribe(self, token: str, topic: str) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            token: The authentication token
            topic: The topic to unsubscribe from
            
        Returns:
            bool: True if the unsubscription was successful, False otherwise
        """
        if not self.verify_permission(token, "unsubscribe", topic):
            logger.warning(f"Permission denied: Cannot unsubscribe from {topic}")
            return False
        
        if not self._is_connected:
            logger.error("Cannot unsubscribe: not connected to AWS IoT Core")
            return False
        
        with self._lock:
            agent_id = self._auth_tokens[token]["agent_id"]
            
            # Check if we're subscribed to this topic
            if topic not in self._subscriptions:
                logger.warning(f"Not subscribed to {topic}")
                return False
            
            # Only allow the agent that subscribed to unsubscribe
            if self._subscriptions[topic]["agent_id"] != agent_id:
                logger.warning(f"Agent {agent_id} did not create the subscription to {topic}")
                return False
            
            # Unsubscribe from the topic in AWS IoT Core
            try:
                unsubscribe_future, _ = self._connection.unsubscribe(topic)
                unsubscribe_future.result(5)  # Wait for 5 seconds
                
                # Clean up resources
                del self._subscriptions[topic]
                if topic in self._callbacks:
                    del self._callbacks[topic]
                
                logger.info(f"Unsubscribed from {topic}")
                return True
                
            except Exception as e:
                logger.error(f"Error unsubscribing from {topic}: {e}")
                return False
    
    def publish(self, token: str, topic: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to a topic.
        
        Args:
            token: The authentication token
            topic: The topic to publish to
            message: The message to publish
            
        Returns:
            bool: True if the message was published successfully, False otherwise
        """
        if not self.verify_permission(token, "publish", topic):
            logger.warning(f"Permission denied: Cannot publish to {topic}")
            return False
        
        if not self._is_connected:
            logger.error("Cannot publish: not connected to AWS IoT Core")
            return False
        
        # Enrich the message with metadata
        enriched_message = self.enrich_message(topic, message)
        
        # Convert to JSON for publishing
        try:
            message_json = json.dumps(enriched_message)
            
            # Publish the message to AWS IoT Core
            publish_future, _ = self._connection.publish(
                topic=topic,
                payload=message_json,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
            publish_future.result(5)  # Wait for 5 seconds
            
            logger.debug(f"Published message to {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}")
            return False
    
    def start(self) -> bool:
        """
        Start the messaging provider, initializing resources.
        
        Returns:
            bool: True if the provider was started successfully, False otherwise
        """
        if self._running:
            logger.warning("AWS IoT messaging provider already running")
            return True
        
        if not AWS_IOT_AVAILABLE:
            logger.error("Cannot start AWS IoT provider: SDK not available")
            return False
        
        # Initialize AWS IoT connection
        try:
            # Create MQTT connection
            self._connection = mqtt_connection_builder.mtls_from_path(
                endpoint=self._endpoint,
                cert_filepath=self._cert_path,
                pri_key_filepath=self._key_path,
                ca_filepath=self._ca_path,
                client_id=self._client_id,
                clean_session=True,
                keep_alive_secs=30
            )
            
            # Connect to AWS IoT Core
            connect_future = self._connection.connect()
            connect_future.result(5)  # Wait for 5 seconds
            
            self._is_connected = True
            self._running = True
            
            logger.info(f"Connected to AWS IoT Core at {self._endpoint}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to AWS IoT Core: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the messaging provider, cleaning up resources.
        
        Returns:
            bool: True if the provider was stopped successfully, False otherwise
        """
        if not self._running:
            logger.warning("AWS IoT messaging provider already stopped")
            return True
        
        # Disconnect from AWS IoT Core
        try:
            if self._connection and self._is_connected:
                disconnect_future = self._connection.disconnect()
                disconnect_future.result(5)  # Wait for 5 seconds
            
            self._is_connected = False
            self._running = False
            
            logger.info("Disconnected from AWS IoT Core")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from AWS IoT Core: {e}")
            return False
    
    def _on_message_received(self, topic: str, payload: bytes, **kwargs) -> None:
        """
        Handle a message received from AWS IoT Core.
        
        Args:
            topic: The topic the message was received on
            payload: The message payload as bytes
            **kwargs: Additional keyword arguments
        """
        try:
            # Convert payload to dictionary
            message_json = payload.decode('utf-8')
            message = json.loads(message_json)
            
            with self._lock:
                # Find callbacks for this topic
                callbacks = []
                
                # Direct topic match
                if topic in self._callbacks:
                    callbacks.extend(self._callbacks[topic])
                
                # Wildcard topic matches
                for pattern, pattern_callbacks in self._callbacks.items():
                    if '#' in pattern or '+' in pattern:
                        if self._topic_matches(pattern, topic):
                            callbacks.extend(pattern_callbacks)
                
                # Execute callbacks
                for callback in callbacks:
                    try:
                        callback(message)
                    except Exception as e:
                        logger.error(f"Error in message callback for topic {topic}: {e}")
                
                logger.debug(f"Processed message from topic {topic} with {len(callbacks)} callbacks")
                
        except Exception as e:
            logger.error(f"Error processing message from topic {topic}: {e}")