# ArtCafe Agent Framework Architecture

## Core Philosophy: Peer-Based Messaging

The ArtCafe Agent Framework is built on the principle that **all agents are peers**. This fundamental design choice shapes how agents interact and collaborate.

### Key Principles

1. **No Hierarchy**: There are no special "producer" or "consumer" agents. Every agent is equal.

2. **Broadcast Messaging**: When an agent publishes to a channel, all subscribed agents receive the message.

3. **Independent Decision Making**: Each agent decides for itself whether and how to respond to messages.

4. **Collaborative Intelligence**: Complex behaviors emerge from simple peer interactions.

## How It Works

### Channel Subscriptions

```python
# All agents subscribing to a channel receive ALL messages
@agent.on_message("team.discussion")
async def handle_discussion(subject, data):
    # Every agent gets this message
    # Each decides independently what to do
```

### Message Flow

1. Agent A publishes a message to `team.discussion`
2. ALL agents subscribed to `team.discussion` receive the message
3. Each agent independently decides:
   - Should I respond to this?
   - Is this relevant to my capabilities?
   - What value can I add?

### Coordination Without Central Control

Agents coordinate through the messages themselves:

```python
# Agent announces it's handling a task
await agent.publish("tasks.claims", {
    "task_id": "123",
    "agent_id": agent.id
})

# All other agents see this and know not to duplicate work
```

## Benefits

### Scalability
- Adding new agents doesn't require reconfiguring existing ones
- No bottlenecks from centralized coordinators
- Natural load distribution

### Resilience
- No single point of failure
- If one agent fails, others continue
- Self-healing through peer discovery

### Flexibility
- Easy to add new capabilities
- Agents can be specialized or general-purpose
- Emergent behaviors from simple rules

## Examples

### Collaborative Task Processing

Instead of dedicated task producers and consumers:

```python
class CollaborativeAgent(SimplifiedAgent):
    async def handle_new_task(self, subject, task):
        # All agents see the task
        if self.can_handle(task) and not self.busy:
            # Claim it
            await self.publish("task.claims", {"task_id": task["id"]})
            # Process it
            await self.process_task(task)
```

### Group Decision Making

Multiple agents contributing to decisions:

```python
@agent.on_message("decisions.needed")
async def contribute_to_decision(subject, question):
    # Each agent with relevant knowledge responds
    if self.has_expertise_in(question["domain"]):
        my_analysis = await self.analyze(question)
        await agent.publish("decisions.input", my_analysis)
```

### Dynamic Team Formation

Agents self-organize based on capabilities:

```python
@agent.on_message("team.forming")
async def join_team(subject, requirements):
    # Agents with matching skills join
    if self.matches_requirements(requirements):
        await agent.publish("team.members", {
            "agent_id": self.id,
            "capabilities": self.capabilities
        })
```

## Best Practices

1. **Design for Broadcast**: Assume all agents see your messages

2. **Be a Good Peer**: Don't flood channels with unnecessary messages

3. **Coordinate Through Messages**: Use the messaging itself for coordination

4. **Think Collectively**: Design agents that work well with others

5. **Handle Partial Failures**: Your agent should work even if others fail

## Getting Started

The simplest peer agent:

```python
agent = SimplifiedAgent(
    agent_id="my-peer",
    organization_id="org-123",
    private_key_path="~/.ssh/key"
)

@agent.on_message("team.chat")
async def participate(subject, data):
    # Every message to team.chat comes here
    # Decide what to do with it
    pass

asyncio.run(agent.run_forever())
```

## Learn More

- See [examples/peer_agents_example.py](examples/peer_agents_example.py) for a complete demonstration
- Try [examples/collaborative_task_processing.py](examples/collaborative_task_processing.py) for task coordination
- Read the [Quick Start Guide](docs/quick_start.md) for step-by-step instructions