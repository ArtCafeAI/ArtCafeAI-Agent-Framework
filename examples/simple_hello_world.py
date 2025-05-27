#!/usr/bin/env python3
"""
Simple Hello World Example

Demonstrates the simplest way to create an agent with the ArtCafe framework.
This uses WebSocket connection with challenge-response authentication.
"""

import asyncio
import os
from framework.core.simple_agent import SimpleAgent


async def main():
    # Configuration from environment
    organization_id = os.environ.get("ARTCAFE_ORGANIZATION_ID", "demo-org")
    private_key_path = os.environ.get("ARTCAFE_PRIVATE_KEY_PATH", "~/.ssh/artcafe_agent_key")
    
    # Expand path
    private_key_path = os.path.expanduser(private_key_path)
    
    # Create a simple agent
    agent = SimpleAgent(
        agent_id="hello-agent",
        private_key_path=private_key_path,
        organization_id=organization_id,
        capabilities=["greeting", "calculation"],
        metadata={"version": "1.0", "type": "demo"}
    )
    
    # Register a message handler using decorator
    @agent.on_message("greet")
    async def handle_greeting(subject, data):
        name = data.get("name", "World")
        response = {
            "greeting": f"Hello, {name}!",
            "agent": agent.agent_id
        }
        # Publish response
        await agent.publish("greet.response", response)
    
    # Register another handler
    @agent.on_message("calculate")
    async def handle_calculation(subject, data):
        operation = data.get("operation", "add")
        a = data.get("a", 0)
        b = data.get("b", 0)
        
        if operation == "add":
            result = a + b
        elif operation == "multiply":
            result = a * b
        else:
            result = None
            
        response = {"result": result, "operation": operation}
        await agent.publish("calculate.response", response)
    
    print(f"Starting {agent.agent_id}...")
    print("Press Ctrl+C to stop")
    
    # Run the agent
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())