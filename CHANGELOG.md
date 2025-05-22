# Changelog

All notable changes to the ArtCafe Agent Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-01-22

### Added
- **SimpleAgent**: Minimal configuration agent for quick starts
- **AugmentedLLMAgent**: LLM-first agent following industry best practices
- **VerifiedAgent**: Agent with built-in verification and ground truth checks
- **BudgetAwareAgent**: Cost tracking and budget enforcement for autonomous agents
- **Workflow Patterns**: Pre-built implementations for chaining, routing, parallelization
- Factory functions: `create_agent()` and `create_llm_agent()` for easy instantiation
- Decorator-based message handlers with `@agent.on_message()`
- Input/output verification decorators: `@verify_input()` and `@verify_output()`
- Cost tracking with multiple budget units (tokens, requests, dollars)
- Circuit breaker pattern for error handling

### Improved
- Simplified getting started experience
- Better alignment with modern agent building best practices
- Enhanced documentation with simpler examples
- More intuitive API for common use cases

## [0.3.0] - 2025-01-15

### Added
- Initial public release of the ArtCafe Agent Framework
- Core agent framework with BaseAgent and EnhancedAgent classes
- Multiple messaging providers (memory, AWS IoT, ArtCafe PubSub)
- LLM integration with support for Anthropic, OpenAI, and Bedrock
- Tool framework with decorator-based tool creation
- Event loop architecture for agent-LLM interactions
- Conversation management with context window handling
- MCP (Model Context Protocol) support
- Telemetry and tracing capabilities
- SSH-based authentication system
- Configuration management with YAML support
- Comprehensive documentation and examples
- Test suite with pytest
- Package distribution files (pyproject.toml)

### Security
- No hardcoded credentials or sensitive information
- Proper gitignore for security-sensitive files
- SSH key authentication for secure agent communication

### Development
- Code of Conduct
- Contributing guidelines
- MIT license
- Development dependencies and tooling setup