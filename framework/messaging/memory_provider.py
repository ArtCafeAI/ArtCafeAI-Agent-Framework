#!/usr/bin/env python3

import uuid
import time
import threading
import queue
import os
import pickle
import tempfile
import logging
from typing import Dict, List, Any, Callable, Optional, Set

from .provider import MessagingProvider

logger = logging.getLogger("AgentFramework.Messaging.MemoryProvider")

class MemoryMessagingProvider(MessagingProvider):
    """
    In-memory messaging provider implementation.
    
    This provider implements the messaging interface using in-memory queues and
    structures, with optional filesystem-based IPC for cross-process communication.
    It's based on the original AURA project's pubsub implementation but refactored
    to follow the provider interface pattern.
    
    Attributes:
        _topics (Dict[str, List[Callable]]): Maps topic names to list of subscribers
        _queues (Dict[str, queue.Queue]): Message queues for each topic
        _threads (Dict[str, Dict[str, threading.Thread]]): Running threads for subscribers
        _auth_tokens (Dict[str, Dict[str, Any]]): Authentication tokens
        _lock (threading.RLock): Lock for thread safety
        _ipc_dir (str): Directory for cross-process communication files
        _monitor_thread (threading.Thread): Thread for monitoring message files
    """
    
    def __init__(self, use_ipc: bool = True, ipc_dir: Optional[str] = None):
        """
        Initialize a new in-memory messaging provider.
        
        Args:
            use_ipc: Whether to use filesystem-based IPC for cross-process communication
            ipc_dir: Directory to use for IPC files, or None to use a default
        """
        self._topics: Dict[str, List[Callable]] = {}
        self._queues: Dict[str, queue.Queue] = {}
        self._threads: Dict[str, Dict[str, threading.Thread]] = {}
        self._auth_tokens: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._monitor_thread = None
        self._running = False
        
        # IPC configuration
        self._use_ipc = use_ipc
        if use_ipc:
            self._ipc_dir = ipc_dir or os.path.join(tempfile.gettempdir(), "agent_framework_pubsub")
            os.makedirs(self._ipc_dir, exist_ok=True)
            
            # Authentication tokens file
            self._auth_tokens_file = os.path.join(self._ipc_dir, "auth_tokens.pickle")
            
            # Load existing tokens if available
            self._load_auth_tokens()
        
        logger.debug("Initialized memory messaging provider")
    
    def _load_auth_tokens(self) -> None:
        """Load authentication tokens from disk."""
        if not self._use_ipc:
            return
            
        try:
            if os.path.exists(self._auth_tokens_file):
                with open(self._auth_tokens_file, 'rb') as f:
                    self._auth_tokens = pickle.load(f)
                logger.debug(f"Loaded {len(self._auth_tokens)} auth tokens from {self._auth_tokens_file}")
        except Exception as e:
            logger.error(f"Error loading auth tokens: {e}")
    
    def _save_auth_tokens(self) -> None:
        """Save authentication tokens to disk."""
        if not self._use_ipc:
            return
            
        try:
            with open(self._auth_tokens_file, 'wb') as f:
                pickle.dump(self._auth_tokens, f)
            logger.debug(f"Saved {len(self._auth_tokens)} auth tokens to {self._auth_tokens_file}")
        except Exception as e:
            logger.error(f"Error saving auth tokens: {e}")
    
    def _monitor_messages(self) -> None:
        """Monitor for new messages across all topics in IPC directory."""
        logger.info("Starting message monitor thread")
        
        while self._running:
            try:
                # Check all potential topic directories
                for item in os.listdir(self._ipc_dir):
                    if item.endswith(".pickle") and item != "auth_tokens.pickle":
                        message_file = os.path.join(self._ipc_dir, item)
                        try:
                            # Load and process the message
                            with open(message_file, 'rb') as f:
                                message = pickle.load(f)
                            
                            # Get the topic
                            topic = message.get("topic")
                            if topic:
                                # Deliver the message to subscribers
                                self._deliver_message(topic, message)
                            
                            # Delete the message file after processing
                            os.remove(message_file)
                        except Exception as e:
                            logger.error(f"Error processing message file {message_file}: {e}")
            except Exception as e:
                logger.error(f"Error in message monitor: {e}")
            
            # Sleep briefly to prevent high CPU usage
            time.sleep(0.1)
    
    def _deliver_message(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Deliver a message to subscribers of a topic.
        
        Args:
            topic: The topic the message was published to
            message: The message to deliver
        """
        with self._lock:
            # Find all matching topics (including wildcards)
            matching_topics = [t for t in self._topics.keys() 
                             if self._match_topic(t, topic) or self._match_topic(topic, t)]
            
            # Deliver to all matching topics
            for t in matching_topics:
                if t in self._queues:
                    self._queues[t].put(message)
    
    def create_token(self, agent_id: str, permissions: List[str]) -> str:
        """
        Create an authentication token for an agent.
        
        Args:
            agent_id: The ID of the agent
            permissions: List of permission strings (e.g., 'publish:topic', 'subscribe:topic/#')
            
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
            # Save tokens to disk for other processes
            if self._use_ipc:
                self._save_auth_tokens()
        
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
            
            # Check topic pattern permissions
            topic_parts = topic.split('/')
            for permission in permissions:
                # Skip non-matching permissions
                if not permission.startswith(action + ":"):
                    continue
                
                # Extract the permission topic pattern
                permission_topic = permission[len(action) + 1:]
                permission_parts = permission_topic.split('/')
                
                # Check if permission pattern matches the topic
                if self._match_topic(permission_topic, topic):
                    return True
            
            logger.warning(f"Permission denied: {action} on {topic} for token {token}")
            return False
    
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
        
        with self._lock:
            if topic not in self._topics:
                self._topics[topic] = []
                self._queues[topic] = queue.Queue()
                self._threads[topic] = {}
            
            agent_id = self._auth_tokens[token]["agent_id"]
            if agent_id in self._threads.get(topic, {}):
                # Already subscribed
                logger.debug(f"Agent {agent_id} already subscribed to {topic}")
                return True
            
            self._topics[topic].append(callback)
            
            # Create a thread to process messages for this subscription
            def worker():
                while self._running:
                    try:
                        message = self._queues[topic].get(timeout=1.0)
                        if message is None:  # Stop signal
                            break
                        callback(message)
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"Error in subscriber callback: {e}")
                    finally:
                        self._queues[topic].task_done()
            
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            self._threads[topic][agent_id] = thread
            
            logger.info(f"Agent {agent_id} subscribed to {topic}")
            return True
    
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
        
        with self._lock:
            if topic not in self._topics:
                logger.warning(f"Cannot unsubscribe from non-existent topic: {topic}")
                return False
            
            agent_id = self._auth_tokens[token]["agent_id"]
            if agent_id not in self._threads.get(topic, {}):
                logger.warning(f"Agent {agent_id} is not subscribed to {topic}")
                return False
            
            # Send stop signal to the worker thread
            self._queues[topic].put(None)
            self._threads[topic][agent_id].join(timeout=1.0)
            del self._threads[topic][agent_id]
            
            # Remove callback from the topics list
            # This is a simplification; in a real implementation we'd need to track which callback
            # belongs to which agent
            if agent_id == len(self._topics[topic]) - 1:
                self._topics[topic].pop()
            
            logger.info(f"Agent {agent_id} unsubscribed from {topic}")
            return True
    
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
        
        # Enrich the message with metadata
        enriched_message = self.enrich_message(topic, message)
        
        if self._use_ipc:
            # Save the message to disk for other processes to pick up
            message_file = os.path.join(self._ipc_dir, f"msg_{enriched_message['message_id']}.pickle")
            try:
                with open(message_file, 'wb') as f:
                    pickle.dump(enriched_message, f)
            except Exception as e:
                logger.error(f"Error saving message: {e}")
                return False
        
        with self._lock:
            # Check if topic exists, create it if not
            if topic not in self._topics:
                self._topics[topic] = []
                self._queues[topic] = queue.Queue()
                self._threads[topic] = {}
            
            # Also check for wildcard subscriptions
            topics_to_publish = [t for t in self._topics.keys() 
                              if self._match_topic(t, topic) or self._match_topic(topic, t)]
            
            # Publish to all matching topics in this process
            for t in topics_to_publish:
                self._queues[t].put(enriched_message)
            
            logger.debug(f"Published message to {topic} (matched {len(topics_to_publish)} topics)")
            return True
    
    def start(self) -> bool:
        """
        Start the messaging provider, initializing resources.
        
        Returns:
            bool: True if the provider was started successfully, False otherwise
        """
        if self._running:
            logger.warning("Messaging provider already running")
            return True
            
        self._running = True
        
        if self._use_ipc:
            # Start message monitoring thread for IPC
            self._monitor_thread = threading.Thread(target=self._monitor_messages, daemon=True)
            self._monitor_thread.start()
        
        logger.info("Memory messaging provider started")
        return True
    
    def stop(self) -> bool:
        """
        Stop the messaging provider, cleaning up resources.
        
        Returns:
            bool: True if the provider was stopped successfully, False otherwise
        """
        if not self._running:
            logger.warning("Messaging provider already stopped")
            return True
            
        self._running = False
        
        # Stop all subscription threads
        for topic, agents in self._threads.items():
            for agent_id, thread in agents.items():
                try:
                    self._queues[topic].put(None)  # Send stop signal
                    thread.join(timeout=1.0)
                except Exception as e:
                    logger.error(f"Error stopping thread for agent {agent_id} on topic {topic}: {e}")
        
        # Wait for monitor thread to stop
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        
        logger.info("Memory messaging provider stopped")
        return True
    
    def _match_topic(self, pattern: str, topic: str) -> bool:
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
        
        # If pattern ends with #, it matches any topic with the same prefix
        if pattern_parts[-1] == "#":
            if len(pattern_parts) - 1 > len(topic_parts):
                return False
            return pattern_parts[:-1] == topic_parts[:len(pattern_parts) - 1]
        
        # If pattern has different number of parts, it doesn't match
        if len(pattern_parts) != len(topic_parts):
            return False
        
        # Check each part
        for i, part in enumerate(pattern_parts):
            if part != "+" and part != topic_parts[i]:
                return False
        
        return True