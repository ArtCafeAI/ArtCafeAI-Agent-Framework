"""
Simple Agent - A minimal agent implementation for quick starts.

This module provides a simplified agent that requires minimal configuration,
following best practices to "start simple".
"""

import asyncio
from typing import Optional, Dict, Any, Callable
from .enhanced_agent import EnhancedAgent
from ..messaging.memory_provider import MemoryMessagingProvider


class SimpleAgent(EnhancedAgent):
    """
    A simplified agent that works with minimal configuration.
    
    Perfect for getting started quickly without complex setup.
    
    Example:
        ```python
        agent = SimpleAgent("my-agent")
        
        @agent.on_message("hello")
        def handle_hello(message):
            return {"response": "Hello back!"}
            
        agent.run()
        ```
    """
    
    def __init__(
        self, 
        agent_id: str = None,
        agent_type: str = "simple",
        use_memory_messaging: bool = True
    ):
        """
        Initialize a simple agent with sensible defaults.
        
        Args:
            agent_id: Optional agent ID (auto-generated if not provided)
            agent_type: Type of agent (default: "simple")
            use_memory_messaging: Use in-memory messaging for easy testing
        """
        # Create minimal config with memory messaging by default
        config = {
            "agent": {
                "type": agent_type,
                "id": agent_id
            }
        }
        
        if use_memory_messaging:
            config["messaging"] = {
                "provider": "memory",
                "memory": {}
            }
        
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            config=config
        )
        
        self._message_handlers = {}
        self._started = False
        
    def on_message(self, topic: str):
        """
        Decorator for registering message handlers.
        
        Example:
            ```python
            @agent.on_message("calculate")
            def calculate(message):
                return {"result": message["a"] + message["b"]}
            ```
        """
        def decorator(func: Callable):
            self._message_handlers[topic] = func
            if self._started:
                # If agent is already running, subscribe immediately
                self.subscribe(topic)
            return func
        return decorator
    
    async def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """Process incoming messages using registered handlers."""
        # Check for exact topic match
        if topic in self._message_handlers:
            handler = self._message_handlers[topic]
            
            # Support both sync and async handlers
            if asyncio.iscoroutinefunction(handler):
                result = await handler(message)
            else:
                result = handler(message)
            
            # Auto-publish response if handler returns data
            if result and isinstance(result, dict):
                response_topic = f"{topic}/response"
                await self.publish(response_topic, result)
            
            return True
        
        # Check for pattern matches (simple wildcard support)
        for pattern, handler in self._message_handlers.items():
            if self._matches_pattern(pattern, topic):
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(message)
                else:
                    result = handler(message)
                
                if result and isinstance(result, dict):
                    response_topic = f"{topic}/response"
                    await self.publish(response_topic, result)
                
                return True
        
        # Let parent handle standard agent messages
        return await super().process_message(topic, message)
    
    def _matches_pattern(self, pattern: str, topic: str) -> bool:
        """Simple pattern matching with * wildcard."""
        if "*" not in pattern:
            return pattern == topic
        
        parts = pattern.split("*")
        if len(parts) == 2:
            return topic.startswith(parts[0]) and topic.endswith(parts[1])
        return False
    
    def _setup_subscriptions(self):
        """Subscribe to all registered topics."""
        for topic in self._message_handlers:
            self.subscribe(topic)
    
    def run(self, duration: Optional[int] = None):
        """
        Run the agent (blocking).
        
        Args:
            duration: Optional duration in seconds (runs forever if None)
        """
        self._started = True
        self.start()
        
        try:
            if duration:
                import time
                time.sleep(duration)
            else:
                # Run forever
                import signal
                
                def signal_handler(sig, frame):
                    print(f"\n{self.agent_id} shutting down...")
                    self.stop()
                    exit(0)
                
                signal.signal(signal.SIGINT, signal_handler)
                signal.pause()
        except KeyboardInterrupt:
            print(f"\n{self.agent_id} shutting down...")
        finally:
            self.stop()
    
    async def run_async(self, duration: Optional[int] = None):
        """
        Run the agent asynchronously.
        
        Args:
            duration: Optional duration in seconds (runs forever if None)
        """
        self._started = True
        await self.start_async()
        
        try:
            if duration:
                await asyncio.sleep(duration)
            else:
                # Run forever
                await asyncio.Event().wait()
        finally:
            await self.stop_async()


def create_agent(agent_id: str = None, **kwargs) -> SimpleAgent:
    """
    Factory function to create a simple agent.
    
    Example:
        ```python
        from artcafe import create_agent
        
        agent = create_agent("my-agent")
        agent.run()
        ```
    """
    return SimpleAgent(agent_id=agent_id, **kwargs)