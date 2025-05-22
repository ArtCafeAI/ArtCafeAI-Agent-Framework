# ArtCafe.ai Agent Framework Developer Guide

## Overview

This guide provides in-depth technical information for developers who want to extend the ArtCafe.ai Agent Framework or contribute to its development. It covers the framework architecture, core components, extension points, and best practices.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Extension Points](#extension-points)
4. [Authentication System](#authentication-system)
5. [Messaging System](#messaging-system)
6. [LLM Integration](#llm-integration)
7. [Testing](#testing)
8. [Contributing Guidelines](#contributing-guidelines)

## Architecture Overview

### Design Principles

The Agent Framework is built on these core principles:

1. **Modularity**: Components are decoupled and interconnected through well-defined interfaces
2. **Extensibility**: Key components can be extended through inheritance or composition
3. **Configurability**: Behavior can be customized through configuration without code changes
4. **Security**: Authentication and authorization are built into the core architecture
5. **Observability**: Comprehensive logging, metrics, and status reporting

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                       Application Layer                     │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │TriageAgent  │  │AnalyticsAgent│  │ InvestigativeAgent │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                      Framework Layer                        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │EnhancedAgent│  │ConfigLoader │  │ ResourceManager     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Provider Layer                            │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │AuthProvider │  │MessagingProv│  │ LLMProvider         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Integration Layer                         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │SSH Auth     │  │ArtCafe PubSub│  │ LLM Providers      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### BaseAgent

The `BaseAgent` class is the foundation of all agents in the framework. It implements:

- Agent lifecycle management (start/stop)
- Message processing interfaces
- Status and capability reporting
- Message handler registration

**Key Methods**:

```python
def start(self) -> bool:
    """Start the agent, initialize resources."""
    
def stop(self) -> bool:
    """Stop the agent, clean up resources."""
    
def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
    """Process a message received from a topic."""
    
def register_handler(self, topic_pattern: str, handler: Callable) -> None:
    """Register a handler for a specific topic pattern."""
    
def get_status(self) -> Dict[str, Any]:
    """Get detailed status information about this agent."""
```

### EnhancedAgent

The `EnhancedAgent` extends `BaseAgent` with additional capabilities:

- Configuration management
- Integrated messaging
- Enhanced lifecycle management
- Authentication and authorization
- Subscription management

**Key Methods**:

```python
def subscribe(self, topic: str, handler: Optional[Callable] = None) -> bool:
    """Subscribe to a topic with a handler function."""
    
def unsubscribe(self, topic: str) -> bool:
    """Unsubscribe from a topic."""
    
def publish(self, topic: str, message: Dict[str, Any]) -> bool:
    """Publish a message to a topic."""
    
def add_resource_authorization(self, resource_type: str, actions: List[str]) -> None:
    """Add authorization for actions on a resource type."""
```

### ConfigLoader

The `ConfigLoader` manages the loading and validation of configuration from various sources:

- Configuration files (YAML/JSON)
- Environment variables
- Command-line arguments
- Default values

**Key Methods**:

```python
def load(self, args: Optional[Dict[str, Any]] = None, 
         env_prefix: str = "ARTCAFE_", 
         config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from various sources."""
```

### MessagingInterface

The `MessagingInterface` defines the contract for messaging providers:

- Message publishing
- Topic subscription
- Authentication

**Key Methods**:

```python
async def publish(self, topic: str, message: Dict[str, Any]) -> bool:
    """Publish a message to a topic."""
    
async def subscribe(self, topic: str, handler: Callable) -> bool:
    """Subscribe to a topic with a handler function."""
    
async def unsubscribe(self, topic: str) -> bool:
    """Unsubscribe from a topic."""
    
async def authenticate(self, permissions: List[str]) -> bool:
    """Authenticate with the messaging system."""
```

### LLMProvider

The `LLMProvider` defines the contract for language model providers:

- Text generation
- Chat completion
- Embedding generation

**Key Methods**:

```python
async def generate(self, prompt: str, system: Optional[str] = None, 
                  max_tokens: Optional[int] = None, 
                  temperature: Optional[float] = None) -> Dict[str, Any]:
    """Generate text from the LLM."""
    
async def chat(self, messages: List[Dict[str, str]], 
              system: Optional[str] = None,
              max_tokens: Optional[int] = None, 
              temperature: Optional[float] = None) -> Dict[str, Any]:
    """Generate a response to a chat conversation."""
    
async def embed(self, text: Union[str, List[str]]) -> Dict[str, Any]:
    """Generate embeddings for text."""
```

## Extension Points

### Creating New Agents

To create a new agent type, extend the `EnhancedAgent` class:

```python
from framework.core.enhanced_agent import EnhancedAgent

class CustomAgent(EnhancedAgent):
    def __init__(self, agent_id=None, config=None):
        super().__init__(agent_id=agent_id, agent_type="custom", config=config)
        # Initialize agent-specific resources
        
    def _setup_subscriptions(self):
        # Set up topic subscriptions
        self.subscribe("data/input/#", self._handle_input)
        
    async def _handle_input(self, message):
        # Process input messages
        pass
        
    async def process_message(self, topic, message):
        # Override to add custom processing
        if await super().process_message(topic, message):
            # Add custom logic here
            return True
        return False
```

### Implementing a New Messaging Provider

To add support for a new messaging system, implement the `MessagingProvider` interface:

```python
from framework.messaging.provider import MessagingProvider

class CustomMessagingProvider(MessagingProvider):
    def __init__(self, agent_id, config):
        super().__init__(agent_id)
        # Initialize provider-specific resources
        
    async def connect(self) -> bool:
        # Establish connection to messaging system
        pass
        
    async def disconnect(self) -> bool:
        # Close connection to messaging system
        pass
        
    async def publish(self, topic, message) -> bool:
        # Publish a message to the topic
        pass
        
    async def subscribe(self, topic, handler) -> bool:
        # Subscribe to the topic
        pass
        
    async def unsubscribe(self, topic) -> bool:
        # Unsubscribe from the topic
        pass
        
    async def authenticate(self, permissions) -> bool:
        # Authenticate with the messaging system
        pass
```

To register your provider, modify the factory function in `framework/messaging/factory.py`.

### Implementing a New LLM Provider

To add support for a new LLM service, implement the `LLMProvider` interface:

```python
from framework.llm.llm_provider import LLMProvider

class CustomLLMProvider(LLMProvider):
    def __init__(self, config):
        super().__init__(config)
        self.provider_name = "custom"
        # Initialize provider-specific resources
        
    async def generate(self, prompt, system=None, max_tokens=None, temperature=None):
        # Generate text from the LLM
        pass
        
    async def chat(self, messages, system=None, max_tokens=None, temperature=None):
        # Generate a chat response
        pass
        
    async def embed(self, text):
        # Generate embeddings
        pass
        
    def get_token_count(self, text):
        # Estimate token count
        pass
```

To register your provider, modify the factory function in `framework/llm/factory.py`.

### Adding Authentication Methods

To add a new authentication method, implement the `AuthProvider` interface:

```python
from framework.auth.auth_provider import AuthProvider

class CustomAuthProvider(AuthProvider):
    def __init__(self, config):
        super().__init__(config)
        # Initialize provider-specific resources
        
    async def authenticate(self):
        # Authenticate with the service
        pass
        
    def is_authenticated(self):
        # Check if authenticated
        pass
        
    def get_token(self):
        # Get the current token
        pass
        
    def get_headers(self):
        # Get headers for API requests
        pass
```

## Authentication System

### SSH Key Authentication Flow

The SSH key authentication process follows these steps:

1. **Challenge Request**: Agent requests a challenge from the server:
   ```
   POST /api/v1/auth/challenge
   {
     "agent_id": "agent-123"
   }
   ```

2. **Challenge Response**: Server returns a random challenge:
   ```
   {
     "challenge": "random_challenge_string",
     "expires_at": "2023-05-10T12:30:00Z"
   }
   ```

3. **Challenge Signature**: Agent signs the challenge with its private key:
   ```python
   # Create digest
   digest = hashes.Hash(hashes.SHA256())
   digest.update(challenge.encode('utf-8'))
   digest_bytes = digest.finalize()
   
   # Sign the digest
   signature = private_key.sign(
       digest_bytes,
       padding.PKCS1v15(),
       Prehashed(hashes.SHA256())
   )
   
   # Encode signature
   signature_b64 = base64.b64encode(signature).decode()
   ```

4. **Verification Request**: Agent sends the signature to the server:
   ```
   POST /api/v1/auth/verify
   {
     "tenant_id": "tenant-456",
     "key_id": "key-789",
     "challenge": "random_challenge_string",
     "response": "base64_encoded_signature",
     "agent_id": "agent-123"
   }
   ```

5. **Token Issuance**: Server verifies signature and issues a JWT token:
   ```
   {
     "valid": true,
     "token": "jwt_token_string"
   }
   ```

### JWT Token Format

The JWT token contains claims that identify the agent and its permissions:

```json
{
  "sub": "agent-123",
  "iss": "artcafe.ai",
  "aud": "artcafe.ai",
  "iat": 1683720000,
  "exp": 1683723600,
  "tenant_id": "tenant-456",
  "agent_type": "worker",
  "permissions": [
    "subscribe:agents/worker/agent-123/#",
    "publish:agents/worker/agent-123/#",
    "subscribe:agents/broadcast/#"
  ]
}
```

## Messaging System

### Topic Patterns and Wildcards

The messaging system supports wildcards in topic subscriptions:

- **+**: Matches exactly one topic level
- **#**: Matches zero or more topic levels

Examples:
- `agents/status/+`: Matches `agents/status/agent-123` but not `agents/status/agent-123/detail`
- `agents/worker/#`: Matches any topic that starts with `agents/worker/`

### Message Structure

All messages follow a standard structure:

```json
{
  "type": "message",
  "id": "msg-uuid-1234",
  "topic": "data/results",
  "data": {
    // Message-specific payload
  },
  "timestamp": "2023-05-10T12:00:00Z"
}
```

Special message types:
- `heartbeat`: Periodic message to indicate agent is alive
- `command`: Instruction for an agent to perform an action
- `response`: Reply to a command
- `status`: Agent status update
- `error`: Error notification

### Quality of Service (QoS)

The messaging system supports different quality of service levels:

- **QoS 0** (At most once): Message is sent once with no confirmation
- **QoS 1** (At least once): Message is sent until confirmation is received
- **QoS 2** (Exactly once): Full handshake ensures message is received exactly once

Configure the default QoS level in the agent configuration:

```yaml
messaging:
  default_qos: 1
```

## LLM Integration

### Provider Interface

All LLM providers implement the same interface for consistency:

```python
class LLMProvider:
    async def generate(self, prompt, system=None, max_tokens=None, temperature=None):
        """Generate text completion."""
        pass
        
    async def chat(self, messages, system=None, max_tokens=None, temperature=None):
        """Generate chat completion."""
        pass
        
    async def embed(self, text):
        """Generate text embeddings."""
        pass
        
    def get_token_count(self, text):
        """Estimate token count."""
        pass
```

### Response Format

All providers return responses in a standardized format:

```json
{
  "provider": "anthropic",
  "model": "claude-3-opus-20240229",
  "success": true,
  "data": {
    "content": "The generated text response",
    "usage": {
      "input_tokens": 10,
      "output_tokens": 50,
      "total_tokens": 60
    },
    "id": "response-id",
    "metadata": {}
  }
}
```

### Error Handling

Providers handle errors and return standardized error responses:

```json
{
  "provider": "anthropic",
  "model": "claude-3-opus-20240229",
  "success": false,
  "error": "API rate limit exceeded",
  "data": {}
}
```

## Testing

### Unit Testing

The framework includes a comprehensive test suite. To run tests:

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_auth.py tests/test_messaging.py

# Run tests with coverage
pytest --cov=framework
```

### Writing Tests

When adding new features, include appropriate tests:

```python
# test_my_feature.py
import pytest
from framework.core.enhanced_agent import EnhancedAgent
from framework.messaging.memory_provider import MemoryMessagingProvider

class TestMyFeature:
    @pytest.fixture
    def agent(self):
        # Set up test agent with memory messaging provider
        config = {
            "messaging": {"provider": "memory"},
            "auth": {"agent_id": "test-agent", "tenant_id": "test-tenant"}
        }
        agent = EnhancedAgent(agent_id="test-agent", config=config)
        return agent
    
    async def test_agent_publishes_message(self, agent):
        # Initialize agent
        await agent.start()
        
        # Test publishing a message
        success = await agent.publish("test/topic", {"test": "data"})
        
        # Verify result
        assert success is True
        
        # Clean up
        await agent.stop()
```

### Mocking External Services

Use mocks for external services in tests:

```python
from unittest.mock import AsyncMock, patch

async def test_llm_integration(agent):
    # Mock LLM provider
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = {
        "provider": "test",
        "model": "test-model",
        "success": True,
        "data": {
            "content": "Test response",
            "usage": {"total_tokens": 5}
        }
    }
    
    # Patch the LLM provider
    with patch("framework.llm.factory.get_llm_provider", return_value=mock_llm):
        result = await agent.process_with_llm("Test prompt")
        assert "Test response" in result
        mock_llm.generate.assert_called_once()
```

## Contributing Guidelines

### Code Style

Follow these guidelines for code style:

- Use [Black](https://black.readthedocs.io/) for code formatting
- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines
- Add type hints to all function parameters and return values
- Use descriptive variable names and add docstrings to all functions and classes

### Pull Request Process

1. Fork the repository and create a feature branch
2. Implement your changes with appropriate tests
3. Update documentation to reflect your changes
4. Submit a pull request with a clear description of the changes
5. Address any feedback from code reviews

### Documentation

When adding new features, update the relevant documentation:

- Add detailed docstrings to all functions and classes
- Update the user guide and developer guide as appropriate
- Include example code for new features

### Testing Requirements

All pull requests should include:

- Unit tests for new functionality
- Integration tests for features that interact with external services
- Performance tests for performance-critical components

### Commit Message Format

Follow the conventional commits format for commit messages:

```
type(scope): brief description

Detailed description of the changes.
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks