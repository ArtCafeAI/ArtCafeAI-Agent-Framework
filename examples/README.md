# ArtCafe Agent Examples

This directory contains example agents demonstrating various use cases and patterns for building agents on the ArtCafe platform.

## Available Examples

### 1. Data Processor Agent
**File**: `data_processor_agent.py`

A comprehensive example showing how to:
- Process batch data with progress tracking
- Handle streaming data
- Implement error handling and retries
- Track metrics and statistics
- Use templates for data transformation

**Use Cases**:
- ETL pipelines
- Data transformation
- Batch processing
- Stream processing

### 2. Notification Agent
**File**: `notification_agent.py`

Demonstrates multi-channel notification delivery:
- Email notifications via SMTP
- SMS notifications (Twilio integration)
- Webhook notifications
- Template support
- Rate limiting
- Bulk sending

**Use Cases**:
- Alert systems
- User notifications
- System monitoring
- Marketing campaigns

### 3. Web Scraper Agent
**File**: `web_scraper_agent.py`

Shows web scraping capabilities:
- HTML parsing with BeautifulSoup
- CSS selector support
- Link following and crawling
- Sitemap processing
- Caching and rate limiting
- Data extraction patterns

**Use Cases**:
- Data collection
- Website monitoring
- Content aggregation
- Price monitoring

## Getting Started

### Installation

1. Install the agent framework:
```bash
cd agent-framework
pip install -r requirements.txt
```

2. Install example-specific dependencies:
```bash
# For web scraper
pip install beautifulsoup4 httpx

# For notifications
pip install twilio  # optional, for SMS
```

### Configuration

Each example agent can be configured using a JSON file:

```json
{
    "agent_id": "your-agent-id",
    "tenant_id": "your-tenant-id",
    "private_key_path": "/path/to/private_key",
    "api_endpoint": "https://api.artcafe.ai",
    "log_level": "INFO"
}
```

### Running an Example

1. Generate SSH key pair:
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/artcafe_agent_key
```

2. Add public key to ArtCafe dashboard

3. Create configuration file:
```bash
cp config.example.json agent_config.json
# Edit with your values
```

4. Run the agent:
```bash
python data_processor_agent.py
```

## Common Patterns

### Command Registration
```python
self.register_command("process", self.handle_process)
self.register_command("status", self.handle_status)
```

### Error Handling
```python
try:
    result = await self.process_data(data)
    return {"status": "success", "result": result}
except Exception as e:
    self.logger.error(f"Processing error: {e}")
    return {"status": "error", "error": str(e)}
```

### Status Updates
```python
await self.update_status("busy", task_id=task_id, progress=50)
```

### Publishing Messages
```python
await self.publish("results/processed", {
    "task_id": task_id,
    "result": result,
    "timestamp": datetime.utcnow().isoformat()
})
```

### Subscribing to Topics
```python
await self.subscribe("tasks/new", self.handle_new_task)
```

## Building Your Own Agent

1. Start with a template:
```python
from artcafe_agent import ArtCafeAgent

class MyAgent(ArtCafeAgent):
    def __init__(self, config):
        super().__init__(
            agent_id=config["agent_id"],
            tenant_id=config["tenant_id"],
            private_key_path=config["private_key_path"]
        )
        
        # Register your commands
        self.register_command("my_command", self.handle_my_command)
    
    async def handle_my_command(self, args):
        # Implement your logic
        return {"status": "success"}
```

2. Add configuration:
```json
{
    "agent_id": "my-agent-001",
    "tenant_id": "tenant-123",
    "private_key_path": "~/.ssh/my_agent_key"
}
```

3. Run your agent:
```python
agent = MyAgent(config)
await agent.start()
```

## Best Practices

1. **Error Handling**: Always wrap operations in try-catch blocks
2. **Logging**: Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
3. **State Management**: Keep agent state minimal and recoverable
4. **Resource Cleanup**: Implement proper cleanup in stop handlers
5. **Rate Limiting**: Respect external API limits
6. **Testing**: Test locally before deploying

## Advanced Topics

### State Persistence
```python
# Save state to file
with open("state.json", "w") as f:
    json.dump(self.state, f)

# Load state on startup
if os.path.exists("state.json"):
    with open("state.json") as f:
        self.state = json.load(f)
```

### Custom Metrics
```python
self.metrics = {
    "requests_processed": 0,
    "average_response_time": 0
}

# Update metrics
self.metrics["requests_processed"] += 1
```

### Integration with External Services
```python
async def call_external_api(self, endpoint):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{self.api_url}/{endpoint}")
        return response.json()
```

## Testing

Test your agents locally:

```python
# Test with mock messaging
from artcafe_agent.testing import MockMessaging

agent = MyAgent(config)
agent.messaging = MockMessaging()

# Test command
result = await agent.handle_my_command({"test": "data"})
assert result["status"] == "success"
```

## Support

- Documentation: https://docs.artcafe.ai
- GitHub: https://github.com/artcafe-ai/agent-framework
- Community: https://community.artcafe.ai

## License

MIT License - see LICENSE file for details.