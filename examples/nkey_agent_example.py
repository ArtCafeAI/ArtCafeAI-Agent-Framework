#!/usr/bin/env python3
"""
Example of using NATSAgent with NKey authentication

This example shows how to create an agent that connects directly to NATS
using NKey authentication for better performance.
"""

import asyncio
import logging
from framework.core.nats_agent import NATSAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Create agent with NKey authentication
    agent = NATSAgent(
        client_id="example-client",
        tenant_id="your-tenant-id",
        nkey_seed="SUABTHCUEEB7DW66XQTPYIJT4OXFHX72FYAC26I6F4MWCKMTFSFP7MRY5U",
        name="Example NATS Agent"
    )
    
    # Connect to NATS
    await agent.connect()
    logger.info("✅ Connected to NATS")
    
    # Define message handler
    async def handle_task(subject, data):
        logger.info(f"📨 Received task on {subject}: {data}")
        
        # Process the task
        result = {
            "task_id": data.get("id", "unknown"),
            "status": "completed",
            "result": "Task processed successfully"
        }
        
        # Publish result
        await agent.publish("tasks.complete", result)
        logger.info(f"✅ Published result for task {data.get('id')}")
    
    # Subscribe to tasks
    await agent.subscribe("tasks.new", handle_task)
    logger.info("👂 Listening for tasks on 'tasks.new'")
    
    # Use decorator pattern for alerts
    @agent.on_message("alerts.*")
    async def handle_alert(subject, data):
        logger.warning(f"🚨 Alert on {subject}: {data}")
    
    # Publish a test message
    await agent.publish("status.online", {
        "client_id": agent.client_id,
        "message": "Agent is online and ready"
    })
    
    # Example of request/response
    try:
        response = await agent.request("echo.service", {"message": "Hello NATS!"}, timeout=5.0)
        logger.info(f"🔄 Echo response: {response}")
    except Exception as e:
        logger.info(f"ℹ️ No echo service available (expected): {e}")
    
    # Keep running
    logger.info("🤖 Agent running. Press Ctrl+C to stop...")
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())