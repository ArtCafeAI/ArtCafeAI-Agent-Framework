# Changelog

All notable changes to the ArtCafe Agent Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.3] - 2025-06-08

### Added
- **NKey Authentication**: Direct NATS connection using Ed25519 NKeys for NATSAgent
- **Direct NATS Connection**: NATSAgent now connects directly to NATS without WebSocket layer
- **Automatic Tenant Prefixing**: All subjects automatically prefixed with tenant ID
- **Built-in Heartbeat**: Automatic heartbeat support for connection health

### Changed
- **NATSAgent**: Rewritten to use direct NATS connection with NKey authentication
- **Dependencies**: Added nats-py>=2.5.0 as a core dependency
- **Performance**: Improved latency by removing WebSocket layer for NATS agents

### Fixed
- Alignment with cyberforge-demo pattern for consistent agent implementation

## [0.4.2] - 2025-05-26

### Added
- **SimplifiedAgent**: New agent class with decorator-based message handling and sensible defaults
- **Peer-Based Architecture**: Examples showing true peer-to-peer agent communication
- **Collaborative Examples**: Agents working together without producer/consumer patterns
- **SSH Authentication**: Secure WebSocket authentication using SSH keys
- **Configuration Templates**: Pre-built YAML configs for common agent patterns
- **Quick Start Guide**: 5-minute getting started documentation
- **CONTRIBUTING.md**: Comprehensive contribution guidelines

### Changed
- **Architecture Shift**: Moved from producer/consumer to peer-based messaging
- **Terminology Update**: `tenant_id` → `organization_id` to match UI terminology
- **Improved Examples**: Added environment variable support and better documentation
- **Security Fix**: Replaced unsafe `eval()` with proper expression parsing
- **Version Consistency**: All version numbers now consistently 0.4.2
- **Code Quality**: Replaced print statements with proper logging

### Fixed
- Security vulnerability in calculator example using `eval()`
- Version inconsistencies across setup.py, pyproject.toml, and __init__.py
- Missing CONTRIBUTING.md file reference
- Print statements in core modules now use logging

### Removed
- JWT authentication - now using SSH keys exclusively
- Producer/consumer pattern examples - replaced with peer-based examples
- Incomplete knowledge provider implementations (moved to roadmap)

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