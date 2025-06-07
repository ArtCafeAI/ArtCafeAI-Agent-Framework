# Quick Start Guide

Get your first ArtCafe agent running in 5 minutes!

## Prerequisites

- Python 3.8+
- An ArtCafe.ai account with API access
- SSH key pair for agent authentication

## Installation

```bash
pip install artcafe-agent-framework
```

## Your First Agent

### 1. Create an Agent

```python
from artcafe.framework import Agent

# Create your agent
agent = Agent(
    agent_id="my-first-agent",
    organization_id="your-org-id",  # Find this in Dashboard > Settings
    private_key_path="~/.ssh/artcafe_agent_key"
)

# Handle incoming messages with decorators
@agent.on_message("hello")
async def handle_hello(subject, data):
    print(f"Received hello: {data}")
    # Send a response
    await agent.publish("hello.response", {"message": "Hello back!"})

# Run the agent (includes automatic heartbeat)
if __name__ == "__main__":
    import asyncio
    asyncio.run(agent.run())
```

### 2. Using Configuration Files

Create `config.yaml`:

```yaml
agent:
  name: "My First Agent"
  description: "Learning ArtCafe.ai"
  capabilities:
    - messaging
    - data_processing

platform:
  heartbeat_interval: 30
  auto_reconnect: true

logging:
  level: INFO
```

Use it in your agent:

```python
agent = SimplifiedAgent(
    agent_id="my-first-agent",
    tenant_id="your-tenant-id", 
    private_key_path="~/.ssh/artcafe_agent_key",
    config_path="config.yaml"
)
```

### 3. Task Queue Pattern

Create a task processor:

```python
from artcafe.framework import SimplifiedAgent

agent = SimplifiedAgent(
    agent_id="task-processor",
    tenant_id="your-tenant-id",
    private_key_path="~/.ssh/artcafe_agent_key"
)

@agent.on_message("tasks.new")
async def process_task(subject, task):
    print(f"Processing task: {task['id']}")
    
    # Do the work
    result = await do_work(task['data'])
    
    # Report completion
    await agent.publish("tasks.complete", {
        "task_id": task['id'],
        "result": result
    })

async def do_work(data):
    # Your task logic here
    return {"status": "success", "output": data}
```

## Common Patterns

### 1. Request/Response

```python
@agent.on_message("requests.*")
async def handle_request(subject, request):
    request_id = request.get('id')
    
    # Process request
    response = process_request(request)
    
    # Send response
    await agent.publish(f"responses.{request_id}", response)
```

### 2. Pub/Sub Broadcasting

```python
# Publisher
await agent.publish("events.user.login", {
    "user_id": "123",
    "timestamp": datetime.now().isoformat()
})

# Subscriber
@agent.on_message("events.user.*")
async def handle_user_event(subject, event):
    event_type = subject.split('.')[-1]
    print(f"User event {event_type}: {event}")
```

### 3. Worker Pool

```python
# Subscribe to work queue
@agent.on_message("work.queue")
async def handle_work(subject, work_item):
    # Check if we can handle this work
    if agent.current_load < agent.max_load:
        await agent.publish("work.claimed", {
            "work_id": work_item['id'],
            "worker": agent.id
        })
        
        # Process the work
        await process_work_item(work_item)
```

## Authentication

The framework handles authentication automatically, but here's what happens:

1. Agent requests a challenge from the platform
2. Signs the challenge with its SSH private key
3. Connects to WebSocket with signed challenge
4. Platform verifies signature and establishes connection

## Environment Variables

Configure your agent using environment variables:

```bash
export ARTCAFE_API_ENDPOINT=https://api.artcafe.ai
export ARTCAFE_WS_ENDPOINT=wss://ws.artcafe.ai
export ARTCAFE_ORGANIZATION_ID=your-org-id  # From Dashboard > Settings
export ARTCAFE_AGENT_ID=my-agent
export ARTCAFE_PRIVATE_KEY_PATH=~/.ssh/artcafe_agent_key
export LOG_LEVEL=INFO
```

## Next Steps

1. Check out the [examples](../examples/) directory
2. Read about [advanced patterns](./advanced_patterns.md)
3. Learn about [error handling](./error_handling.md)
4. Explore [monitoring and metrics](./monitoring.md)

## Troubleshooting

### Connection Issues

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check connection status
if agent.is_connected:
    print("Connected!")
else:
    print("Not connected")
```

### Message Not Received

1. Check your subscription pattern matches the topic
2. Verify tenant prefix is correct
3. Enable debug logging to see all messages

### Authentication Failed

1. Verify your SSH key is correct
2. Check the key has the right permissions (600)
3. Ensure agent_id matches the key_id in the platform

## Getting Help

- Documentation: https://docs.artcafe.ai
- Examples: [GitHub examples](../examples/)
- Community: Discord/Slack
- Support: support@artcafe.ai