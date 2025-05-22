#!/usr/bin/env python3

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Callable, Optional, Union
from datetime import datetime

import nats
from nats.aio.client import Client as NATS
from nats.errors import ConnectionClosedError, TimeoutError as NATSTimeoutError

from .provider import MessagingProvider
from ..core.config import AgentConfig

logger = logging.getLogger("AgentFramework.Messaging.NATSProvider")

class NATSProvider(MessagingProvider):
    """
    NATS-based messaging provider implementing the architecture from the guide.
    
    Supports hierarchical topic structure:
    - agents.{environment}.{message_type}.{domain}.{specificity}
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the NATS provider.
        
        Args:
            config: Configuration containing NATS connection details
        """
        self.config = config
        self.nats = NATS()
        self.subscriptions = {}
        self.tokens = {}
        self.environment = config.get("nats.environment", "prod")
        self.servers = config.get("nats.servers", ["nats://localhost:4222"])
        self._running = False
        self._loop = None
        
    async def _connect(self):
        """Connect to NATS server."""
        try:
            await self.nats.connect(servers=self.servers)
            logger.info(f"Connected to NATS servers: {self.servers}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise
            
    async def _disconnect(self):
        """Disconnect from NATS server."""
        if self.nats.is_connected:
            await self.nats.drain()
            await self.nats.close()
            logger.info("Disconnected from NATS")
            
    def create_token(self, agent_id: str, permissions: List[str]) -> str:
        """
        Create an authentication token for an agent.
        
        Args:
            agent_id: The ID of the agent
            permissions: List of permission strings
            
        Returns:
            str: The authentication token
        """
        token = str(uuid.uuid4())
        self.tokens[token] = {
            "agent_id": agent_id,
            "permissions": permissions,
            "created_at": time.time()
        }
        return token
        
    def verify_permission(self, token: str, action: str, topic: str) -> bool:
        """
        Verify if a token has permission to perform an action on a topic.
        
        Args:
            token: The authentication token
            action: The action to perform (e.g., 'publish', 'subscribe')
            topic: The topic to perform the action on
            
        Returns:
            bool: True if the action is permitted
        """
        if token not in self.tokens:
            return False
            
        token_data = self.tokens[token]
        permissions = token_data["permissions"]
        
        # Check for specific permission format: "action:topic_pattern"
        for permission in permissions:
            if ":" in permission:
                perm_action, perm_pattern = permission.split(":", 1)
                if perm_action == action and self._matches_pattern(topic, perm_pattern):
                    return True
            elif permission == "*":
                return True
                
        return False
        
    def _matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if a topic matches a pattern with wildcards."""
        if pattern == "*":
            return True
            
        pattern_parts = pattern.split(".")
        topic_parts = topic.split(".")
        
        if len(pattern_parts) != len(topic_parts) and not pattern.endswith(">"):
            return False
            
        for i, (pattern_part, topic_part) in enumerate(zip(pattern_parts, topic_parts)):
            if pattern_part == ">":
                return True
            elif pattern_part == "*":
                continue
            elif pattern_part != topic_part:
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
            bool: True if the subscription was successful
        """
        if not self.verify_permission(token, "subscribe", topic):
            logger.warning(f"Token lacks permission to subscribe to {topic}")
            return False
            
        async def _subscribe():
            try:
                # Convert agent framework topic format to NATS hierarchical format
                nats_topic = self._convert_topic_to_nats(topic)
                
                async def message_handler(msg):
                    try:
                        # Parse message according to guide's AgentMessage structure
                        data = json.loads(msg.data.decode())
                        
                        # Extract the actual message content
                        if "data" in data:
                            # Message is already enriched, extract the data
                            callback(data["data"])
                        else:
                            # Raw message
                            callback(data)
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
                        
                sub = await self.nats.subscribe(nats_topic, cb=message_handler)
                self.subscriptions[topic] = sub
                logger.info(f"Subscribed to topic: {topic} (NATS: {nats_topic})")
                return True
            except Exception as e:
                logger.error(f"Failed to subscribe to {topic}: {e}")
                return False
                
        if self._loop and self._running:
            future = asyncio.run_coroutine_threadsafe(_subscribe(), self._loop)
            return future.result(timeout=5.0)
        else:
            logger.warning("NATS provider not running, subscription queued")
            return False
            
    def unsubscribe(self, token: str, topic: str) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            token: The authentication token
            topic: The topic to unsubscribe from
            
        Returns:
            bool: True if the unsubscription was successful
        """
        if not self.verify_permission(token, "subscribe", topic):
            return False
            
        async def _unsubscribe():
            try:
                if topic in self.subscriptions:
                    sub = self.subscriptions[topic]
                    await sub.unsubscribe()
                    del self.subscriptions[topic]
                    logger.info(f"Unsubscribed from topic: {topic}")
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to unsubscribe from {topic}: {e}")
                return False
                
        if self._loop and self._running:
            future = asyncio.run_coroutine_threadsafe(_unsubscribe(), self._loop)
            return future.result(timeout=5.0)
        else:
            return False
            
    def publish(self, token: str, topic: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to a topic.
        
        Args:
            token: The authentication token
            topic: The topic to publish to
            message: The message to publish
            
        Returns:
            bool: True if the message was published successfully
        """
        if not self.verify_permission(token, "publish", topic):
            logger.warning(f"Token lacks permission to publish to {topic}")
            return False
            
        async def _publish():
            try:
                # Convert to NATS topic format
                nats_topic = self._convert_topic_to_nats(topic)
                
                # Create message following guide's AgentMessage structure
                agent_message = self._create_agent_message(topic, message, token)
                
                # Publish
                await self.nats.publish(
                    nats_topic,
                    json.dumps(agent_message).encode()
                )
                logger.debug(f"Published message to {topic} (NATS: {nats_topic})")
                return True
            except Exception as e:
                logger.error(f"Failed to publish to {topic}: {e}")
                return False
                
        if self._loop and self._running:
            future = asyncio.run_coroutine_threadsafe(_publish(), self._loop)
            return future.result(timeout=5.0)
        else:
            logger.warning("NATS provider not running, publish failed")
            return False
            
    def _convert_topic_to_nats(self, topic: str) -> str:
        """
        Convert agent framework topic to NATS hierarchical format.
        
        Examples:
        - agents/control/agent123 -> agents.prod.control.agent123
        - agents/status/agent123 -> agents.prod.status.agent123
        - tasks/new -> agents.prod.task.general.new
        """
        parts = topic.split("/")
        
        if parts[0] == "agents":
            if len(parts) >= 3:
                # agents/control/agent123 -> agents.prod.control.agent123
                return f"agents.{self.environment}.{parts[1]}.{'.'.join(parts[2:])}"
            else:
                # agents/status -> agents.prod.status
                return f"agents.{self.environment}.{'.'.join(parts[1:])}"
        elif parts[0] == "tasks":
            # tasks/new -> agents.prod.task.general.new
            return f"agents.{self.environment}.task.general.{'.'.join(parts[1:])}"
        else:
            # Default mapping
            return f"agents.{self.environment}.general.{topic.replace('/', '.')}"
            
    def _create_agent_message(self, topic: str, message: Dict[str, Any], token: str) -> Dict[str, Any]:
        """
        Create a message following the guide's AgentMessage structure.
        """
        agent_id = self.tokens[token]["agent_id"] if token in self.tokens else "unknown"
        
        # Determine message type based on topic
        if "control" in topic:
            msg_type = "task"
        elif "status" in topic:
            msg_type = "result"
        elif "event" in topic or "presence" in topic:
            msg_type = "event"
        else:
            msg_type = "query"
            
        return {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().timestamp(),
            "version": "1.0",
            "type": msg_type,
            "source": {
                "id": agent_id,
                "type": "agent"
            },
            "target": None,
            "replyTo": None,
            "correlationId": message.get("correlation_id"),
            "context": {
                "conversationId": message.get("conversation_id", str(uuid.uuid4())),
                "metadata": message.get("metadata", {})
            },
            "payload": {
                "content": message
            },
            "routing": {
                "priority": message.get("priority", 5),
                "timeout": 30000
            }
        }
        
    def start(self) -> bool:
        """
        Start the NATS provider in a background thread.
        
        Returns:
            bool: True if started successfully
        """
        if self._running:
            return True
            
        try:
            # Create and start event loop in background thread
            import threading
            
            def run_loop():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._loop.run_until_complete(self._start_async())
                
            thread = threading.Thread(target=run_loop, daemon=True)
            thread.start()
            
            # Wait for connection
            time.sleep(1.0)
            self._running = True
            return True
        except Exception as e:
            logger.error(f"Failed to start NATS provider: {e}")
            return False
            
    async def _start_async(self):
        """Async start method."""
        await self._connect()
        
        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)
            
    def stop(self) -> bool:
        """
        Stop the NATS provider.
        
        Returns:
            bool: True if stopped successfully
        """
        if not self._running:
            return True
            
        try:
            self._running = False
            
            # Disconnect from NATS
            if self._loop:
                future = asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
                future.result(timeout=5.0)
                
            logger.info("NATS provider stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping NATS provider: {e}")
            return False