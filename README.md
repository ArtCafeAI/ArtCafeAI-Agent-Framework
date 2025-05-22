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
  <img src="https://img.shields.io/badge/pypi-v0.3.0-blue" alt="PyPI version">
</div>

<br/>

## Overview

The Agent Framework is a key component of the ArtCafe.ai platform, providing the foundation for building intelligent agents that can:

- Communicate through a pub/sub messaging system
- Discover and collaborate with other agents
- Process complex data and make decisions
- Self-report status and health metrics
- Manage their own lifecycle (start, stop, pause, etc.)

The framework implements a clean, extensible architecture with well-defined interfaces and pluggable components, making it easy to customize and extend.

## Key Features

### 🚀 New: Simplified Agent Creation
- **SimpleAgent**: Get started with just 3 lines of code
- **AugmentedLLMAgent**: Start with LLM capabilities, add tools as needed
- **VerifiedAgent**: Built-in verification and ground truth checks
- **BudgetAwareAgent**: Cost tracking and budget enforcement

### Core Features
- **Lightweight Agent Core**: Base agent classes with essential functionality
- **Flexible Messaging**: Multiple messaging backends (memory, pub/sub, NATS)
- **NATS Integration**: Scalable pub/sub architecture with hierarchical topics
- **LLM Integration**: Plug-and-play support for leading LLM providers
- **Tool Framework**: Decorator-based tool creation and registry
- **Workflow Patterns**: Pre-built patterns for chaining, routing, and parallelization
- **Event Loop Architecture**: Structured flow for agent-LLM interactions
- **Conversation Management**: Context window management for LLM interactions
- **MCP Support**: Integration with Model Context Protocol servers (including MCP over NATS)
- **A2A Protocol**: Agent-to-Agent negotiation and coordination
- **Telemetry & Tracing**: Built-in metrics collection and tracing

## Installation

```bash
# Install from PyPI (coming soon)
pip install artcafe-agent-framework

# Install from source
git clone https://github.com/artcafeai/agent-framework.git
cd agent-framework
pip install -e .

# Or install with optional dependencies
pip install -e ".[llm-providers,dev]"
```

## Quick Start

### Hello World Example

The absolute simplest way to create an agent:

```python
from framework import create_agent

# Create and run an agent in 3 lines
agent = create_agent("my-agent")

@agent.on_message("hello")
def say_hello(message):
    return {"response": f"Hello, {message.get('name', 'World')}!"}

agent.run()
```

### LLM-First Example

Start with an LLM and add capabilities:

```python
from framework import create_llm_agent

# Create an LLM agent with tools
agent = create_llm_agent(provider="anthropic", api_key="your-key")

@agent.tool
def search_web(query: str) -> str:
    """Search the web for information."""
    # Your search implementation
    return f"Search results for: {query}"

# Chat with the agent
response = await agent.chat("What's the weather in Paris?")
print(response)
```

### Verified Agent Example

Build reliable agents with verification:

```python
from framework import VerifiedAgent, verify_input, verify_output

class DataAgent(VerifiedAgent):
    @verify_input(lambda x: "data" in x)
    @verify_output(lambda x: x is not None)
    async def process_data(self, message):
        # Process with automatic verification
        return {"processed": message["data"].upper()}
```

## Architecture

The ArtCafe.ai Agent Framework is built on a modular architecture with these key components:

### Core Components

- **BaseAgent**: Abstract base class that defines the agent lifecycle and messaging patterns
- **EnhancedAgent**: Extension with integrated messaging, configuration, and advanced features
- **MessagingInterface**: Abstraction layer for all messaging operations
- **Provider Pattern**: Support for different messaging backends (in-memory, pub/sub)
- **LLM Integration**: Pluggable LLM providers (Anthropic, OpenAI, Bedrock)

### Directory Structure

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
├── main.py                 # Main entry point
└── setup_agent.py          # Setup script
```

## NATS Integration

The framework now supports NATS as a scalable messaging backbone:

```python
from framework.core import NATSAgent, AgentConfig

# Create a NATS-enabled agent
config = AgentConfig({"nats.servers": ["nats://localhost:4222"]})
agent = NATSAgent(agent_id="my-agent", config=config)

# Use MCP over NATS
await agent.call_mcp_tool("remote-server", "search", {"query": "AI news"})

# A2A negotiations
result = await agent.negotiate_with_agents(
    ["agent-2", "agent-3"],
    "task_assignment",
    {"task": "process_data", "size": "10GB"}
)
```

See the [NATS Integration Guide](docs/nats_integration.md) for details.

## Advanced Topics

For more advanced usage, check out the example scripts in the `examples/` directory. These demonstrate:

- Building multi-agent systems with NATS
- Using MCP over NATS and A2A protocols
- Customizing LLM providers
- Creating tool libraries
- Implementing custom messaging backends
- Integrating with external services

## Contributing

We welcome contributions to the Agent Framework! Please see the [Contributing Guide](CONTRIBUTING.md) for details on how to get involved.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## About ArtCafe.ai

[ArtCafe.ai](https://artcafe.ai) is building the future of AI collaboration by providing tools, frameworks, and infrastructure for creating and deploying intelligent agent systems. Our mission is to make AI agents accessible, composable, and useful for real-world tasks.