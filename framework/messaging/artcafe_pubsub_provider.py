#!/usr/bin/env python3

import json
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional, Set, Union

import websockets
from websockets.exceptions import ConnectionClosed

from .provider import MessagingProvider
from ..auth.ssh_auth_provider import SSHAuthProvider

logger = logging.getLogger("AgentFramework.Messaging.ArtCafePubSubProvider")

class ArtCafePubSubProvider(MessagingProvider):
    """
    Messaging provider implementation using ArtCafe.ai PubSub service.
    
    This provider implements messaging through the ArtCafe.ai WebSocket API,
    with support for authentication, pub/sub messaging, and heartbeats.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """
        Initialize the ArtCafe PubSub messaging provider.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary
        """
        super().__init__(agent_id)
        
        self.config = config
        self.api_config = config.get("api", {})
        self.auth_config = config.get("auth", {})
        self.messaging_config = config.get("messaging", {})
        
        # Extract configuration values
        self.api_endpoint = self.api_config.get("endpoint", "https://api.artcafe.ai")
        self.ws_endpoint = self.api_config.get("websocket_endpoint", "wss://api.artcafe.ai/ws")
        self.heartbeat_interval = self.messaging_config.get("heartbeat_interval", 30)
        
        # Set up authentication provider
        self.auth_provider = SSHAuthProvider(config)
        
        # WebSocket connection
        self.ws = None
        self.ws_connected = False
        self.running = False
        self.reconnect_delay = 1
        self.max_reconnect_delay = 120
        
        # Message handlers
        self.topic_handlers = {}
        self.message_buffer = []
        
        # Tasks
        self.heartbeat_task = None
        self.process_task = None
    
    async def connect(self) -> bool:
        """
        Connect to the ArtCafe PubSub WebSocket server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.ws_connected:
            return True
        
        try:
            # Authenticate if needed
            if not self.auth_provider.is_authenticated():
                success, error = await self.auth_provider.authenticate()
                if not success:
                    logger.error(f"Authentication failed: {error}")
                    return False
            
            # Prepare headers
            headers = self.auth_provider.get_headers()
            
            # Connect to WebSocket
            agent_id = self.agent_id
            self.ws = await websockets.connect(
                f"{self.ws_endpoint}/agent/{agent_id}",
                extra_headers=headers
            )
            
            self.ws_connected = True
            self.reconnect_delay = 1  # Reset backoff on successful connection
            
            logger.info(f"Connected to ArtCafe PubSub service")
            
            # Start heartbeat task
            if self.heartbeat_task is None:
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Start message processing task
            if self.process_task is None:
                self.process_task = asyncio.create_task(self._process_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            self.ws_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the WebSocket server.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        if not self.ws_connected or self.ws is None:
            return True
        
        try:
            # Cancel tasks
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                self.heartbeat_task = None
            
            if self.process_task:
                self.process_task.cancel()
                self.process_task = None
            
            # Close WebSocket
            await self.ws.close()
            self.ws = None
            self.ws_connected = False
            
            logger.info("Disconnected from ArtCafe PubSub service")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
            return False
    
    async def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to a topic.
        
        Args:
            topic: The topic to publish to
            message: The message to publish
            
        Returns:
            bool: True if the message was published successfully, False otherwise
        """
        if not self.ws_connected:
            if not await self.connect():
                return False
        
        try:
            # Prepare message envelope
            envelope = {
                "type": "message",
                "id": str(uuid.uuid4()),
                "topic": topic,
                "data": message,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send message
            await self.ws.send(json.dumps(envelope))
            logger.debug(f"Published message to topic: {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing message to {topic}: {str(e)}")
            self.ws_connected = False
            return False
    
    async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Subscribe to a topic with a handler function.
        
        Args:
            topic: The topic to subscribe to
            handler: Function to call when a message is received
            
        Returns:
            bool: True if the subscription was successful, False otherwise
        """
        if not self.ws_connected:
            if not await self.connect():
                return False
        
        try:
            # Register handler
            if topic not in self.topic_handlers:
                self.topic_handlers[topic] = []
            
            if handler not in self.topic_handlers[topic]:
                self.topic_handlers[topic].append(handler)
            
            # Send subscription request
            subscription_request = {
                "type": "subscribe",
                "id": str(uuid.uuid4()),
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.ws.send(json.dumps(subscription_request))
            logger.info(f"Subscribed to topic: {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to {topic}: {str(e)}")
            return False
    
    async def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: The topic to unsubscribe from
            
        Returns:
            bool: True if the unsubscription was successful, False otherwise
        """
        if not self.ws_connected:
            if not await self.connect():
                return False
        
        try:
            # Remove handlers
            if topic in self.topic_handlers:
                del self.topic_handlers[topic]
            
            # Send unsubscription request
            unsubscription_request = {
                "type": "unsubscribe",
                "id": str(uuid.uuid4()),
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.ws.send(json.dumps(unsubscription_request))
            logger.info(f"Unsubscribed from topic: {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing from {topic}: {str(e)}")
            return False
    
    async def authenticate(self, permissions: List[str]) -> bool:
        """
        Authenticate with the messaging system.
        
        Args:
            permissions: List of permission strings to request
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        # Authentication is handled by the SSHAuthProvider
        success, error = await self.auth_provider.authenticate()
        return success
    
    async def start(self) -> bool:
        """
        Start the messaging provider.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        self.running = True
        
        # Connect to WebSocket server
        if not await self.connect():
            return False
        
        return True
    
    async def stop(self) -> bool:
        """
        Stop the messaging provider.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        self.running = False
        
        # Disconnect from WebSocket server
        await self.disconnect()
        
        return True
    
    async def _heartbeat_loop(self) -> None:
        """
        Send periodic heartbeats to keep the connection alive.
        """
        while self.running and self.ws_connected:
            try:
                # Send heartbeat
                heartbeat = {
                    "type": "heartbeat",
                    "id": f"hb-{uuid.uuid4()}",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "agent_id": self.agent_id,
                        "status": "online"
                    }
                }
                
                await self.ws.send(json.dumps(heartbeat))
                logger.debug("Sent heartbeat")
                
                # Wait for next heartbeat interval
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error sending heartbeat: {str(e)}")
                await asyncio.sleep(5)  # Shorter wait on error
    
    async def _process_messages(self) -> None:
        """
        Process incoming WebSocket messages.
        """
        while self.running:
            try:
                if not self.ws_connected or self.ws is None:
                    await asyncio.sleep(1)
                    continue
                
                # Receive message
                message_text = await self.ws.recv()
                
                try:
                    # Parse message
                    message = json.loads(message_text)
                    
                    # Process message based on type
                    if message["type"] == "message":
                        await self._handle_pubsub_message(message)
                    elif message["type"] == "ping":
                        await self._handle_ping(message)
                    elif message["type"] == "command":
                        await self._handle_command(message)
                    elif message["type"] == "error":
                        await self._handle_error(message)
                    else:
                        logger.warning(f"Unknown message type: {message['type']}")
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON message: {message_text}")
                except KeyError as e:
                    logger.error(f"Missing field in message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                
            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self.ws_connected = False
                await self._attempt_reconnect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message processing loop: {str(e)}")
                self.ws_connected = False
                await self._attempt_reconnect()
    
    async def _attempt_reconnect(self) -> None:
        """
        Attempt to reconnect to the WebSocket server with exponential backoff.
        """
        if not self.running:
            return
        
        # Sleep with exponential backoff
        sleep_time = min(self.reconnect_delay, self.max_reconnect_delay)
        logger.info(f"Attempting to reconnect in {sleep_time}s")
        await asyncio.sleep(sleep_time)
        self.reconnect_delay *= 2
        
        # Attempt to reconnect
        if await self.connect():
            # Resubscribe to topics
            for topic in self.topic_handlers.keys():
                subscription_request = {
                    "type": "subscribe",
                    "id": str(uuid.uuid4()),
                    "topic": topic,
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.ws.send(json.dumps(subscription_request))
                logger.info(f"Resubscribed to topic: {topic}")
    
    async def _handle_pubsub_message(self, message: Dict[str, Any]) -> None:
        """
        Handle a pub/sub message from a topic.
        
        Args:
            message: The message to handle
        """
        topic = message.get("topic")
        data = message.get("data", {})
        
        if not topic:
            logger.warning("Received message without topic")
            return
        
        # Find matching topic handlers
        handlers = []
        
        # Exact match
        if topic in self.topic_handlers:
            handlers.extend(self.topic_handlers[topic])
        
        # Wildcard matches
        for pattern, pattern_handlers in self.topic_handlers.items():
            if "#" in pattern and self._topic_matches(pattern, topic):
                handlers.extend(pattern_handlers)
        
        # Call handlers
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in message handler for topic {topic}: {str(e)}")
    
    async def _handle_ping(self, message: Dict[str, Any]) -> None:
        """
        Handle a ping message.
        
        Args:
            message: The message to handle
        """
        ping_id = message.get("id")
        
        # Send pong response
        pong = {
            "type": "pong",
            "id": str(uuid.uuid4()),
            "ping_id": ping_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.ws.send(json.dumps(pong))
        logger.debug(f"Responded to ping {ping_id}")
    
    async def _handle_command(self, message: Dict[str, Any]) -> None:
        """
        Handle a command message.
        
        Args:
            message: The message to handle
        """
        command_id = message.get("id")
        command = message.get("data", {}).get("command")
        
        if not command:
            logger.warning(f"Received command message without command: {message}")
            return
        
        logger.info(f"Received command: {command}")
        
        # Special handling for system commands
        if command == "reconnect":
            await self.disconnect()
            await self.connect()
            
            # Send response
            response = {
                "type": "response",
                "id": str(uuid.uuid4()),
                "command_id": command_id,
                "data": {
                    "status": "success",
                    "message": "Reconnected to messaging service"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.ws.send(json.dumps(response))
            
        # Other commands would be handled by the agent
    
    async def _handle_error(self, message: Dict[str, Any]) -> None:
        """
        Handle an error message.
        
        Args:
            message: The message to handle
        """
        error_code = message.get("data", {}).get("code")
        error_message = message.get("data", {}).get("message")
        
        logger.error(f"Received error from server: {error_code} - {error_message}")
        
        # Handle authentication errors
        if error_code == "auth_error":
            # Reauthenticate
            success, _ = await self.auth_provider.authenticate()
            
            if success:
                # Reconnect with new token
                await self.disconnect()
                await self.connect()
    
    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """
        Check if a topic matches a pattern with wildcards.
        
        Args:
            pattern: The pattern with possible wildcards
            topic: The topic to match
            
        Returns:
            bool: True if the topic matches the pattern, False otherwise
        """
        # Split into segments
        pattern_parts = pattern.split('/')
        topic_parts = topic.split('/')
        
        # Handle # wildcard (matches any number of segments)
        if "#" in pattern_parts:
            # Find position of #
            hash_pos = pattern_parts.index("#")
            
            # Check if parts before # match
            if pattern_parts[:hash_pos] != topic_parts[:hash_pos]:
                return False
            
            # # must be the last segment
            if hash_pos != len(pattern_parts) - 1:
                logger.warning(f"Invalid pattern: {pattern} (# must be the last segment)")
                return False
            
            return True
        
        # Handle + wildcard (matches exactly one segment)
        if len(pattern_parts) != len(topic_parts):
            return False
        
        for p_part, t_part in zip(pattern_parts, topic_parts):
            if p_part != "+" and p_part != t_part:
                return False
        
        return True