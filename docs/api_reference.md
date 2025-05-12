# ArtCafe.ai Agent Framework API Reference

This document provides detailed API reference for the ArtCafe.ai Agent Framework's core components and interfaces.

## Table of Contents

1. [Core Components](#core-components)
   - [BaseAgent](#baseagent)
   - [EnhancedAgent](#enhancedagent)
   - [ConfigLoader](#configloader)
2. [Authentication](#authentication)
   - [AuthProvider](#authprovider)
   - [SSHAuthProvider](#sshauthprovider)
3. [Messaging](#messaging)
   - [MessagingInterface](#messaginginterface)
   - [MessagingProvider](#messagingprovider)
   - [ArtCafePubSubProvider](#artcafepubsubprovider)
   - [MemoryProvider](#memoryprovider)
4. [LLM Integration](#llm-integration)
   - [LLMProvider](#llmprovider)
   - [AnthropicProvider](#anthropicprovider)
   - [Factory Functions](#factory-functions)
5. [Utility Functions](#utility-functions)

---

## Core Components

### BaseAgent

Abstract base class for all agents in the framework.

#### Constructor

```python
def __init__(self, agent_id: Optional[str] = None, agent_type: str = "base")
```

- **agent_id**: Unique identifier for this agent. If None, a UUID will be generated.
- **agent_type**: Type of agent, used for categorization and discovery.

#### Properties

- **agent_id** (str): Unique identifier for the agent
- **agent_type** (str): Type of agent
- **capabilities** (List[str]): List of capabilities this agent provides
- **status** (str): Current status of the agent (initialized, running, stopped, etc.)
- **logger** (Logger): Logger instance for this agent

#### Methods

```python
@abc.abstractmethod
def start(self) -> bool
```
Start the agent, initializing resources and subscribing to required topics.
- **Returns**: True if the agent was started successfully, False otherwise.

```python
@abc.abstractmethod
def stop(self) -> bool
```
Stop the agent, cleaning up resources and unsubscribing from topics.
- **Returns**: True if the agent was stopped successfully, False otherwise.

```python
@abc.abstractmethod
def process_message(self, topic: str, message: Dict[str, Any]) -> bool
```
Process a message received from a topic.
- **topic**: The topic the message was received on.
- **message**: The message data as a dictionary.
- **Returns**: True if the message was processed successfully, False otherwise.

```python
def register_handler(self, topic_pattern: str, handler: Callable[[Dict[str, Any]], None]) -> None
```
Register a handler for a specific topic pattern.
- **topic_pattern**: The topic pattern to handle (may include wildcards)
- **handler**: The callback function to invoke when a message is received on this topic

```python
def get_capabilities(self) -> List[str]
```
Get the capabilities this agent provides.
- **Returns**: List of capability strings

```python
def get_status(self) -> Dict[str, Any]
```
Get detailed status information about this agent.
- **Returns**: Status dictionary including status, metrics, etc.

```python
def add_capability(self, capability: str) -> None
```
Add a capability to this agent.
- **capability**: The capability string to add

```python
def remove_capability(self, capability: str) -> None
```
Remove a capability from this agent.
- **capability**: The capability string to remove

### EnhancedAgent

Enhanced agent implementation with integrated messaging and configuration.

#### Constructor

```python
def __init__(self, 
             agent_id: Optional[str] = None, 
             agent_type: str = "enhanced",
             config: Optional[Dict[str, Any]] = None,
             permissions: Optional[List[str]] = None)
```

- **agent_id**: Unique identifier for this agent. If None, a UUID will be generated.
- **agent_type**: Type of agent, used for categorization and discovery.
- **config**: Configuration for this agent, or None to use defaults
- **permissions**: Messaging permissions to request, or None for defaults

#### Properties

- **config** (Dict[str, Any]): Configuration for this agent
- **messaging** (MessagingInterface): Messaging interface for communication
- **subscriptions** (Dict[str, Callable]): Map of topic patterns to handler functions
- **resource_authorizations** (Dict[str, List[str]]): Map of resource types to allowed actions

#### Methods

```python
async def start(self) -> bool
```
Start the agent, initializing resources and subscribing to required topics.
- **Returns**: True if the agent was started successfully, False otherwise.

```python
async def stop(self) -> bool
```
Stop the agent, cleaning up resources and unsubscribing from topics.
- **Returns**: True if the agent was stopped successfully, False otherwise.

```python
async def process_message(self, topic: str, message: Dict[str, Any]) -> bool
```
Process a message received from a topic.
- **topic**: The topic the message was received on.
- **message**: The message data as a dictionary.
- **Returns**: True if the message was processed successfully, False otherwise.

```python
async def subscribe(self, topic: str, handler: Optional[Callable] = None) -> bool
```
Subscribe to a topic with a handler function.
- **topic**: The topic to subscribe to
- **handler**: Function to call when a message is received, or None to use process_message
- **Returns**: True if the subscription was successful, False otherwise

```python
async def unsubscribe(self, topic: str) -> bool
```
Unsubscribe from a topic.
- **topic**: The topic to unsubscribe from
- **Returns**: True if the unsubscription was successful, False otherwise

```python
async def publish(self, topic: str, message: Dict[str, Any]) -> bool
```
Publish a message to a topic.
- **topic**: The topic to publish to
- **message**: The message to publish
- **Returns**: True if the message was published successfully, False otherwise

```python
def authorize_resource(self, resource_type: str, resource_id: str, action: str) -> bool
```
Check if the agent is authorized to perform an action on a resource.
- **resource_type**: Type of resource (e.g., 'finding', 'alert')
- **resource_id**: ID of the resource
- **action**: Action to perform (e.g., 'read', 'write')
- **Returns**: True if the action is authorized, False otherwise

```python
def add_resource_authorization(self, resource_type: str, actions: List[str]) -> None
```
Add authorization for actions on a resource type.
- **resource_type**: Type of resource (e.g., 'finding', 'alert')
- **actions**: List of actions to allow (e.g., ['read', 'write'])

```python
def remove_resource_authorization(self, resource_type: str, actions: Optional[List[str]] = None) -> None
```
Remove authorization for actions on a resource type.
- **resource_type**: Type of resource (e.g., 'finding', 'alert')
- **actions**: List of actions to remove, or None to remove all

```python
async def run(self) -> None
```
Main processing loop for the agent.
This method can be overridden by subclasses to implement custom behavior.

### ConfigLoader

Configuration loader for the agent framework.

#### Constructor

```python
def __init__(self)
```

#### Methods

```python
def load(self, args: Optional[Dict[str, Any]] = None, 
         env_prefix: str = "ARTCAFE_", 
         config_file: Optional[str] = None) -> Dict[str, Any]
```
Load configuration from various sources.
- **args**: Command-line arguments as a dictionary
- **env_prefix**: Prefix for environment variables
- **config_file**: Path to configuration file
- **Returns**: Merged configuration

```python
@staticmethod
def get_default_config() -> Dict[str, Any]
```
Get the default configuration.
- **Returns**: Default configuration

---

## Authentication

### AuthProvider

Abstract base class for authentication providers.

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```
- **config**: Configuration dictionary for the provider

#### Methods

```python
@abc.abstractmethod
async def authenticate(self) -> Tuple[bool, Optional[str]]
```
Authenticate with the service.
- **Returns**: Tuple of (success, error_message)

```python
@abc.abstractmethod
def is_authenticated(self) -> bool
```
Check if the provider is authenticated.
- **Returns**: True if authenticated, False otherwise

```python
@abc.abstractmethod
def get_token(self) -> Optional[str]
```
Get the current authentication token.
- **Returns**: Current token if authenticated, None otherwise

```python
@abc.abstractmethod
def get_headers(self) -> Dict[str, str]
```
Get headers for API requests.
- **Returns**: Headers containing authentication token and tenant ID

### SSHAuthProvider

SSH key-based authentication provider for ArtCafe.ai PubSub service.

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```
- **config**: Configuration dictionary containing auth settings

#### Properties

- **private_key_path** (str): Path to SSH private key
- **key_type** (str): Type of SSH key (agent, access, deployment)
- **api_endpoint** (str): API endpoint for ArtCafe.ai
- **agent_id** (str): Agent ID for authentication
- **tenant_id** (str): Tenant ID for authentication
- **jwt_token** (str): JWT token received after authentication
- **jwt_expires_at** (datetime): Expiration time for JWT token
- **key_id** (str): ID of the SSH key in ArtCafe.ai

#### Methods

```python
async def authenticate(self) -> Tuple[bool, Optional[str]]
```
Authenticate with the ArtCafe.ai platform using SSH key.
- **Returns**: Tuple of (success, error_message)

```python
def is_authenticated(self) -> bool
```
Check if the provider is authenticated with a valid token.
- **Returns**: True if authenticated with a valid token, False otherwise

```python
def get_token(self) -> Optional[str]
```
Get the current authentication token.
- **Returns**: Current token if authenticated, None otherwise

```python
def get_headers(self) -> Dict[str, str]
```
Get headers for API requests.
- **Returns**: Headers containing authentication token and tenant ID

---

## Messaging

### MessagingInterface

Abstract interface for messaging operations.

#### Methods

```python
@abc.abstractmethod
async def publish(self, topic: str, message: Dict[str, Any]) -> bool
```
Publish a message to a topic.
- **topic**: The topic to publish to
- **message**: The message to publish
- **Returns**: True if the message was published successfully, False otherwise

```python
@abc.abstractmethod
async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> bool
```
Subscribe to a topic with a handler function.
- **topic**: The topic to subscribe to
- **handler**: Function to call when a message is received
- **Returns**: True if the subscription was successful, False otherwise

```python
@abc.abstractmethod
async def unsubscribe(self, topic: str) -> bool
```
Unsubscribe from a topic.
- **topic**: The topic to unsubscribe from
- **Returns**: True if the unsubscription was successful, False otherwise

```python
@abc.abstractmethod
async def authenticate(self, permissions: List[str]) -> bool
```
Authenticate with the messaging system.
- **permissions**: List of permission strings to request
- **Returns**: True if authentication successful, False otherwise

### MessagingProvider

Abstract base class for messaging providers.

#### Constructor

```python
def __init__(self, agent_id: str)
```
- **agent_id**: Unique identifier for the agent

#### Properties

- **agent_id** (str): Agent ID for this messaging provider

#### Methods

```python
@abc.abstractmethod
async def publish(self, topic: str, message: Dict[str, Any]) -> bool
```
Publish a message to a topic.
- **topic**: The topic to publish to
- **message**: The message to publish
- **Returns**: True if the message was published successfully, False otherwise

```python
@abc.abstractmethod
async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> bool
```
Subscribe to a topic with a handler function.
- **topic**: The topic to subscribe to
- **handler**: Function to call when a message is received
- **Returns**: True if the subscription was successful, False otherwise

```python
@abc.abstractmethod
async def unsubscribe(self, topic: str) -> bool
```
Unsubscribe from a topic.
- **topic**: The topic to unsubscribe from
- **Returns**: True if the unsubscription was successful, False otherwise

```python
@abc.abstractmethod
async def authenticate(self, permissions: List[str]) -> bool
```
Authenticate with the messaging system.
- **permissions**: List of permission strings to request
- **Returns**: True if authentication successful, False otherwise

```python
@abc.abstractmethod
async def start(self) -> bool
```
Start the messaging provider.
- **Returns**: True if started successfully, False otherwise

```python
@abc.abstractmethod
async def stop(self) -> bool
```
Stop the messaging provider.
- **Returns**: True if stopped successfully, False otherwise

### ArtCafePubSubProvider

Messaging provider implementation using ArtCafe.ai PubSub service.

#### Constructor

```python
def __init__(self, agent_id: str, config: Dict[str, Any])
```
- **agent_id**: Unique identifier for the agent
- **config**: Configuration dictionary

#### Properties

- **config** (Dict[str, Any]): Configuration dictionary
- **api_endpoint** (str): API endpoint for ArtCafe.ai
- **ws_endpoint** (str): WebSocket endpoint for ArtCafe.ai
- **heartbeat_interval** (int): Seconds between heartbeats
- **auth_provider** (SSHAuthProvider): Authentication provider
- **ws** (WebSocket): WebSocket connection
- **ws_connected** (bool): Whether the WebSocket is connected
- **running** (bool): Whether the provider is running
- **topic_handlers** (Dict[str, List[Callable]]): Topic handlers

#### Methods

```python
async def connect(self) -> bool
```
Connect to the ArtCafe PubSub WebSocket server.
- **Returns**: True if connection successful, False otherwise

```python
async def disconnect(self) -> bool
```
Disconnect from the WebSocket server.
- **Returns**: True if disconnection successful, False otherwise

```python
async def publish(self, topic: str, message: Dict[str, Any]) -> bool
```
Publish a message to a topic.
- **topic**: The topic to publish to
- **message**: The message to publish
- **Returns**: True if the message was published successfully, False otherwise

```python
async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> bool
```
Subscribe to a topic with a handler function.
- **topic**: The topic to subscribe to
- **handler**: Function to call when a message is received
- **Returns**: True if the subscription was successful, False otherwise

```python
async def unsubscribe(self, topic: str) -> bool
```
Unsubscribe from a topic.
- **topic**: The topic to unsubscribe from
- **Returns**: True if the unsubscription was successful, False otherwise

```python
async def authenticate(self, permissions: List[str]) -> bool
```
Authenticate with the messaging system.
- **permissions**: List of permission strings to request
- **Returns**: True if authentication successful, False otherwise

```python
async def start(self) -> bool
```
Start the messaging provider.
- **Returns**: True if started successfully, False otherwise

```python
async def stop(self) -> bool
```
Stop the messaging provider.
- **Returns**: True if stopped successfully, False otherwise

### MemoryProvider

In-memory messaging provider for testing and development.

#### Constructor

```python
def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None)
```
- **agent_id**: Unique identifier for the agent
- **config**: Optional configuration dictionary

#### Properties

- **subscriptions** (Dict[str, List[Callable]]): Topic subscriptions
- **messages** (List[Dict[str, Any]]): Message history
- **running** (bool): Whether the provider is running

#### Methods

```python
async def publish(self, topic: str, message: Dict[str, Any]) -> bool
```
Publish a message to a topic.
- **topic**: The topic to publish to
- **message**: The message to publish
- **Returns**: True if the message was published successfully, False otherwise

```python
async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> bool
```
Subscribe to a topic with a handler function.
- **topic**: The topic to subscribe to
- **handler**: Function to call when a message is received
- **Returns**: True if the subscription was successful, False otherwise

```python
async def unsubscribe(self, topic: str) -> bool
```
Unsubscribe from a topic.
- **topic**: The topic to unsubscribe from
- **Returns**: True if the unsubscription was successful, False otherwise

```python
async def authenticate(self, permissions: List[str]) -> bool
```
Authenticate with the messaging system. Always returns True for memory provider.
- **permissions**: List of permission strings to request
- **Returns**: True

```python
async def start(self) -> bool
```
Start the messaging provider.
- **Returns**: True

```python
async def stop(self) -> bool
```
Stop the messaging provider.
- **Returns**: True

```python
def get_messages_for_topic(self, topic: str) -> List[Dict[str, Any]]
```
Get all messages published to a specific topic.
- **topic**: Topic to filter messages by
- **Returns**: List of messages

---

## LLM Integration

### LLMProvider

Abstract base class for LLM providers.

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```
- **config**: Configuration dictionary for the provider

#### Properties

- **config** (Dict[str, Any]): Configuration dictionary
- **model** (str): Model identifier
- **provider_name** (str): Provider name

#### Methods

```python
@abc.abstractmethod
async def generate(self, 
                   prompt: str, 
                   system: Optional[str] = None, 
                   max_tokens: Optional[int] = None, 
                   temperature: Optional[float] = None, 
                   stop_sequences: Optional[List[str]] = None,
                   **kwargs) -> Dict[str, Any]
```
Generate text from the LLM.
- **prompt**: The user prompt to send to the LLM
- **system**: Optional system prompt to define context and behavior
- **max_tokens**: Maximum number of tokens to generate
- **temperature**: Sampling temperature (0-1)
- **stop_sequences**: List of strings that will stop generation if encountered
- **kwargs**: Additional provider-specific parameters
- **Returns**: Response containing generated text and metadata

```python
@abc.abstractmethod
async def chat(self, 
               messages: List[Dict[str, str]], 
               system: Optional[str] = None,
               max_tokens: Optional[int] = None, 
               temperature: Optional[float] = None, 
               stop_sequences: Optional[List[str]] = None,
               **kwargs) -> Dict[str, Any]
```
Generate a response to a chat conversation.
- **messages**: List of message objects with role and content fields
- **system**: Optional system message to define context and behavior
- **max_tokens**: Maximum number of tokens to generate
- **temperature**: Sampling temperature (0-1)
- **stop_sequences**: List of strings that will stop generation if encountered
- **kwargs**: Additional provider-specific parameters
- **Returns**: Response containing generated text and metadata

```python
@abc.abstractmethod
async def embed(self, 
                text: Union[str, List[str]], 
                **kwargs) -> Dict[str, Any]
```
Generate embeddings for text.
- **text**: Text or list of texts to embed
- **kwargs**: Additional provider-specific parameters
- **Returns**: Response containing embeddings and metadata

```python
@abc.abstractmethod
def get_token_count(self, text: str) -> int
```
Estimate the number of tokens in a text string.
- **text**: Text to count tokens for
- **Returns**: Estimated token count

```python
def format_json_response(self, 
                         data: Dict[str, Any], 
                         success: bool = True, 
                         error: Optional[str] = None) -> Dict[str, Any]
```
Format a response in a standard structure.
- **data**: The response data
- **success**: Whether the request was successful
- **error**: Error message if request failed
- **Returns**: Formatted response

### AnthropicProvider

LLM provider implementation for Anthropic Claude models.

#### Constructor

```python
def __init__(self, config: Dict[str, Any])
```
- **config**: Configuration dictionary for the provider

#### Properties

- **provider_name** (str): Provider name ("anthropic")
- **model** (str): Model identifier
- **api_key** (str): Anthropic API key
- **api_endpoint** (str): Anthropic API endpoint
- **default_max_tokens** (int): Default maximum tokens to generate
- **default_temperature** (float): Default sampling temperature
- **tokenizer** (Tokenizer): Token counter

#### Methods

```python
async def generate(self, 
                   prompt: str, 
                   system: Optional[str] = None, 
                   max_tokens: Optional[int] = None, 
                   temperature: Optional[float] = None, 
                   stop_sequences: Optional[List[str]] = None,
                   **kwargs) -> Dict[str, Any]
```
Generate text from Claude.
- **prompt**: The user prompt to send to Claude
- **system**: Optional system prompt to define context and behavior
- **max_tokens**: Maximum number of tokens to generate
- **temperature**: Sampling temperature (0-1)
- **stop_sequences**: List of strings that will stop generation if encountered
- **kwargs**: Additional Claude-specific parameters
- **Returns**: Response containing generated text and metadata

```python
async def chat(self, 
               messages: List[Dict[str, str]], 
               system: Optional[str] = None,
               max_tokens: Optional[int] = None, 
               temperature: Optional[float] = None, 
               stop_sequences: Optional[List[str]] = None,
               **kwargs) -> Dict[str, Any]
```
Generate a response to a chat conversation with Claude.
- **messages**: List of message objects with role and content fields
- **system**: Optional system message to define context and behavior
- **max_tokens**: Maximum number of tokens to generate
- **temperature**: Sampling temperature (0-1)
- **stop_sequences**: List of strings that will stop generation if encountered
- **kwargs**: Additional Claude-specific parameters
- **Returns**: Response containing generated text and metadata

```python
async def embed(self, 
                text: Union[str, List[str]], 
                **kwargs) -> Dict[str, Any]
```
Generate embeddings for text using Claude.
- **text**: Text or list of texts to embed
- **kwargs**: Additional Claude-specific parameters
- **Returns**: Response containing embeddings and metadata

```python
def get_token_count(self, text: str) -> int
```
Estimate the number of tokens in a text string.
- **text**: Text to count tokens for
- **Returns**: Estimated token count

### Factory Functions

```python
def get_llm_provider(config: Dict[str, Any]) -> LLMProvider
```
Factory function to create an appropriate LLM provider.
- **config**: LLM configuration dictionary
- **Returns**: Appropriate provider instance based on config
- **Raises**: ValueError if the requested provider is not available

```python
def register_provider(provider_name: str, provider_class) -> None
```
Register a custom LLM provider.
- **provider_name**: Name of the provider for configuration
- **provider_class**: Class implementing the LLMProvider interface

---

## Utility Functions

```python
def get_messaging(agent_id: str, config: Optional[Dict[str, Any]] = None) -> MessagingInterface
```
Get a messaging provider instance for the agent.
- **agent_id**: Unique identifier for the agent
- **config**: Optional configuration dictionary
- **Returns**: Messaging provider instance

```python
def configure_logging(config: Dict[str, Any]) -> None
```
Configure logging based on configuration.
- **config**: Logging configuration dictionary

```python
def generate_ssh_key(key_path: str, key_name: str, force: bool = False) -> str
```
Generate an SSH key for agent authentication.
- **key_path**: Directory to store the key
- **key_name**: Base name for the key files
- **force**: Whether to overwrite existing keys
- **Returns**: Path to the private key

```python
def create_config(config_path: str, agent_id: str, tenant_id: str, ssh_key_path: str, api_endpoint: str, llm_provider: str, force: bool = False) -> str
```
Create a configuration file for the agent.
- **config_path**: Path to write the configuration file
- **agent_id**: Agent ID from ArtCafe.ai
- **tenant_id**: Tenant ID from ArtCafe.ai
- **ssh_key_path**: Path to the SSH private key
- **api_endpoint**: API endpoint for ArtCafe.ai
- **llm_provider**: LLM provider to use
- **force**: Whether to overwrite existing config
- **Returns**: Path to the created config file