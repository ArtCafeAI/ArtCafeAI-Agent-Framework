#!/usr/bin/env python3

"""
Example of using NATS-enabled agents with MCP over NATS and A2A protocol.

This example demonstrates:
1. Creating NATS-enabled agents
2. Using MCP tools over NATS
3. A2A negotiations between agents
4. Message streaming
5. Batch processing
"""

import asyncio
import logging
from typing import Dict, Any

from framework.core import NATSAgent, AgentConfig
from framework.mcp import MCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AnalysisAgent(NATSAgent):
    """Agent that performs analysis tasks."""
    
    def __init__(self):
        config = AgentConfig({
            "nats.servers": ["nats://localhost:4222"],
            "nats.environment": "prod"
        })
        super().__init__(agent_id="analysis-001", agent_type="analysis", config=config)
        
        # Add capabilities
        self.add_capability("analysis")
        self.add_capability("sentiment")
        
    def _setup_subscriptions(self):
        """Set up topic subscriptions."""
        super()._setup_subscriptions()
        
        # Subscribe to analysis tasks
        self.subscribe("agents/task/analysis/*")
        
    def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """Process analysis tasks."""
        super().process_message(topic, message)
        
        if "task/analysis" in topic:
            task = message.get("payload", {}).get("content", {})
            instruction = task.get("instruction", "")
            
            # Perform analysis (mock result)
            result = {
                "analysis": f"Analysis of: {instruction}",
                "sentiment": "positive",
                "confidence": 0.95
            }
            
            # Publish result
            result_topic = f"agents/result/analysis/{self.agent_id}"
            self.publish(result_topic, {
                "correlation_id": message.get("id"),
                "result": result
            })
            
        return True

class CodeGenerationAgent(NATSAgent):
    """Agent that generates code."""
    
    def __init__(self):
        config = AgentConfig({
            "nats.servers": ["nats://localhost:4222"],
            "nats.environment": "prod",
            "nats.batch_size": 5,
            "nats.batch_timeout": 2.0
        })
        super().__init__(agent_id="codegen-001", agent_type="codegen", config=config)
        
        # Add capabilities
        self.add_capability("code")
        self.add_capability("generation")
        
        # Enable batch processing
        self.enable_batch_processing(batch_size=5, batch_timeout=2.0)
        
        # Register A2A negotiation handler
        self.register_a2a_handler("code_review", self._handle_code_review_negotiation)
        
    def _setup_subscriptions(self):
        """Set up topic subscriptions."""
        super()._setup_subscriptions()
        
        # Subscribe to code generation tasks
        self.subscribe("agents/task/code/*")
        
    def _handle_code_review_negotiation(self, negotiation: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code review negotiations from other agents."""
        proposal = negotiation.get("proposal", {})
        code_complexity = proposal.get("complexity", "medium")
        
        # Accept simple and medium complexity reviews
        if code_complexity in ["simple", "medium"]:
            return {
                "accept": True,
                "terms": {
                    "review_time": "2 hours" if code_complexity == "medium" else "1 hour",
                    "review_depth": "comprehensive"
                }
            }
        else:
            return {
                "accept": False,
                "reason": "Only accepting simple and medium complexity reviews"
            }
            
    async def generate_code_stream(self, instruction: str):
        """Generate code in a streaming fashion."""
        # Mock streaming code generation
        code_parts = [
            "def process_data(data):\n",
            "    # Process the input data\n",
            "    result = []\n",
            "    for item in data:\n",
            "        processed = transform(item)\n",
            "        result.append(processed)\n",
            "    return result\n"
        ]
        
        for part in code_parts:
            yield part
            await asyncio.sleep(0.5)  # Simulate generation delay

class OrchestratorAgent(NATSAgent):
    """Agent that orchestrates tasks between other agents."""
    
    def __init__(self):
        config = AgentConfig({
            "nats.servers": ["nats://localhost:4222"],
            "nats.environment": "prod"
        })
        super().__init__(agent_id="orchestrator-001", agent_type="orchestrator", config=config)
        
        self.pending_tasks = {}
        
    async def submit_analysis_task(self, instruction: str) -> str:
        """Submit an analysis task."""
        task_id = await self._submit_task("analysis", instruction, ["analysis"])
        return task_id
        
    async def submit_code_task(self, instruction: str) -> str:
        """Submit a code generation task."""
        task_id = await self._submit_task("code", instruction, ["code", "generation"])
        return task_id
        
    async def _submit_task(self, task_type: str, instruction: str, capabilities: List[str]) -> str:
        """Submit a task to agents with specific capabilities."""
        import uuid
        
        task_id = str(uuid.uuid4())
        
        message = {
            "id": task_id,
            "instruction": instruction,
            "expected_output": "text",
            "capabilities_required": capabilities
        }
        
        # Publish task
        for capability in capabilities:
            topic = f"agents/task/{capability}/general"
            self.publish(topic, message)
            
        # Track pending task
        self.pending_tasks[task_id] = {
            "type": task_type,
            "instruction": instruction,
            "submitted_at": asyncio.get_event_loop().time()
        }
        
        return task_id
        
    async def negotiate_code_review(self, target_agents: List[str], code_complexity: str):
        """Negotiate a code review with other agents."""
        proposal = {
            "task": "code_review",
            "complexity": code_complexity,
            "lines_of_code": 500 if code_complexity == "medium" else 100,
            "language": "python"
        }
        
        result = await self.negotiate_with_agents(
            target_agents,
            "code_review",
            proposal,
            timeout=10.0
        )
        
        return result

async def main():
    """Run the example."""
    # Create agents
    analysis_agent = AnalysisAgent()
    codegen_agent = CodeGenerationAgent()
    orchestrator = OrchestratorAgent()
    
    # Start agents
    agents = [analysis_agent, codegen_agent, orchestrator]
    for agent in agents:
        if not agent.start():
            print(f"Failed to start agent {agent.agent_id}")
            return
            
    print("All agents started successfully")
    
    # Give agents time to connect
    await asyncio.sleep(2)
    
    try:
        # Example 1: Submit analysis task
        print("\n=== Example 1: Analysis Task ===")
        task_id = await orchestrator.submit_analysis_task(
            "Analyze the sentiment of customer feedback data"
        )
        print(f"Submitted analysis task: {task_id}")
        
        # Example 2: Submit code generation task
        print("\n=== Example 2: Code Generation Task ===")
        code_task_id = await orchestrator.submit_code_task(
            "Generate a Python function to process JSON data"
        )
        print(f"Submitted code generation task: {code_task_id}")
        
        # Example 3: A2A negotiation
        print("\n=== Example 3: A2A Negotiation ===")
        negotiation_result = await orchestrator.negotiate_code_review(
            ["codegen-001"],
            "medium"
        )
        print(f"Negotiation result: {negotiation_result}")
        
        # Example 4: Stream code generation
        print("\n=== Example 4: Streaming Response ===")
        print("Streaming code generation:")
        async for chunk in codegen_agent.generate_code_stream("Generate data processor"):
            print(chunk, end="")
            
        # Wait for tasks to complete
        await asyncio.sleep(5)
        
    finally:
        # Stop agents
        print("\n\nStopping agents...")
        for agent in agents:
            agent.stop()

if __name__ == "__main__":
    asyncio.run(main())