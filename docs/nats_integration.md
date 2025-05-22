# NATS Integration Guide

This guide describes how to use NATS as the messaging backbone for the Agent Framework, implementing the scalable pub/sub architecture for LLM agents.

## Overview

The NATS integration provides:

- **Hierarchical Topic Structure**: Following the pattern `agents.{environment}.{message_type}.{domain}.{specificity}`
- **MCP over NATS**: Route Model Context Protocol calls through NATS topics
- **A2A Protocol**: Agent-to-Agent negotiations and coordination
- **Message Streaming**: Stream responses in chunks for real-time processing
- **Batch Processing**: Process multiple messages efficiently

## Installation

```bash
pip install nats-py
```

## Configuration

Create a configuration file (e.g., `config/nats_config.yaml`):

```yaml
messaging:
  provider: nats
  
nats:
  servers:
    - nats://localhost:4222
  environment: prod
  batch_size: 10
  batch_timeout: 1.0
```

## Basic Usage

### Creating a NATS-Enabled Agent

```python
from framework.core import NATSAgent, AgentConfig

class MyAgent(NATSAgent):
    def __init__(self):
        config = AgentConfig({
            "nats.servers": ["nats://localhost:4222"],
            "nats.environment": "prod"
        })
        super().__init__(agent_id="my-agent-001", agent_type="worker", config=config)
        
        # Add capabilities
        self.add_capability("analysis")
        self.add_capability("processing")
        
    def _setup_subscriptions(self):
        """Set up topic subscriptions."""
        super()._setup_subscriptions()
        
        # Subscribe to specific task types
        self.subscribe("agents/task/analysis/*")
        
    def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """Process incoming messages."""
        # Handle the message based on topic
        if "task/analysis" in topic:
            result = self.perform_analysis(message)
            self.publish_result(message.get("id"), result)
        return True
```

### Starting the Agent

```python
agent = MyAgent()
if agent.start():
    print(f"Agent {agent.agent_id} started successfully")
    # Agent is now running and processing messages
```

## Message Structure

Messages follow the AgentMessage structure from the guide:

```python
{
    "id": "unique-message-id",
    "timestamp": 1234567890.123,
    "version": "1.0",
    "type": "task",  # task, result, event, query
    "source": {
        "id": "agent-id",
        "type": "agent"
    },
    "target": "optional-target-agent",
    "replyTo": "optional-reply-topic",
    "correlationId": "id-of-related-message",
    "context": {
        "conversationId": "conversation-id",
        "metadata": {}
    },
    "payload": {
        "content": {
            # Actual message content
        }
    },
    "routing": {
        "priority": 5,
        "capabilities": ["required", "capabilities"],
        "timeout": 30000
    }
}
```

## MCP over NATS

### Registering an MCP Server

```python
from framework.mcp import MCPClient

# Create MCP client
mcp_client = MCPClient(server_command="mcp-server", server_args=["--mode", "tools"])
await mcp_client.connect()

# Register with agent
agent.register_mcp_server("my-mcp-server", mcp_client)
```

### Calling Remote MCP Tools

```python
# Call a tool on a remote MCP server through NATS
result = await agent.call_mcp_tool(
    server_id="remote-mcp-server",
    tool_name="web_search",
    arguments={"query": "latest AI news"},
    timeout=30.0
)
```

## A2A Protocol

### Registering Negotiation Handlers

```python
def handle_task_negotiation(negotiation: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming task negotiations."""
    proposal = negotiation.get("proposal", {})
    
    # Evaluate the proposal
    if can_handle_task(proposal):
        return {
            "accept": True,
            "terms": {
                "estimated_time": "5 minutes",
                "priority": "high"
            }
        }
    else:
        return {
            "accept": False,
            "reason": "Insufficient resources"
        }

# Register the handler
agent.register_a2a_handler("task_assignment", handle_task_negotiation)
```

### Initiating Negotiations

