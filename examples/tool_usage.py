#!/usr/bin/env python3

"""
Tool Usage Example

This example demonstrates how to create and use tools with the @tool decorator.
"""

import asyncio
import logging
import os
import sys
import json
import datetime

# Add parent directory to path to allow importing the framework
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from artcafe.framework.core.enhanced_agent import EnhancedAgent
from artcafe.framework.core.config import AgentConfig
from artcafe.framework.event_loop import EventLoop
from artcafe.framework.event_loop.callback import ConsoleCallbackHandler
from artcafe.framework.llm import get_llm_provider
from artcafe.framework.tools import tool, ToolRegistry, ToolHandler

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ToolUsageExample")

# Create tools using the @tool decorator
@tool
def get_current_time(timezone: str = "UTC") -> str:
    """
    Get the current time in the specified timezone.
    
    Args:
        timezone: Timezone to get the time for (default: UTC)
        
    Returns:
        Current time as a string
    """
    # This is a simplified example - a real implementation would handle timezones properly
    return f"Current time ({timezone}): {datetime.datetime.now().isoformat()}"

@tool
def calculate(operation: str, a: float, b: float) -> dict:
    """
    Perform a basic calculation.
    
    Args:
        operation: Operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number
        
    Returns:
        Result of the calculation
    """
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            return {"status": "error", "error": "Division by zero"}
        result = a / b
    else:
        return {"status": "error", "error": f"Unknown operation: {operation}"}
    
    return {
        "status": "success",
        "result": result,
        "operation": operation,
        "a": a,
        "b": b
    }

@tool
def search_database(query: str, limit: int = 5) -> list:
    """
    Simulate searching a database.
    
    Args:
        query: Search query
        limit: Maximum number of results to return
        
    Returns:
        List of search results
    """
    # This is a simulated database search
    sample_data = [
        {"id": 1, "title": "Introduction to AI", "author": "Jane Smith"},
        {"id": 2, "title": "Machine Learning Basics", "author": "John Doe"},
        {"id": 3, "title": "Advanced AI Techniques", "author": "Bob Johnson"},
        {"id": 4, "title": "Neural Networks", "author": "Alice Brown"},
        {"id": 5, "title": "Reinforcement Learning", "author": "Charlie Davis"},
        {"id": 6, "title": "Natural Language Processing", "author": "Diana Evans"},
        {"id": 7, "title": "Computer Vision", "author": "Frank Wilson"},
    ]
    
    # Filter results based on query (case-insensitive)
    results = [
        item for item in sample_data 
        if query.lower() in item["title"].lower() or query.lower() in item["author"].lower()
    ]
    
    # Limit results
    return results[:limit]

class ToolAgent(EnhancedAgent):
    """An agent that demonstrates tool usage."""
    
    def __init__(self, agent_id=None, config=None):
        """Initialize the tool agent."""
        super().__init__(agent_id=agent_id, agent_type="tool_agent", config=config)
        
        # Add capabilities
        self.add_capability("tools")
        
        # Initialize LLM provider
        self.llm = get_llm_provider(self.config.get("llm", {}))
        
        # Initialize tool registry and handler
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(get_current_time)
        self.tool_registry.register_tool(calculate)
        self.tool_registry.register_tool(search_database)
        
        self.tool_handler = ToolHandler(self.tool_registry)
        
        # Initialize event loop
        self.event_loop = EventLoop(
            llm_provider=self.llm,
            tool_handler=self.tool_handler,
            callback_handler=ConsoleCallbackHandler(verbose=True)
        )
        
        # Initialize conversation history
        self.conversations = {}
    
    async def process_message(self, topic, message):
        """Process incoming messages."""
        # Call parent method for basic processing
        if await super().process_message(topic, message):
            # Handle tool requests
            if topic.startswith("tools/request"):
                await self._handle_tool_request(topic, message)
                return True
        return False
    
    async def _handle_tool_request(self, topic, message):
        """Handle tool requests using the event loop."""
        try:
            # Extract conversation ID from topic
            parts = topic.split('/')
            if len(parts) >= 3:
                conversation_id = parts[2]
            else:
                conversation_id = "default"
            
            # Get or initialize conversation history
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            # Get user message
            user_message = message.get("request", "")
            if not user_message:
                logger.warning("Received empty tool request")
                return
            
            logger.info(f"Processing tool request in conversation {conversation_id}: {user_message}")
            
            # Process message through event loop
            system_prompt = """
            You are a helpful AI assistant with access to tools. When the user asks you to do something, 
            use the most appropriate tool to help them. You have the following tools available:
            
            - get_current_time: Get the current time in a specified timezone
            - calculate: Perform basic math operations
            - search_database: Search a database for information
            
            Use these tools to respond to user requests effectively.
            """
            
            response, updated_history = await self.event_loop.process_message(
                user_message=user_message,
                conversation_history=self.conversations[conversation_id],
                system_prompt=system_prompt
            )
            
            # Update conversation history
            self.conversations[conversation_id] = updated_history
            
            # Publish response
            await self.publish(f"tools/response/{conversation_id}", {
                "response": response,
                "agent_id": self.agent_id
            })
            
            logger.info(f"Sent tool response in conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error handling tool request: {str(e)}")
            # Publish error response
            await self.publish(f"tools/error/{conversation_id}", {
                "error": str(e),
                "agent_id": self.agent_id
            })

async def main():
    """Run the tool agent."""
    # Create configuration
    config = AgentConfig()
    
    # Set LLM configuration (using Anthropic by default)
    config.set("llm.provider", "anthropic")
    config.set("llm.model", "claude-3-opus-20240229")
    
    # Create and start the agent
    agent = ToolAgent(config=config)
    success = await agent.start()
    
    if not success:
        logger.error("Failed to start agent")
        return
    
    logger.info(f"Agent started with ID: {agent.agent_id}")
    logger.info(f"Registered tools: {[spec['name'] for spec in agent.tool_registry.get_all_tool_specs().values()]}")
    
    try:
        # Subscribe to tool requests
        await agent.subscribe("tools/request/#")
        
        # Simulate a tool request
        sample_requests = [
            "What time is it right now?",
            "Calculate 15 divided by 3",
            "Find information about Machine Learning in the database",
            "Can you search for articles by Jane Smith?",
        ]
        
        for i, request in enumerate(sample_requests):
            # Send a sample request
            await agent.publish(f"tools/request/{i+1}", {
                "request": request,
                "user_id": "sample_user"
            })
            
            # Wait for the agent to process the request
            await asyncio.sleep(5)
        
        # Keep the agent running for a while
        await asyncio.sleep(10)
        
    except KeyboardInterrupt:
        logger.info("Stopping agent...")
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())