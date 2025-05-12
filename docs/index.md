# ArtCafe.ai Agent Framework Documentation

Welcome to the ArtCafe.ai Agent Framework documentation. This framework provides a robust foundation for building intelligent agents that communicate and collaborate through a distributed messaging system, with full multi-tenant support and LLM integration.

## Documentation Sections

### User Guides

- [User Guide](user_guide.md) - Comprehensive guide for using the framework
- [Multi-Tenant Integration Guide](multi_tenant_guide.md) - Guide for multi-tenant deployment

### Developer Resources

- [Developer Guide](developer_guide.md) - In-depth technical information for developers
- [API Reference](api_reference.md) - Detailed API documentation

## Quick Links

- [GitHub Repository](https://github.com/artcafe-ai/agent-framework)
- [ArtCafe.ai Portal](https://portal.artcafe.ai)
- [Support](mailto:support@artcafe.ai)

## Getting Started

For a quick start, follow these steps:

1. Installation:
   ```bash
   git clone https://github.com/artcafe-ai/agent-framework.git
   cd agent-framework
   pip install -r requirements.txt
   ```

2. Setup:
   ```bash
   ./setup_agent.py --interactive
   ```

3. Running an example agent:
   ```bash
   python -m framework.examples.enhanced_runner --config ~/.artcafe/config.yaml
   ```

## Key Features

- **Multi-Tenant Support**: Secure tenant isolation and SSH key authentication
- **Flexible Messaging**: Topic-based messaging with various providers
- **LLM Integration**: Multiple LLM providers with a consistent interface
- **Web Portal Integration**: Seamless integration with the ArtCafe.ai portal

## Contributing

We welcome contributions to the Agent Framework! Please see the [CONTRIBUTING.md](https://github.com/artcafe-ai/agent-framework/blob/main/CONTRIBUTING.md) file for guidelines.