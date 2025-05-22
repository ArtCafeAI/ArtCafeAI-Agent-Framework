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

- **Lightweight Agent Core**: Base agent classes with essential functionality
- **Flexible Messaging**: Multiple messaging backends (memory, pub/sub, etc.)
- **LLM Integration**: Plug-and-play support for leading LLM providers
- **Tool Framework**: Decorator-based tool creation and registry
- **Event Loop Architecture**: Structured flow for agent-LLM interactions
- **Conversation Management**: Context window management for LLM interactions
- **MCP Support**: Integration with Model Context Protocol servers
- **Telemetry & Tracing**: Built-in metrics collection and tracing

## Installation

```bash
# Install from source
git clone https://github.com/artcafeai/artcafe-agent-framework.git
cd artcafe-agent-framework
pip install -e .

# Or install with optional dependencies
pip install -e ".[llm-providers,dev]"
```

## Quick Start

Here's a minimal example of creating an agent with the ArtCafe.ai Agent Framework:

```python
from artcafe.framework.core.enhanced_agent import EnhancedAgent
from artcafe.framework.tools import tool
from artcafe.framework.llm import get_llm_provider

# Create a simple tool with the @tool decorator
@tool
def calculate_sum(a: int, b: int) -> int:
    """
    Calculate the sum of two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of the two numbers
    """
    return a + b

# Create a simple agent
class MathAgent(EnhancedAgent):
    def __init__(self, agent_id=None, config=None):
        super().__init__(agent_id=agent_id, agent_type="math", config=config)
        self.add_capability("basic_math")
        
        # Initialize LLM provider
        self.llm = get_llm_provider(self.config.get("llm", {}))
    
    async def process_message(self, topic, message):
        # Handle parent processing
        if await super().process_message(topic, message):
            # Add custom processing logic
            if topic == "math/calculate":
                result = await self._process_calculation(message)
                await self.publish("math/results", result)
                return True
        return False
    
    async def _process_calculation(self, message):
        # Use LLM to understand the math problem
        prompt = f"Understand this math problem: {message.get('problem')}"
        response = await self.llm.generate(prompt=prompt)
        
        # Generate a response
        return {
            "problem": message.get("problem"),
            "solution": response["data"]["content"],
            "agent_id": self.agent_id
        }
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

## Advanced Topics

For more advanced usage, check out the example scripts in the `examples/` directory. These demonstrate:

- Building multi-agent systems
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