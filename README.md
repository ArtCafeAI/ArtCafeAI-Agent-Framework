# ArtCafe.ai Agent Framework

<div align="center">
  <img src="https://artcafe.ai/img/logo/artcafe-logo.png" alt="ArtCafe.ai Logo" width="200"/>
  <h3>A flexible, modular framework for building intelligent, collaborative AI agents</h3>
</div>

<div align="center">
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+">
  </a>
  <img src="https://img.shields.io/badge/pypi-v0.4.3-blue" alt="PyPI version">
</div>

<br/>

## Overview

The Agent Framework is a key component of the ArtCafe.ai platform, providing the foundation for building intelligent agents that can:

- Connect directly to NATS with NKey authentication for high-performance messaging
- Communicate through pub/sub patterns with automatic tenant isolation
- Collaborate with other agents as peers
- Process complex data and make decisions using integrated LLM providers
- Self-report status and health metrics via built-in heartbeat
- Manage their own lifecycle (start, stop, pause, etc.)

## 🚀 Quick Start

### Direct NATS Connection (Recommended)

```python
import asyncio
from framework.core.nats_agent import NATSAgent

async def main():
    # Create agent with NKey authentication
    agent = NATSAgent(
        client_id="my-client",
        tenant_id="your-tenant-id",
        nkey_seed="SUAIBDPBAUTWCWBKIO6XHQNINK5FWJW4OHLXC3HQ2KFE4PEJYQFN7MOVOA"
    )
    
    # Connect directly to NATS
    await agent.connect()
    
    # Handle messages with decorator
    @agent.on_message("tasks.*")
    async def handle_task(subject, data):
        print(f"Received task: {data}")
        await agent.publish("tasks.complete", {"status": "done"})
    
    # Keep running
    await agent.start()

asyncio.run(main())
```

### LLM-Powered Agent

```python
from framework import create_llm_agent

# Create an LLM agent with tools
agent = create_llm_agent(provider="anthropic", api_key="your-key")

@agent.tool
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Search results for: {query}"

# Chat with the agent
response = await agent.chat("What's the weather in Paris?")
```

## Key Features

### 🚀 Core Capabilities
- **NKey Authentication**: Direct NATS connection with Ed25519 keys
- **High Performance**: <1ms latency with direct NATS (no WebSocket layer)
- **Peer Messaging**: All agents are equal peers in the network
- **Automatic Tenant Isolation**: Subjects automatically prefixed with tenant ID
- **Built-in Heartbeat**: Connection health monitoring every 30 seconds
- **Multiple Agent Types**: NATSAgent, SimplifiedAgent, LLM agents, and more

### Framework Features
- **Flexible Messaging**: Multiple backends (NATS, memory, pub/sub)
- **LLM Integration**: Anthropic, OpenAI, and Bedrock providers
- **Tool Framework**: Easy tool creation with decorators
- **Workflow Patterns**: Chaining, routing, and parallel execution
- **MCP Support**: Model Context Protocol integration
- **A2A Protocol**: Agent-to-Agent communication
- **Telemetry**: Built-in metrics and tracing

## Installation

```bash
# Install from PyPI
pip install artcafe-agent-framework

# Install from source
git clone https://github.com/artcafeai/artcafe-agent-framework.git
cd artcafe-agent-framework
pip install -e .

# Install with optional dependencies
pip install -e ".[llm-providers,dev]"
```

## Architecture

The framework provides multiple agent implementations:

- **NATSAgent**: Direct NATS connection with NKey authentication (fastest)
- **SimplifiedAgent**: WebSocket-based with decorator patterns
- **HeartbeatAgent**: WebSocket with automatic heartbeat
- **LLM Agents**: Pre-configured for AI interactions

Choose the agent type that best fits your use case. For new projects, we recommend `NATSAgent` for its performance and simplicity.

## Directory Structure

```
/agent_framework/
├── agents/                 # Agent implementations
├── framework/              # Core framework code
│   ├── auth/               # Authentication providers
│   ├── conversation/       # Conversation management
│   ├── core/               # Base agent classes
│   ├── event_loop/         # Event loop architecture
│   ├── examples/           # Example agent implementations
│   ├── llm/                # LLM provider implementations
│   ├── mcp/                # Model Context Protocol
│   ├── messaging/          # Messaging providers
│   ├── telemetry/          # Metrics and tracing
│   └── tools/              # Tool decorator and registry
├── examples/               # Example scripts
└── setup.py                # Package setup
```

## NATS Integration

The framework now supports direct NATS connections with NKey authentication:

```python
from framework.core.nats_agent import NATSAgent

# Create a NATS-enabled agent
agent = NATSAgent(
    client_id="my-agent",
    tenant_id="your-tenant-id",
    nkey_seed="your-nkey-seed"
)

# All subjects are automatically prefixed with tenant_id
await agent.subscribe("sensors.*", handle_sensor_data)
await agent.publish("alerts.high", {"temperature": 98.6})

# Request/Response pattern
response = await agent.request("service.echo", {"message": "hello"})
```

See the [examples](examples/) directory for more usage patterns.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## About ArtCafe.ai

ArtCafe.ai provides infrastructure for building and deploying intelligent agent systems. Our platform enables AI agents to communicate, collaborate, and scale effectively.