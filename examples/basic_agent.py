#!/usr/bin/env python3
"""
Basic Agent Example

The simplest way to create an ArtCafe agent.
"""

import asyncio
import os
from framework.core.simple_agent import SimpleAgent


async def main():
    # Get credentials from environment
    agent_id = os.environ.get("ARTCAFE_AGENT_ID", "basic-agent-001")
    organization_id = os.environ.get("ARTCAFE_ORGANIZATION_ID", "demo-org")
    private_key_path = os.environ.get("ARTCAFE_PRIVATE_KEY_PATH", "~/.ssh/artcafe_agent_key")
    
    # Create agent
    agent = SimpleAgent(
        agent_id=agent_id,
        private_key_path=os.path.expanduser(private_key_path),
        organization_id=organization_id
    )
    
    # Add message handler
    @agent.on_message("general")
    async def handle_general(subject, data):
        print(f"Received on {subject}: {data}")
        
        # Respond to questions
        if "?" in data.get("content", ""):
            await agent.publish("general", {
                "agent_id": agent.agent_id,
                "content": "That's an interesting question!",
                "in_reply_to": data.get("agent_id")
            })
    
    print(f"Starting {agent_id}...")
    print("The agent will receive all messages on the 'general' channel")
    print("Press Ctrl+C to stop\n")
    
    # Run the agent
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())