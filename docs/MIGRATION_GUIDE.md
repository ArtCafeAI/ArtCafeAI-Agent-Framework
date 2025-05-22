# Migration Guide

## Migrating to v0.4.0

Version 0.4.0 introduces several new agent types and patterns that make it easier to get started while maintaining backward compatibility with existing code.

### What's New

1. **SimpleAgent** - For quick prototypes and simple use cases
2. **AugmentedLLMAgent** - Start with LLM capabilities
3. **VerifiedAgent** - Built-in verification
4. **BudgetAwareAgent** - Cost tracking and limits
5. **Workflow patterns** - Pre-built coordination patterns

### Breaking Changes

None! Version 0.4.0 is fully backward compatible. All existing code will continue to work.

### Recommended Updates

While your existing code will work, we recommend adopting the new patterns for simpler code:

#### Before (v0.3.0):
```python
from framework import EnhancedAgent

class MyAgent(EnhancedAgent):
    def __init__(self):
        config = {
            "messaging": {"provider": "memory"},
            "agent": {"type": "custom"}
        }
        super().__init__(config=config)
        
    async def process_message(self, topic, message):
        if topic == "hello":
            await self.publish("response", {"text": "Hi!"})
        return await super().process_message(topic, message)
        
agent = MyAgent()
agent.start()
# Complex shutdown handling...
```

#### After (v0.4.0):
```python
from framework import create_agent

agent = create_agent("my-agent")

@agent.on_message("hello")
def handle_hello(message):
    return {"text": "Hi!"}

agent.run()  # Handles shutdown automatically
```

### New Best Practices

1. **Start Simple**: Use `SimpleAgent` for basic messaging needs
2. **LLM First**: Use `AugmentedLLMAgent` when you need AI capabilities
3. **Add Verification**: Use `VerifiedAgent` for production systems
4. **Track Costs**: Use `BudgetAwareAgent` for autonomous agents

### Getting Help

- Check the new examples in `examples/`
- See the updated README for quick start guides
- Review the API documentation in `docs/`

### Future Deprecations

No deprecations are planned. The framework is designed to support both simple and advanced use cases.