```python
# Negotiate with other agents
result = await agent.negotiate_with_agents(
    target_agents=["agent-002", "agent-003"],
    negotiation_type="task_assignment",
    proposal={
        "task": "analyze_data",
        "data_size": "10GB",
        "deadline": "2 hours"
    },
    constraints={
        "max_cost": 100,
        "required_accuracy": 0.95
    },
    timeout=10.0
)

# Check results
if result["state"] == "finalized":
    print("Negotiation successful!")
    for agent_id, response in result["responses"].items():
        print(f"{agent_id}: {response}")
```

## Streaming Responses

```python
async def generate_analysis():
    """Generate analysis results in chunks."""
    for i in range(10):
        yield f"Analysis part {i+1}: Processing...\n"
        await asyncio.sleep(0.5)

# Stream the response
await agent.stream_response(
    task_id="task-123",
    response_generator=generate_analysis(),
    chunk_size=1024
)
```

## Batch Processing

```python
# Enable batch processing
agent.enable_batch_processing(batch_size=10, batch_timeout=2.0)

# Messages are automatically batched and processed together
# for improved efficiency
```

## Topic Hierarchy

The framework uses a hierarchical topic structure:

### Core Topics

- `agents.{env}.control.{agent_id}` - Control messages for specific agents
- `agents.{env}.status.{agent_id}` - Status updates from agents
- `agents.{env}.task.{capability}.{specificity}` - Task assignments
- `agents.{env}.result.{agent_id}.{task_type}` - Task results
- `agents.{env}.event.{event_type}.{detail}` - System events
- `agents.{env}.discovery.requests` - Agent discovery requests
- `agents.{env}.discovery.responses` - Agent discovery responses

### MCP Topics

- `agents.{env}.mcp.{server_id}.requests` - MCP tool requests
- `agents.{env}.mcp.{agent_id}.responses.{request_id}` - MCP responses

### A2A Topics

- `agents.{env}.a2a.negotiate.{agent_id}` - Negotiation messages

## Performance Optimization

### Message Caching

The NATS provider includes built-in caching for frequently accessed data:

```python
# Messages with the same content hash are cached automatically
# to reduce redundant processing
```

### Connection Pooling

```python
# Configure multiple NATS servers for redundancy
config = AgentConfig({
    "nats.servers": [
        "nats://nats1.example.com:4222",
        "nats://nats2.example.com:4222",
        "nats://nats3.example.com:4222"
    ]
})
```

### Monitoring

```python
# Access agent metrics
metrics = agent.get_metrics()
print(f"Messages processed: {metrics['messages_processed']}")
print(f"Average latency: {metrics.get('avg_latency_ms', 0)}ms")
```

## Deployment

### Docker Compose Example

```yaml
version: '3.8'

services:
  nats:
    image: nats:latest
    ports:
      - "4222:4222"
      - "8222:8222"
    command: ["--jetstream", "--store_dir", "/data"]
    volumes:
      - nats-data:/data
      
  agent:
    build: .
    environment:
      - NATS_URL=nats://nats:4222
    depends_on:
      - nats
    deploy:
      replicas: 3

volumes:
  nats-data:
```

### Production Considerations

1. **Use NATS Clustering** for high availability
2. **Enable JetStream** for message persistence
3. **Configure TLS** for secure communication
4. **Set appropriate timeouts** based on your workload
5. **Monitor queue depths** to prevent backlogs

## Troubleshooting

### Connection Issues

```python
# Enable debug logging
import logging
logging.getLogger("AgentFramework.Messaging.NATSProvider").setLevel(logging.DEBUG)
```

### Message Not Received

1. Check topic subscriptions match the publishing pattern
2. Verify permissions in the token
3. Ensure NATS server is running and accessible

### Performance Issues

1. Increase batch size for high-volume scenarios
2. Use message streaming for large payloads
3. Consider horizontal scaling with multiple agent instances