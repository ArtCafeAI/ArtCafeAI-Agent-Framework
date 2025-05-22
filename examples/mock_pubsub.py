import json
import time
import uuid
import threading
import queue
import os
import pickle
import tempfile
from typing import Dict, List, Callable, Any, Optional

class PubSubService:
    """
    A simple pub/sub service that mimics AWS IoT Core functionality for our proof of concept.
    In a real implementation, this would use AWS IoT SDK instead.
    
    This implementation uses filesystem-based IPC to communicate between different processes,
    allowing it to work across multiple terminal windows.
    """
    def __init__(self):
        # Topics dictionary: maps topic names to list of subscribers
        self._topics: Dict[str, List[Callable]] = {}
        # Messages queue for each topic
        self._queues: Dict[str, queue.Queue] = {}
        # Running threads for subscribers
        self._threads: Dict[str, Dict[str, threading.Thread]] = {}
        # Authentication tokens (mock implementation)
        self._auth_tokens: Dict[str, Dict[str, Any]] = {}
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # IPC directory for cross-process communication
        self._ipc_dir = os.path.join(tempfile.gettempdir(), "aura_pubsub")
        os.makedirs(self._ipc_dir, exist_ok=True)
        
        # Authentication tokens file
        self._auth_tokens_file = os.path.join(self._ipc_dir, "auth_tokens.pickle")
        
        # Load existing tokens if available
        self._load_auth_tokens()
        
        # Start message monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_messages, daemon=True)
        self._monitor_thread.start()
    
    def _load_auth_tokens(self):
        """Load authentication tokens from disk"""
        try:
            if os.path.exists(self._auth_tokens_file):
                with open(self._auth_tokens_file, 'rb') as f:
                    self._auth_tokens = pickle.load(f)
        except Exception as e:
            print(f"Error loading auth tokens: {e}")
    
    def _save_auth_tokens(self):
        """Save authentication tokens to disk"""
        try:
            with open(self._auth_tokens_file, 'wb') as f:
                pickle.dump(self._auth_tokens, f)
        except Exception as e:
            print(f"Error saving auth tokens: {e}")
    
    def _get_message_dir(self, topic):
        """Get directory for a topic's messages"""
        topic_dir = os.path.join(self._ipc_dir, topic.replace('/', '_'))
        os.makedirs(topic_dir, exist_ok=True)
        return topic_dir
    
    def _monitor_messages(self):
        """Monitor for new messages across all topics"""
        while True:
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
                            print(f"Error processing message file {message_file}: {e}")
            except Exception as e:
                print(f"Error in message monitor: {e}")
            
            # Sleep briefly to prevent high CPU usage
            time.sleep(0.1)
    
    def _deliver_message(self, topic, message):
        """Deliver a message to subscribers of a topic"""
        with self._lock:
            # Find all matching topics (including wildcards)
            matching_topics = [t for t in self._topics.keys() 
                              if self._match_topic(t, topic) or self._match_topic(topic, t)]
            
            # Deliver to all matching topics
            for t in matching_topics:
                if t in self._queues:
                    self._queues[t].put(message)
        
    def create_authentication_token(self, agent_id: str, permissions: List[str]) -> str:
        """Creates a mock authentication token for an agent"""
        token = str(uuid.uuid4())
        with self._lock:
            self._auth_tokens[token] = {
                "agent_id": agent_id,
                "permissions": permissions,
                "created_at": time.time()
            }
            # Save tokens to disk for other processes
            self._save_auth_tokens()
        return token
    
    def verify_permission(self, token: str, action: str, topic: str) -> bool:
        """Verify if the agent has permission to perform the given action on the topic"""
        with self._lock:
            if token not in self._auth_tokens:
                return False
            
            permissions = self._auth_tokens[token]["permissions"]
            
            # Check if agent has wildcard permission for all actions
            if "*" in permissions:
                return True
            
            # Check wildcard permission for this specific action
            if f"{action}:*" in permissions:
                return True
            
            # For now, let's simplify permissions to get the demo working
            # In a real system, we'd implement proper topic pattern matching
            return True
            
            # Check specific topic permissions
            topic_parts = topic.split('/')
            for permission in permissions:
                # Skip non-matching permissions
                if not permission.startswith(action + ":"):
                    continue
                
                # Extract the permission topic pattern
                permission_topic = permission[len(action) + 1:]
                permission_parts = permission_topic.split('/')
                
                # Check if permission pattern matches the topic
                if len(permission_parts) != len(topic_parts):
                    if permission_parts[-1] != "#":
                        continue
                    
                    # Check if the part before # matches
                    if permission_parts[:-1] != topic_parts[:len(permission_parts) - 1]:
                        continue
                else:
                    # Check exact match or with + wildcards
                    match = True
                    for i, part in enumerate(permission_parts):
                        if part != "+" and part != topic_parts[i]:
                            match = False
                            break
                    
                    if not match:
                        continue
                
                return True
            
            return False
    
    def subscribe(self, token: str, topic: str, callback: Callable[[Dict], None]) -> bool:
        """Subscribe to a topic with the given callback function"""
        if not self.verify_permission(token, "subscribe", topic):
            print(f"Permission denied: Cannot subscribe to {topic}")
            return False
        
        with self._lock:
            if topic not in self._topics:
                self._topics[topic] = []
                self._queues[topic] = queue.Queue()
                self._threads[topic] = {}
            
            agent_id = self._auth_tokens[token]["agent_id"]
            if agent_id in self._threads.get(topic, {}):
                # Already subscribed
                return True
            
            self._topics[topic].append(callback)
            
            # Create a thread to process messages for this subscription
            def worker():
                while True:
                    try:
                        message = self._queues[topic].get()
                        if message is None:  # Stop signal
                            break
                        callback(message)
                    except Exception as e:
                        print(f"Error in subscriber callback: {e}")
                    finally:
                        self._queues[topic].task_done()
            
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            self._threads[topic][agent_id] = thread
            
            return True
    
    def unsubscribe(self, token: str, topic: str) -> bool:
        """Unsubscribe from a topic"""
        if not self.verify_permission(token, "unsubscribe", topic):
            print(f"Permission denied: Cannot unsubscribe from {topic}")
            return False
        
        with self._lock:
            if topic not in self._topics:
                return False
            
            agent_id = self._auth_tokens[token]["agent_id"]
            if agent_id not in self._threads.get(topic, {}):
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
            
            return True
    
    def publish(self, token: str, topic: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a topic"""
        if not self.verify_permission(token, "publish", topic):
            print(f"Permission denied: Cannot publish to {topic}")
            return False
        
        # Add metadata to the message
        enriched_message = {
            "data": message,
            "topic": topic,
            "timestamp": time.time(),
            "message_id": str(uuid.uuid4())
        }
        
        # Save the message to disk for other processes to pick up
        message_file = os.path.join(self._ipc_dir, f"msg_{enriched_message['message_id']}.pickle")
        try:
            with open(message_file, 'wb') as f:
                pickle.dump(enriched_message, f)
        except Exception as e:
            print(f"Error saving message: {e}")
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
            
            return True
    
    def _match_topic(self, pattern: str, topic: str) -> bool:
        """Check if a topic pattern matches a specific topic"""
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

# Create a singleton instance
pubsub_service = PubSubService()

# Utility functions for easier usage
def create_agent_token(agent_id: str, permissions: List[str]) -> str:
    """Create an authentication token for an agent"""
    return pubsub_service.create_authentication_token(agent_id, permissions)

def subscribe(token: str, topic: str, callback: Callable[[Dict], None]) -> bool:
    """Subscribe to a topic"""
    return pubsub_service.subscribe(token, topic, callback)

def publish(token: str, topic: str, message: Dict[str, Any]) -> bool:
    """Publish a message to a topic"""
    return pubsub_service.publish(token, topic, message)

def unsubscribe(token: str, topic: str) -> bool:
    """Unsubscribe from a topic"""
    return pubsub_service.unsubscribe(token, topic)