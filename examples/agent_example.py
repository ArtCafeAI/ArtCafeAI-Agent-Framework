#!/usr/bin/env python3
"""
Agent Example - Shows how to create and run an agent.
"""

import asyncio
import logging
from framework import Agent

# Setup logging
logging.basicConfig(level=logging.INFO)

async def main():
    # Create an agent
    agent = Agent(
        agent_id="example-agent-001",
        private_key_path="path/to/private_key.pem",  # Replace with your key
        organization_id="your-org-id",  # Replace with your org ID
        websocket_url="wss://ws.artcafe.ai"
    )
    
    # Register message handlers
    @agent.on_message("tasks.new")
    async def handle_new_task(subject, data):
        print(f"Received new task on {subject}: {data}")
        
        # Process the task
        result = {"status": "completed", "result": "Task processed successfully"}
        
        # Publish the result
        await agent.publish("tasks.completed", result)
    
    @agent.on_message("system.alerts")
    async def handle_alert(subject, data):
        print(f"Alert received: {data}")
    
    # Run the agent (includes automatic heartbeat)
    print("Starting agent...")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())