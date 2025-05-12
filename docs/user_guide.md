# ArtCafe.ai Agent Framework User Guide

## Introduction

The ArtCafe.ai Agent Framework provides a robust foundation for building intelligent agents that communicate and collaborate through a distributed messaging system. This guide will walk you through the process of setting up, configuring, and developing agents using the framework.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Agent Architecture](#agent-architecture)
3. [Configuration](#configuration)
4. [Authentication](#authentication)
5. [Messaging System](#messaging-system)
6. [LLM Integration](#llm-integration)
7. [Creating Custom Agents](#creating-custom-agents)
8. [Web Portal Integration](#web-portal-integration)
9. [Debugging and Troubleshooting](#debugging-and-troubleshooting)

## Getting Started

### Prerequisites

- Python 3.8 or higher
- An ArtCafe.ai account with tenant and agent registration
- SSH key generation capability

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/artcafe-ai/agent-framework.git
   cd agent-framework
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the setup script:
   ```bash
   ./setup_agent.py --interactive
   ```

The setup script will:
- Generate an SSH key pair for your agent
- Create a configuration file with your agent details
- Guide you through registering your agent with ArtCafe.ai

### Running Your First Agent

After completing setup, you can run one of the example agents:

```bash
# Using the enhanced example runner
python -m framework.examples.enhanced_runner --config ~/.artcafe/config.yaml

# Using the main runner with example agents
python main.py --config ~/.artcafe/config.yaml
```

## Agent Architecture

### Core Components

The framework implements a layered architecture:

1. **BaseAgent** - Abstract base class defining the agent lifecycle
2. **EnhancedAgent** - Extension with integrated messaging and LLM capabilities
3. **MessagingInterface** - Abstraction for communication
4. **AuthProvider** - Authentication mechanisms
5. **LLMProvider** - LLM integration

### Agent Lifecycle

Agents follow a standard lifecycle:

1. **Initialization**: Load configuration and set up resources
2. **Authentication**: Authenticate with the messaging system
3. **Start**: Begin processing messages and subscriptions
4. **Process**: Handle messages and perform tasks
5. **Stop**: Clean up resources and exit gracefully

### Key Interfaces

```
BaseAgent
├── start()
├── stop()
├── process_message(topic, message)
└── register_handler(topic, handler)

MessagingInterface
├── publish(topic, message)
├── subscribe(topic, handler)
├── unsubscribe(topic)
└── authenticate(permissions)

LLMProvider
├── generate(prompt, ...)
├── chat(messages, ...)
└── embed(text, ...)
```

## Configuration

### Configuration File

Agents are configured using YAML or JSON files. The default location is `~/.artcafe/config.yaml`:

```yaml
# API configuration
api:
  endpoint: "https://api.artcafe.ai"
  version: "v1"
  websocket_endpoint: "wss://api.artcafe.ai/ws"

# Authentication
auth:
  agent_id: "your-agent-id"     # From ArtCafe.ai portal
  tenant_id: "your-tenant-id"   # From ArtCafe.ai portal
  ssh_key:
    private_key_path: "~/.ssh/artcafe_agent"
    key_type: "agent"
  retry_attempts: 5
  retry_delay: 1000
  token_refresh_margin: 300

# Messaging
messaging:
  provider: "artcafe_pubsub"
  heartbeat_interval: 30
  batch_size: 10
  message_ttl: 3600

# LLM configuration
llm:
  provider: "anthropic"
  model: "claude-3-opus-20240229"
  api_key: ""  # Set via ANTHROPIC_API_KEY environment variable
  anthropic:
    api_endpoint: "https://api.anthropic.com"
    max_tokens: 4096
    temperature: 0.7
  
# Logging
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: ""  # Leave empty for console logging
  max_size: 10  # MB
  backup_count: 5
```

### Configuration Sources

The framework loads configuration from multiple sources in the following order of precedence:

1. Command-line arguments
2. Environment variables (prefixed with `ARTCAFE_`)
3. Configuration file
4. Default values

### Environment Variables

Configuration can be provided through environment variables:

```bash
# Core settings
export ARTCAFE_AUTH_AGENT_ID="your-agent-id"
export ARTCAFE_AUTH_TENANT_ID="your-tenant-id"
export ARTCAFE_API_ENDPOINT="https://api.artcafe.ai"

# LLM provider API keys
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
```

## Authentication

### SSH Key Authentication

The framework uses SSH keys for secure agent authentication:

1. Generate an SSH key pair for your agent
2. Register the public key in the ArtCafe.ai portal
3. Configure the agent with the path to the private key
4. The agent will authenticate using a challenge-response flow

### Authentication Flow

1. Agent requests a challenge from the ArtCafe.ai API
2. Server sends a random challenge string
3. Agent signs the challenge with its private key
4. Agent sends the signature back to the server
5. Server verifies the signature with the registered public key
6. Server issues a JWT token for subsequent communications

### Manual Key Generation

If you prefer to generate keys manually:

```bash
# Generate a key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/artcafe_agent

# View the public key for registration
cat ~/.ssh/artcafe_agent.pub
```

## Messaging System

### Topic Structure

The messaging system uses a hierarchical topic structure:

- `agents/control/{agent_id}/#` - Control messages for a specific agent
- `agents/status/{agent_id}` - Status reports from an agent
- `agents/presence/online` - Agent presence announcements
- `agents/presence/offline` - Agent departure announcements
- `agents/discovery/requests` - Agent discovery requests
- `agents/discovery/responses` - Agent discovery responses
- `agents/heartbeat` - Periodic heartbeat messages
- `data/{topic}` - Application-specific data topics

### Subscribing to Topics

```python
# Subscribe to a specific topic
agent.subscribe("data/inputs", self.handle_input_message)

# Subscribe to a topic with wildcards
agent.subscribe("agents/status/#", self.handle_status_update)
```

### Publishing Messages

```python
# Publish a message to a topic
agent.publish("data/results", {
    "result_id": "12345",
    "value": 42,
    "timestamp": time.time()
})
```

### Message Format

Messages follow a standard format:

```json
{
  "type": "message",
  "id": "msg-uuid-1234",
  "topic": "data/results",
  "data": {
    "result_id": "12345",
    "value": 42,
    "timestamp": 1683720000
  },
  "timestamp": "2023-05-10T12:00:00Z"
}
```

## LLM Integration

### Supported Providers

The framework supports multiple LLM providers:

- **Anthropic** (Claude models)
- **OpenAI** (GPT models)
- **AWS Bedrock** (Various models)
- **Local** (Self-hosted models)

### Using LLMs in Agents

```python
from framework.llm import get_llm_provider

# Initialize LLM provider from config
llm = get_llm_provider(config.get("llm", {}))

# Generate text completion
response = await llm.generate(
    prompt="Summarize the following text: ...",
    system="You are a helpful AI assistant.",
    max_tokens=1000,
    temperature=0.7
)

# Chat completion
response = await llm.chat(
    messages=[
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Hello, who are you?"}
    ],
    temperature=0.7
)

# Generate embeddings
embeddings = await llm.embed(
    text=["Document 1", "Document 2", "Document 3"]
)
```

### Provider-Specific Configuration

Each provider has specific configuration options:

```yaml
llm:
  provider: "anthropic"
  model: "claude-3-opus-20240229"
  api_key: ""  # Set via ANTHROPIC_API_KEY environment variable
  
  # Anthropic-specific settings
  anthropic:
    api_endpoint: "https://api.anthropic.com"
    max_tokens: 4096
    temperature: 0.7
  
  # OpenAI-specific settings
  openai:
    api_endpoint: "https://api.openai.com"
    model: "gpt-4"
    max_tokens: 4096
    temperature: 0.7
  
  # AWS Bedrock-specific settings
  bedrock:
    region: "us-west-2"
    model_id: "anthropic.claude-3-opus-20240229"
    max_tokens: 4096
    temperature: 0.7
```

## Creating Custom Agents

### Basic Agent Template

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

### Agent Runner

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

### Adding Capabilities

Agents can advertise capabilities to help with discovery:

```python
# Add capabilities during initialization
def __init__(self, agent_id=None, config=None):
    super().__init__(agent_id=agent_id, agent_type="assistant", config=config)
    
    # Add capabilities
    self.add_capability("text_processing")
    self.add_capability("image_analysis")
    self.add_capability("data_transformation")
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

## Web Portal Integration

### Agent Registration

1. Log in to the ArtCafe.ai web portal
2. Navigate to the Agents section
3. Click "Register New Agent"
4. Provide a name and description for your agent
5. Select the agent type and capabilities
6. Submit to generate an agent ID

### SSH Key Management

1. Navigate to the SSH Keys section in the portal
2. Click "Add New Key"
3. Provide a name for the key
4. Paste the public key content from your `~/.ssh/artcafe_agent.pub` file
5. Select "Agent" as the key type
6. Associate the key with your agent ID
7. Submit to register the key

### Monitoring Agents

The web portal provides several tools for monitoring agents:

- **Agent Dashboard**: View all registered agents and their status
- **Agent Details**: See detailed information about a specific agent
- **Logs**: View logs from agent operations
- **Metrics**: Monitor performance and health metrics

## Debugging and Troubleshooting

### Enabling Debug Logging

For more detailed logs, set the logging level to DEBUG:

```yaml
logging:
  level: "DEBUG"
```

Or use an environment variable:

```bash
export ARTCAFE_LOGGING_LEVEL=DEBUG
```

### Common Issues and Solutions

**Authentication Failures**:
- Verify your agent_id and tenant_id are correct
- Ensure your SSH key is properly registered in the portal
- Check that your private key path is correct in the configuration

**Connection Issues**:
- Confirm your API endpoint is correct
- Check your network connection and firewall settings
- Verify that your agent has the necessary permissions

**Message Processing Errors**:
- Look for errors in message handling functions
- Verify topic subscriptions are correctly set up
- Check message format compliance

### Diagnostic Commands

The framework provides diagnostic commands for troubleshooting:

```bash
# Check agent configuration
python -m framework.tools.check_config --config ~/.artcafe/config.yaml

# Test authentication
python -m framework.tools.test_auth --config ~/.artcafe/config.yaml

# Test messaging connection
python -m framework.tools.test_messaging --config ~/.artcafe/config.yaml
```

### Logging

Logs are written to the console by default. To save logs to a file, update your configuration:

```yaml
logging:
  level: "INFO"
  file: "~/.artcafe/logs/agent.log"
  max_size: 10  # MB
  backup_count: 5
```

This will create rotating log files with the most recent information.