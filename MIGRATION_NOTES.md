# Migration Notes - Agent Framework v0.4.2

## Summary of Changes

This document summarizes the changes made to align the agent-framework with the working artcafe-getting-started implementation.

### 1. SimpleAgent Rewrite

The `SimpleAgent` class has been completely rewritten to match the working implementation:

**Before:**
- Inherited from EnhancedAgent
- Used complex configuration system
- Had JWT token handling
- Producer/consumer patterns

**After:**
- Standalone implementation
- WebSocket connection with challenge-response authentication
- Uses PKCS1v15 padding (not PSS) for signature
- Authentication via URL parameters
- Decorator-based message handlers
- True peer-based messaging

### 2. Authentication Flow

The new authentication flow matches the working implementation:
1. Get challenge from REST API: `GET /api/v1/agents/{agent_id}/challenge`
2. Sign challenge with private key using PKCS1v15 padding
3. Connect to WebSocket with auth params in URL: `/api/v1/ws/agent/{agent_id}?agent_id=...&challenge=...&signature=...`
4. No JWT tokens are used

### 3. Message Handling

**Before:**
```python
async def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
    # Complex processing with parent class involvement
```

**After:**
```python
@agent.on_message("channel_name")
async def handler(subject: str, data: Dict[str, Any]):
    # Simple, direct handling
    # Each agent decides independently whether to respond
```

### 4. Peer-Based Architecture

- All agents are equal peers
- Every agent on a channel receives all messages
- No producer/consumer hierarchy
- Agents independently decide how to process messages

### 5. Example Updates

Updated examples to use the new SimpleAgent:
- `simple_hello_world.py` - Basic agent with message handlers
- `peer_agents_example.py` - Multiple peer agents collaborating
- `basic_agent.py` - New minimal example

### 6. Configuration

**Before:**
- Complex YAML configuration files
- Multiple messaging providers
- JWT configuration

**After:**
- Simple constructor parameters
- Environment variables for credentials
- Direct WebSocket connection

### 7. Dependencies

The framework now requires:
- `websockets>=10.4` for WebSocket connections
- `aiohttp>=3.8.0` for HTTP requests
- `cryptography>=38.0.0` for SSH key operations

### 8. Breaking Changes

1. SimpleAgent no longer inherits from EnhancedAgent
2. No JWT token support
3. No producer/consumer patterns
4. Authentication is done via challenge-response, not JWT
5. Message handlers receive (subject, data) instead of just (message)

### 9. Migration Guide

To migrate existing agents:

1. Replace inheritance:
   ```python
   # Before
   class MyAgent(EnhancedAgent):
   
   # After
   agent = SimpleAgent(...)
   ```

2. Update message handlers:
   ```python
   # Before
   async def process_message(self, topic, message):
   
   # After
   @agent.on_message("topic")
   async def handler(subject, data):
   ```

3. Remove JWT configuration and use SSH keys
4. Update to peer-based logic (no producer/consumer roles)

### 10. Coexistence

The framework maintains both implementations:
- `SimpleAgent` - The new implementation matching artcafe-getting-started
- `SimplifiedAgent` - Previous implementation (kept for compatibility)
- `EnhancedAgent` - Original base class (kept for compatibility)

Choose SimpleAgent for new projects connecting to the ArtCafe platform.