# Changelog

All notable changes to the ArtCafe Agent Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-01-XX

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