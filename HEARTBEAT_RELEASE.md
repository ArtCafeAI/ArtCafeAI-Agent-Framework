# HeartbeatAgent - Production-Ready Agent with Automatic Status Tracking

## 🚀 New Feature Release

We've released the **HeartbeatAgent** class, which provides automatic heartbeat functionality for accurate agent status tracking in production environments.

## Key Benefits

### 1. **Accurate Status Tracking**
- Agents automatically send heartbeats every 30 seconds
- Dashboard shows real-time agent availability
- Failed agents are detected within 90 seconds

### 2. **Cost-Optimized Implementation**
- DynamoDB scans reduced from every 60 seconds to every 5 minutes
- 80% reduction in read operations
- Same reliability with lower costs

### 3. **Built-in Resilience**
- Automatic reconnection on connection loss
- Exponential backoff to prevent connection storms
- Connection health monitoring

## Quick Start

```python
from artcafe.framework.core import HeartbeatAgent

# Create an agent with automatic heartbeats
agent = HeartbeatAgent(
    agent_id="production-agent-001",
    private_key_path="path/to/private_key.pem",
    organization_id="your-org-id",
    heartbeat_interval=30,  # seconds
    auto_reconnect=True     # automatic reconnection
)

# Add your message handlers
@agent.on_message("tasks.process")
async def process_task(subject, data):
    # Your task processing logic
    print(f"Processing: {data}")

# Run the agent
await agent.run()
```

## Migration Guide

### From SimpleAgent to HeartbeatAgent

```python
# Before
from artcafe.framework.core import SimpleAgent
agent = SimpleAgent(agent_id="my-agent", ...)

# After
from artcafe.framework.core import HeartbeatAgent
agent = HeartbeatAgent(agent_id="my-agent", ...)
```

No other code changes required! The HeartbeatAgent is a drop-in replacement with added reliability.

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `heartbeat_interval` | 30 | Seconds between heartbeats |
| `heartbeat_timeout_multiplier` | 3.0 | Multiplier for timeout (30s × 3 = 90s timeout) |
| `auto_reconnect` | True | Automatically reconnect on connection loss |

## Monitoring Connection Health

```python
# Get real-time connection health
health = agent.get_connection_health()

print(f"Healthy: {health['healthy']}")
print(f"Last heartbeat: {health['last_heartbeat_ack']}")
print(f"Time since ACK: {health['seconds_since_ack']}s")
```

## Architecture Benefits

### For Developers
- No manual heartbeat implementation needed
- Built-in connection monitoring
- Automatic status management

### For Operations
- Accurate agent monitoring in dashboards
- Automatic cleanup of stale connections
- Reduced DynamoDB costs (5-minute scan interval)

### For Scaling
- Works seamlessly across multiple servers
- No coordination required between servers
- DynamoDB provides shared state

## Examples

See the complete examples:
- [examples/heartbeat_example.py](examples/heartbeat_example.py) - Full monitoring agent example
- [docs/heartbeat_guide.md](docs/heartbeat_guide.md) - Comprehensive guide

## Best Practices

1. **Always use HeartbeatAgent in production** - SimpleAgent is for development only
2. **Configure appropriate intervals** - 30s for critical agents, 60s for standard
3. **Monitor connection health** - Set up alerts for offline agents
4. **Handle reconnections gracefully** - Implement state recovery if needed

## Technical Details

- Heartbeats are sent via WebSocket as `{"type": "heartbeat"}`
- Server acknowledges with `{"type": "heartbeat_ack"}`
- Agents marked offline if no heartbeat for 90 seconds
- DynamoDB cleanup runs every 5 minutes (cost-optimized)

## Support

For questions or issues:
- Check the [heartbeat guide](docs/heartbeat_guide.md)
- Review the [example implementation](examples/heartbeat_example.py)
- Open an issue on GitHub

---

**Released**: June 1, 2025  
**Version**: 1.0.0  
**Status**: Production Ready