# ArtCafe.ai Agent Framework

A flexible, modular framework for building intelligent agents that communicate through our pub/sub messaging system. The framework is designed to simplify the creation of collaborative agent networks while providing robust lifecycle management, messaging, and configuration capabilities.

## Overview

The Agent Framework is a key component of the ArtCafe.ai platform, providing the foundation for building intelligent agents that can:

- Communicate over the pub/sub messaging system
- Discover and collaborate with other agents
- Process complex data and make decisions
- Self-report status and health metrics
- Manage their own lifecycle (start, stop, pause, etc.)

The framework implements a clean, extensible architecture with well-defined interfaces and pluggable components, making it easy to customize and extend.

## Architecture

### Core Components

- **BaseAgent**: Abstract base class that defines the agent lifecycle and messaging patterns
- **EnhancedAgent**: Extension with integrated messaging, configuration, and advanced features
- **MessagingInterface**: Abstraction layer for all messaging operations
- **Provider Pattern**: Support for different messaging backends (in-memory, AWS IoT, etc.)

### Directory Structure

```
/agent_framework/
├── agents/                 # Agent implementations
├── framework/              # Core framework code
│   ├── auth/               # Authentication providers
│   ├── core/               # Base agent classes and configuration
│   ├── examples/           # Example agent implementations
│   ├── knowledge/          # Knowledge integration components
│   ├── messaging/          # Messaging providers and interfaces
│   └── mcp/                # Management control plane integration
├── main.py                 # Main entry point for running agents
├── mocks/                  # Mock data and services for testing
└── utils/                  # Utility functions for agents
```

## Quick Start

### Installation

1. Ensure you have Python 3.8+ installed
2. Clone the repository and navigate to the agent_framework directory
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Example

The framework includes example implementations that demonstrate the core functionality:

```bash
python main.py --run-time 30
```

This will:
1. Initialize the system with default settings
2. Create and start two agents (triage and investigative)
3. Process simulated security findings
4. Generate a comprehensive report of agent interactions

### Using the Enhanced Examples

For a more advanced example using the enhanced agent classes:

```bash
python -m framework.examples.enhanced_runner --run-time 30
```

## Creating Your Own Agents

1. Create a new agent class that extends `EnhancedAgent`:

```python
from framework.core.enhanced_agent import EnhancedAgent

class MyCustomAgent(EnhancedAgent):
    def __init__(self, agent_id=None, config=None):
        super().__init__(agent_id=agent_id, agent_type="custom", config=config)
        self.add_capability("custom_processing")
    
    def _setup_subscriptions(self):
        # Subscribe to relevant topics
        self.subscribe("data/input/#")
    
    def process_message(self, topic, message):
        # Process incoming messages
        if super().process_message(topic, message):
            # Handle custom processing logic
            data = message.get("data", {})
            result = self._process_data(data)
            
            # Publish results
            self.publish("data/results", result)
            return True
        return False
    
    def _process_data(self, data):
        # Custom processing logic
        return {"processed": True, "result": "Success"}
```

2. Create a runner script to start your agent:

```python
import time
from my_custom_agent import MyCustomAgent

def main():
    # Create and start the agent
    agent = MyCustomAgent()
    agent.start()
    
    try:
        # Keep the agent running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent...")
    finally:
        agent.stop()

if __name__ == "__main__":
    main()
```

## Key Features

### Topic-Based Communication

Agents communicate through a topic-based messaging system, where topics are organized in a hierarchical structure:

- `agents/control/{agent_id}/#`: Control messages for a specific agent
- `agents/status/{agent_id}`: Status reports from an agent
- `agents/presence/online`: Agent presence announcements
- `agents/discovery/requests`: Agent discovery requests
- `agents/discovery/responses`: Agent discovery responses

### Permission Model

The framework includes a fine-grained permission model that controls what topics an agent can publish to or subscribe to:

```python
# Create a token with specific permissions
token = create_token("agent-id", [
    "publish:data/results/#",
    "subscribe:data/input/#",
    "subscribe:agents/broadcast/#"
])
```

### Agent Discovery

Agents can discover other agents with specific capabilities:

```python
# Publish a discovery request
self.publish("agents/discovery/requests", {
    "request_id": str(uuid.uuid4()),
    "agent_type": "processor",
    "capabilities": ["data_processing", "text_analysis"],
    "timestamp": time.time()
})

# Set up a handler for responses
self.subscribe("agents/discovery/responses", self._handle_discovery_response)
```

### Resource Authorization

Control access to resources:

```python
# Add resource authorizations
agent.add_resource_authorization("finding", ["read", "write", "update"])
agent.add_resource_authorization("alert", ["create"])

# Check authorization
if agent.authorize_resource("finding", finding_id, "update"):
    # Proceed with the update
    pass
```

## Integration with PubSub

The Agent Framework integrates seamlessly with the ArtCafe.ai PubSub system, using a provider architecture:

1. **In-Memory Provider**: For local development and testing
2. **AWS IoT Provider**: For production deployment on AWS
3. Custom providers: Implement the `MessagingProvider` interface for your own backends

To specify which provider to use:

```python
config = AgentConfig()
config.set("messaging.provider", "aws_iot")
agent = EnhancedAgent(config=config)
```

## Contributing

We welcome contributions to the Agent Framework! Please see the CONTRIBUTING.md file for guidelines.

## License

This project is proprietary and confidential. All rights reserved.