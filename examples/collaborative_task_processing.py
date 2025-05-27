"""
Collaborative task processing with peer agents.

Instead of producer/consumer pattern, this example shows:
- All agents are peers that monitor a shared task channel
- Any agent can create tasks
- All agents see all tasks and decide whether to process them
- Agents coordinate through messages to avoid duplicate work
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Set
import random
import os

from framework.core.simple_agent import SimpleAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CollaborativeAgent(SimpleAgent):
    """
    A peer agent that collaborates on task processing.
    
    Each agent:
    - Monitors the shared task channel
    - Can create new tasks
    - Sees all tasks and claims ones it can handle
    - Coordinates with peers to avoid conflicts
    """
    
    def __init__(self, agent_id: str, capabilities: list[str], **kwargs):
        super().__init__(agent_id=agent_id, **kwargs)
        self.capabilities = set(capabilities)
        self.current_task_id = None
        self.processing_tasks: Set[str] = set()  # Track what's being processed globally
        self.completed_tasks: Set[str] = set()
        self.task_creation_probability = 0.2  # 20% chance to create a task
    
    async def on_start(self):
        """Initialize agent and subscribe to channels."""
        await super().on_start()
        
        # All agents subscribe to the same channels
        await self.subscribe("tasks.available")    # New tasks appear here
        await self.subscribe("tasks.claims")       # Agents claim tasks here
        await self.subscribe("tasks.status")       # Task status updates
        await self.subscribe("tasks.completed")    # Completed tasks
        
        # Start task creation cycle
        self.create_task(self._task_creation_cycle())
        
        # Announce capabilities
        await self.publish("agents.capabilities", {
            "agent_id": self.id,
            "capabilities": list(self.capabilities),
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"{self.id} ready with capabilities: {self.capabilities}")
    
    @SimplifiedAgent.on_message("tasks.available")
    async def handle_new_task(self, subject: str, task: Dict[str, Any]):
        """
        All agents receive notification of new tasks.
        Each decides independently whether to claim it.
        """
        task_id = task.get("id")
        task_type = task.get("type")
        created_by = task.get("created_by")
        
        # Don't process if:
        # 1. Already being processed by someone
        # 2. Already completed
        # 3. Currently busy with another task
        # 4. Don't have required capability
        
        if (task_id in self.processing_tasks or 
            task_id in self.completed_tasks or
            self.current_task_id is not None or
            task_type not in self.capabilities):
            return
        
        logger.info(f"{self.id} evaluating task {task_id} (type: {task_type})")
        
        # Add some randomness to avoid all agents claiming at once
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Try to claim the task
        await self.publish("tasks.claims", {
            "task_id": task_id,
            "agent_id": self.id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    @SimplifiedAgent.on_message("tasks.claims")
    async def handle_task_claim(self, subject: str, claim: Dict[str, Any]):
        """
        Handle task claims from all agents (including self).
        First valid claim wins.
        """
        task_id = claim.get("task_id")
        claiming_agent = claim.get("agent_id")
        
        # If task already being processed, ignore
        if task_id in self.processing_tasks:
            return
        
        # Mark task as being processed
        self.processing_tasks.add(task_id)
        
        # If we claimed it, start processing
        if claiming_agent == self.id:
            self.current_task_id = task_id
            logger.info(f"{self.id} claimed task {task_id}")
            
            # Notify others we're working on it
            await self.publish("tasks.status", {
                "task_id": task_id,
                "agent_id": self.id,
                "status": "in_progress",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Process the task
            self.create_task(self._process_task(task_id))
        else:
            logger.info(f"{self.id} saw {claiming_agent} claim task {task_id}")
    
    @SimplifiedAgent.on_message("tasks.completed")
    async def handle_task_completion(self, subject: str, completion: Dict[str, Any]):
        """Track completed tasks to avoid reprocessing."""
        task_id = completion.get("task_id")
        self.completed_tasks.add(task_id)
        self.processing_tasks.discard(task_id)
        
        completed_by = completion.get("agent_id")
        if completed_by != self.id:
            logger.info(f"{self.id} saw {completed_by} complete task {task_id}")
    
    async def _process_task(self, task_id: str):
        """Simulate task processing."""
        try:
            # Simulate work
            processing_time = random.uniform(2, 5)
            logger.info(f"{self.id} processing task {task_id} (ETA: {processing_time:.1f}s)")
            await asyncio.sleep(processing_time)
            
            # Complete the task
            result = {
                "task_id": task_id,
                "agent_id": self.id,
                "status": "completed",
                "result": f"Processed by {self.id}",
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.publish("tasks.completed", result)
            logger.info(f"{self.id} completed task {task_id}")
            
        except Exception as e:
            logger.error(f"{self.id} failed task {task_id}: {e}")
            await self.publish("tasks.status", {
                "task_id": task_id,
                "agent_id": self.id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        finally:
            self.current_task_id = None
    
    async def _task_creation_cycle(self):
        """Periodically create new tasks."""
        await asyncio.sleep(5)  # Initial delay
        
        task_types = list(self.capabilities)  # Create tasks we can handle
        
        while self._running:
            # Randomly decide to create a task
            if random.random() < self.task_creation_probability:
                task_type = random.choice(task_types)
                task = {
                    "id": str(uuid.uuid4()),
                    "type": task_type,
                    "created_by": self.id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "description": f"{task_type} task from {self.id}",
                        "priority": random.choice(["low", "medium", "high"])
                    }
                }
                
                await self.publish("tasks.available", task)
                logger.info(f"{self.id} created new {task_type} task")
            
            await asyncio.sleep(random.uniform(5, 15))


async def run_collaborative_demo():
    """Run the collaborative task processing demo."""
    # Configuration
    organization_id = os.environ.get("ARTCAFE_ORGANIZATION_ID", "demo-org")
    private_key_path = os.environ.get("ARTCAFE_PRIVATE_KEY_PATH", "~/.ssh/artcafe_agent_key")
    
    # Create agents with different capabilities
    agent_configs = [
        ("agent-alpha", ["data_processing", "analysis", "reporting"]),
        ("agent-beta", ["data_processing", "transformation", "validation"]),
        ("agent-gamma", ["analysis", "visualization", "reporting"]),
        ("agent-delta", ["transformation", "validation", "export"]),
        ("agent-epsilon", ["reporting", "export", "notification"])
    ]
    
    agents = []
    for agent_id, capabilities in agent_configs:
        agent = CollaborativeAgent(
            agent_id=agent_id,
            capabilities=capabilities,
            organization_id=organization_id,
            private_key_path=private_key_path
        )
        agents.append(agent)
    
    # Run all agents
    tasks = []
    for agent in agents:
        tasks.append(asyncio.create_task(agent.run_forever()))
    
    logger.info(f"Started {len(agents)} collaborative agents")
    logger.info("All agents are peers that:")
    logger.info("- See all available tasks")
    logger.info("- Claim tasks they can handle")
    logger.info("- Create new tasks for the group")
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down collaborative agents...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    print("""
Collaborative Task Processing Demo
=================================
This demonstrates peer-based task processing where:
- All agents are equal peers (no dedicated producer/consumer)
- Every agent sees all tasks on the channel
- Agents claim tasks based on their capabilities
- Any agent can create new tasks
- Agents coordinate to avoid duplicate work

Press Ctrl+C to stop.
""")
    
    asyncio.run(run_collaborative_demo())