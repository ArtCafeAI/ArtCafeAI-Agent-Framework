"""
Peer agents example - demonstrating true peer-to-peer messaging.

In this example, all agents are peers that:
- Subscribe to the same channels/topics
- Receive all messages sent to those channels
- Decide independently how to process messages
- Can all contribute to the conversation
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any
import os

from framework.core.simple_agent import SimpleAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_peer_agents_demo():
    """Run the peer agents demonstration."""
    # Configuration
    organization_id = os.environ.get("ARTCAFE_ORGANIZATION_ID", "demo-org")
    private_key_path = os.environ.get("ARTCAFE_PRIVATE_KEY_PATH", "~/.ssh/artcafe_agent_key")
    
    # Expand path
    private_key_path = os.path.expanduser(private_key_path)
    
    # Create diverse team of peer agents
    agents = []
    
    # Analyst agent
    analyst = SimpleAgent(
        agent_id="peer-analyst-001",
        private_key_path=private_key_path,
        organization_id=organization_id,
        capabilities=["data-analysis", "metrics", "reporting"],
        metadata={"role": "analyst", "team": "data"}
    )
    
    @analyst.on_message("team.discussion")
    async def analyst_handler(subject: str, data: Dict[str, Any]):
        sender = data.get("agent_id")
        content = data.get("content", "")
        
        # Don't respond to own messages
        if sender == analyst.agent_id:
            return
        
        # Decide whether to respond based on content
        content_lower = content.lower()
        interests = ["data", "metrics", "analysis", "report", "trend"]
        
        if any(word in content_lower for word in interests) or random.random() < 0.2:
            await asyncio.sleep(random.uniform(1, 3))
            
            responses = [
                "Let me analyze that data point...",
                "The metrics suggest we should consider...",
                "Based on the trends I'm seeing...",
                "Here's what the numbers tell us..."
            ]
            
            await analyst.publish("team.discussion", {
                "agent_id": analyst.agent_id,
                "content": random.choice(responses),
                "in_reply_to": sender,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    agents.append(analyst)
    
    # Creative agent
    creative = SimpleAgent(
        agent_id="peer-creative-002",
        private_key_path=private_key_path,
        organization_id=organization_id,
        capabilities=["design", "innovation", "brainstorming"],
        metadata={"role": "creative", "team": "design"}
    )
    
    @creative.on_message("team.discussion")
    async def creative_handler(subject: str, data: Dict[str, Any]):
        sender = data.get("agent_id")
        content = data.get("content", "")
        
        if sender == creative.agent_id:
            return
        
        content_lower = content.lower()
        interests = ["design", "idea", "creative", "innovation", "concept"]
        
        if any(word in content_lower for word in interests) or random.random() < 0.2:
            await asyncio.sleep(random.uniform(1, 3))
            
            responses = [
                "What if we approached it differently?",
                "I have an idea that might work...",
                "Let's think outside the box here...",
                "From a design perspective..."
            ]
            
            await creative.publish("team.discussion", {
                "agent_id": creative.agent_id,
                "content": random.choice(responses),
                "in_reply_to": sender,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    agents.append(creative)
    
    # Engineer agent
    engineer = SimpleAgent(
        agent_id="peer-engineer-003",
        private_key_path=private_key_path,
        organization_id=organization_id,
        capabilities=["coding", "architecture", "debugging"],
        metadata={"role": "engineer", "team": "engineering"}
    )
    
    @engineer.on_message("team.discussion")
    async def engineer_handler(subject: str, data: Dict[str, Any]):
        sender = data.get("agent_id")
        content = data.get("content", "")
        
        if sender == engineer.agent_id:
            return
        
        content_lower = content.lower()
        interests = ["code", "system", "architecture", "bug", "technical"]
        
        if any(word in content_lower for word in interests) or random.random() < 0.2:
            await asyncio.sleep(random.uniform(1, 3))
            
            responses = [
                "I can build a solution for that.",
                "The technical approach would be...",
                "Let me check the system architecture...",
                "That's a classic engineering problem..."
            ]
            
            await engineer.publish("team.discussion", {
                "agent_id": engineer.agent_id,
                "content": random.choice(responses),
                "in_reply_to": sender,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    agents.append(engineer)
    
    # Manager agent - also initiates topics
    manager = SimpleAgent(
        agent_id="peer-manager-004",
        private_key_path=private_key_path,
        organization_id=organization_id,
        capabilities=["planning", "coordination", "leadership"],
        metadata={"role": "manager", "team": "leadership"}
    )
    
    @manager.on_message("team.discussion")
    async def manager_handler(subject: str, data: Dict[str, Any]):
        sender = data.get("agent_id")
        content = data.get("content", "")
        
        if sender == manager.agent_id:
            return
        
        content_lower = content.lower()
        interests = ["plan", "schedule", "resource", "team", "goal", "deadline"]
        
        if any(word in content_lower for word in interests) or random.random() < 0.2:
            await asyncio.sleep(random.uniform(1, 3))
            
            responses = [
                "Let's align this with our goals.",
                "We need to consider the timeline...",
                "I'll coordinate with the team on this.",
                "What resources do we need?"
            ]
            
            await manager.publish("team.discussion", {
                "agent_id": manager.agent_id,
                "content": random.choice(responses),
                "in_reply_to": sender,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    agents.append(manager)
    
    # Function to initiate topics periodically
    async def initiate_topics():
        topics = [
            "Has anyone reviewed the latest data trends?",
            "We need innovative ideas for the new feature.",
            "There's a technical challenge with the system architecture.",
            "Let's discuss our goals for next quarter.",
            "I found an interesting design pattern we could use.",
            "The metrics show some concerning trends we should address."
        ]
        
        await asyncio.sleep(5)  # Initial delay
        
        while True:
            topic = random.choice(topics)
            initiator = random.choice(agents)
            
            await initiator.publish("team.discussion", {
                "agent_id": initiator.agent_id,
                "content": topic,
                "type": "topic-start",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"{initiator.agent_id} initiated topic: {topic}")
            
            # Wait before next topic
            await asyncio.sleep(random.uniform(20, 40))
    
    # Run all agents concurrently
    tasks = []
    
    # Start all agents
    for agent in agents:
        task = asyncio.create_task(agent.run())
        tasks.append(task)
    
    # Start topic initiator
    topic_task = asyncio.create_task(initiate_topics())
    tasks.append(topic_task)
    
    logger.info(f"Started {len(agents)} peer agents")
    logger.info("All agents are equal peers receiving all messages")
    logger.info("Each agent decides independently how to respond")
    
    try:
        # Run until interrupted
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down peer agents...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    print("""
Peer Agents Demo
===============
This demonstrates true peer-to-peer agent communication where:
- All agents are equal peers (no producer/consumer hierarchy)  
- Every agent receives all messages on subscribed channels
- Each agent independently decides whether to respond
- Agents can all initiate new topics

Press Ctrl+C to stop.
""")
    
    asyncio.run(run_peer_agents_demo())