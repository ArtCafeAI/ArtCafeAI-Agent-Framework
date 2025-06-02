# Heartbeat Agent Guide

## Overview

The HeartbeatAgent class provides automatic heartbeat functionality to ensure accurate agent status tracking in the ArtCafe platform. This is essential for maintaining reliable agent presence and enabling proper monitoring in production environments.

## Why Heartbeats Matter

Without heartbeats:
- Agents that crash or lose connection may appear "online" indefinitely
- The dashboard shows inaccurate agent status
- Resource allocation and monitoring become unreliable

With heartbeats:
- Agents are automatically marked offline after 90 seconds of no activity
- Dashboard accurately reflects agent availability
- Failed agents are detected and can trigger alerts

## Quick Start

```python
from artcafe.framework.core import HeartbeatAgent

# Create an agent with automatic heartbeats
agent = HeartbeatAgent(
    agent_id="my-agent-001",
    private_key_path="path/to/private_key.pem",
    organization_id="your-org-id",
    heartbeat_interval=30  # seconds
)

# Add message handlers
@agent.on_message("tasks.new")
async def handle_task(subject, data):
    print(f"Processing task: {data}")
    # Your task processing logic here

# Run the agent
await agent.run()
```

## Configuration Options

### Heartbeat Settings

- **heartbeat_interval** (default: 30 seconds)
  - How often to send heartbeat messages
  - Lower values = more responsive status updates but higher network usage
  - Recommended: 30-60 seconds for most agents

- **heartbeat_timeout_multiplier** (default: 3.0)
  - Multiplied by interval to determine timeout threshold
  - Example: 30s interval × 3.0 = 90s timeout
  - Agent marked offline if no heartbeat for this duration

- **auto_reconnect** (default: True)
  - Automatically reconnect on connection loss
  - Includes exponential backoff to prevent connection storms
  - Maximum 10 reconnection attempts

## Advanced Usage

### Custom Heartbeat Agent

```python
class CustomMonitoringAgent(HeartbeatAgent):
    """Agent with custom heartbeat handling."""
    
    async def setup(self):
        # Set up your message handlers
        @self.on_message("system.health")
        async def health_check(subject, data):
            # Get connection health status
            health = self.get_connection_health()
            
            await self.publish("health.response", {
                "agent_id": self.agent_id,
                "healthy": health['healthy'],
                "last_heartbeat": health['last_heartbeat_ack'],
                "uptime": health['seconds_since_ack']
            })
    
    async def run(self):
        await self.setup()
        await super().run()
```

### Monitoring Connection Health

```python
# Get current connection health
health = agent.get_connection_health()

print(f"Connection healthy: {health['healthy']}")
print(f"Connected: {health['connected']}")
print(f"Last heartbeat ACK: {health['last_heartbeat_ack']}")
print(f"Seconds since ACK: {health['seconds_since_ack']}")
print(f"Reconnect attempts: {health['reconnect_attempts']}")
```

## Best Practices

1. **Use HeartbeatAgent for Production**
   - Always use HeartbeatAgent instead of SimpleAgent in production
   - Ensures accurate status tracking and monitoring

2. **Configure Appropriate Intervals**
   - Critical agents: 15-30 seconds
   - Standard agents: 30-60 seconds  
   - Low-priority agents: 60-120 seconds

3. **Handle Reconnections Gracefully**
   - Implement state recovery after reconnection
   - Log reconnection events for monitoring

4. **Monitor Agent Health**
   - Set up alerts for agents that go offline
   - Track heartbeat metrics in your monitoring system

## Migration from SimpleAgent

Migrating from SimpleAgent to HeartbeatAgent is straightforward:

```python
# Before (SimpleAgent)
from artcafe.framework.core import SimpleAgent

agent = SimpleAgent(
    agent_id="my-agent",
    private_key_path="key.pem",
    organization_id="org-id"
)

# After (HeartbeatAgent)
from artcafe.framework.core import HeartbeatAgent

agent = HeartbeatAgent(
    agent_id="my-agent",
    private_key_path="key.pem",
    organization_id="org-id",
    heartbeat_interval=30  # Add heartbeat configuration
)
```

## Troubleshooting

### Agent Shows Offline Despite Running

1. Check heartbeat interval is appropriate
2. Verify network connectivity
3. Check agent logs for heartbeat errors
4. Ensure WebSocket connection is stable

### Too Many Reconnection Attempts

1. Check network stability
2. Verify authentication credentials
3. Consider increasing reconnect delay
4. Check server-side logs for errors

### High Network Usage

1. Increase heartbeat interval
2. Batch messages where possible
3. Monitor actual heartbeat frequency

## Example: Production Monitoring Agent

See [examples/heartbeat_example.py](../examples/heartbeat_example.py) for a complete example of a production-ready monitoring agent with:

- Automatic heartbeats
- Connection health monitoring
- Periodic status reports
- Graceful error handling
- Auto-reconnection support