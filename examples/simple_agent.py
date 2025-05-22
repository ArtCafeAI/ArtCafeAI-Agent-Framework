#!/usr/bin/env python3

"""
Simple Agent Example

This example demonstrates how to create a basic agent that responds to messages
and uses the event loop for LLM interactions.
"""

import asyncio
import logging
import os
import sys

# Add parent directory to path to allow importing the framework
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from artcafe.framework.core.enhanced_agent import EnhancedAgent
from artcafe.framework.core.config import AgentConfig
from artcafe.framework.event_loop import EventLoop
from artcafe.framework.event_loop.callback import ConsoleCallbackHandler
from artcafe.framework.llm import get_llm_provider

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleAgent")

class SimpleAgent(EnhancedAgent):
    """A simple agent that responds to messages using the event loop."""
    
    def __init__(self, agent_id=None, config=None):
        """Initialize the simple agent."""
        super().__init__(agent_id=agent_id, agent_type="simple", config=config)
        
        # Add capabilities
        self.add_capability("chat")
        
        # Initialize LLM provider
        self.llm = get_llm_provider(self.config.get("llm", {}))
        
        # Initialize event loop
        self.event_loop = EventLoop(
            llm_provider=self.llm,
            callback_handler=ConsoleCallbackHandler(verbose=True)
        )
        
        # Initialize conversation history
        self.conversations = {}
    
    async def process_message(self, topic, message):
        """Process incoming messages."""
        # Call parent method for basic processing
        if await super().process_message(topic, message):
            # Handle chat messages
            if topic.startswith("chat/"):
                await self._handle_chat(topic, message)
                return True
        return False
    
    async def _handle_chat(self, topic, message):
        """Handle chat messages using the event loop."""
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
            user_message = message.get("message", "")
            if not user_message:
                logger.warning("Received empty message")
                return
            
            logger.info(f"Processing message in conversation {conversation_id}: {user_message}")
            
            # Process message through event loop
            response, updated_history = await self.event_loop.process_message(
                user_message=user_message,
                conversation_history=self.conversations[conversation_id],
                system_prompt="You are a helpful assistant. Be concise and clear in your responses."
            )
            
            # Update conversation history
            self.conversations[conversation_id] = updated_history
            
            # Publish response
            await self.publish(f"chat/response/{conversation_id}", {
                "message": response,
                "agent_id": self.agent_id
            })
            
            logger.info(f"Sent response in conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error handling chat message: {str(e)}")
            # Publish error response
            await self.publish(f"chat/error/{conversation_id}", {
                "error": str(e),
                "agent_id": self.agent_id
            })

async def main():
    """Run the simple agent."""
    # Create configuration
    config = AgentConfig()
    
    # Set LLM configuration (using Anthropic by default)
    config.set("llm.provider", "anthropic")
    config.set("llm.model", "claude-3-opus-20240229")
    
    # Create and start the agent
    agent = SimpleAgent(config=config)
    success = await agent.start()
    
    if not success:
        logger.error("Failed to start agent")
        return
    
    logger.info(f"Agent started with ID: {agent.agent_id}")
    
    try:
        # Subscribe to chat messages
        await agent.subscribe("chat/message/#")
        
        # Keep the agent running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping agent...")
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())