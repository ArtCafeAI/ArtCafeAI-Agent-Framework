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

## New Multi-Tenant Support

We've enhanced the framework with full multi-tenant support:

- **SSH Key Authentication**: Secure agent identity management using SSH keys
- **ArtCafe.ai PubSub Integration**: Connect directly to the ArtCafe.ai pub/sub service
- **Tenant Isolation**: Ensure data and messages are properly isolated between tenants
- **Web Portal Support**: Register and manage agents through the ArtCafe.ai web portal

## Architecture

### Core Components

- **BaseAgent**: Abstract base class that defines the agent lifecycle and messaging patterns
- **EnhancedAgent**: Extension with integrated messaging, configuration, and advanced features
- **MessagingInterface**: Abstraction layer for all messaging operations
- **Provider Pattern**: Support for different messaging backends (in-memory, AWS IoT, ArtCafe PubSub)
- **LLM Integration**: Pluggable LLM providers (Anthropic, OpenAI, Bedrock)

### Directory Structure

```
/agent_framework/
├── agents/                 # Agent implementations
├── framework/              # Core framework code
│   ├── auth/               # Authentication providers (SSH, token)
│   ├── core/               # Base agent classes and configuration
│   ├── examples/           # Example agent implementations
│   ├── knowledge/          # Knowledge integration components
│   ├── llm/                # LLM provider implementations
│   ├── messaging/          # Messaging providers and interfaces
│   └── mcp/                # Management control plane integration
├── main.py                 # Main entry point for running agents
├── setup_agent.py          # Setup script for configuring agents
├── mocks/                  # Mock data and services for testing
└── utils/                  # Utility functions for agents
```

## Quick Start

### Setup

1. Ensure you have Python 3.8+ installed
2. Clone the repository and navigate to the agent_framework directory
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the setup script:
   ```bash
   ./setup_agent.py --interactive
   ```
   
This script will:
1. Generate an SSH key pair for your agent
2. Create a configuration file with your agent details
3. Display next steps for registering your agent with ArtCafe.ai

### Manual Configuration

If you prefer to set up manually:

1. Create an SSH key pair for your agent:
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/artcafe_agent
   ```

2. Create a configuration file (`~/.artcafe/config.yaml`):
   ```yaml
   api:
     endpoint: "https://api.artcafe.ai"
     version: "v1"
     websocket_endpoint: "wss://api.artcafe.ai/ws"
   
   auth:
     agent_id: "your-agent-id"     # From ArtCafe.ai portal
     tenant_id: "your-tenant-id"   # From ArtCafe.ai portal
     ssh_key:
       private_key_path: "~/.ssh/artcafe_agent"
       key_type: "agent"
   
   messaging:
     provider: "artcafe_pubsub"
     heartbeat_interval: 30
   
   llm:
     provider: "anthropic"
     model: "claude-3-opus-20240229"
     api_key: ""  # Set via ANTHROPIC_API_KEY environment variable
   ```

3. Register your agent and SSH key on the ArtCafe.ai portal

### Running an Agent

```bash
# Using the enhanced example
python -m framework.examples.enhanced_runner --config ~/.artcafe/config.yaml

# Using the standard examples
python main.py --config ~/.artcafe/config.yaml
```

## Creating Custom Agents

1. Create a new agent class that extends `EnhancedAgent`:

```python
from framework.core.enhanced_agent import EnhancedAgent
from framework.llm import get_llm_provider

class MyCustomAgent(EnhancedAgent):
    def __init__(self, agent_id=None, config=None):
        super().__init__(agent_id=agent_id, agent_type="custom", config=config)
        self.add_capability("custom_processing")
        
        # Initialize LLM provider
        self.llm = get_llm_provider(self.config.get("llm", {}))
    
    def _setup_subscriptions(self):
        # Subscribe to relevant topics
        self.subscribe("data/input/#")
    
    async def process_message(self, topic, message):
        # Process incoming messages
        if await super().process_message(topic, message):
            # Handle custom processing logic
            data = message.get("data", {})
            result = await self._process_data(data)
            
            # Publish results
            await self.publish("data/results", result)
            return True
        return False
    
    async def _process_data(self, data):
        # Custom processing logic using LLM
        response = await self.llm.generate(
            prompt=f"Process this data: {data}",
            system="You are a helpful AI assistant."
        )
        
        return {"processed": True, "result": response["data"]["content"]}
```

2. Create a runner script to start your agent:

```python
import asyncio
import logging
from my_custom_agent import MyCustomAgent
from framework.core.config_loader import ConfigLoader

async def main():
    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.load(config_file="~/.artcafe/config.yaml")
    
    # Create and start the agent
    agent = MyCustomAgent(config=config)
    await agent.start()
    
    try:
        # Keep the agent running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent...")
    finally:
        await agent.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

## Key Features

### Multi-Tenant Authentication

Agents authenticate securely using SSH keys and a challenge-response flow:

1. Agent requests a challenge from the ArtCafe.ai API
2. Agent signs the challenge with its private key
3. Server verifies the signature using the registered public key
4. Server issues a JWT token for subsequent API calls

### Topic-Based Communication

Agents communicate through a topic-based messaging system with a hierarchical structure:

- `agents/control/{agent_id}/#`: Control messages for a specific agent
- `agents/status/{agent_id}`: Status reports from an agent
- `agents/presence/online`: Agent presence announcements
- `agents/discovery/requests`: Agent discovery requests
- `agents/discovery/responses`: Agent discovery responses

### LLM Integration

The framework provides a flexible LLM integration layer:

- Multiple provider support (Anthropic, OpenAI, Bedrock)
- Easy switching between models
- Standardized interface for text generation and embeddings
- Automatic token counting and optimization

## Web Portal Integration

Agents can be managed through the ArtCafe.ai web portal:

- Register agents and generate IDs
- Manage SSH keys for authentication
- Monitor agent status and activity
- Configure agent parameters
- View logs and metrics

## Contributing

We welcome contributions to the Agent Framework! Please see the CONTRIBUTING.md file for guidelines.

## License

This project is proprietary and confidential. All rights reserved.