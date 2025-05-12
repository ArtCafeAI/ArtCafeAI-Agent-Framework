# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Framework Overview

The ArtCafe.ai Agent Framework is a modular framework for building intelligent agents that communicate through a pub/sub messaging system. The architecture consists of:

1. **Core Components**:
   - `BaseAgent`: Abstract base class defining agent lifecycle and messaging patterns
   - `EnhancedAgent`: Extends BaseAgent with integrated messaging, configuration, and advanced features
   - `MessagingInterface`: Abstraction layer for messaging operations

2. **Messaging System**:
   - Topic-based hierarchical messaging (agents/control, agents/status, agents/presence)
   - Provider pattern supporting different backends (in-memory, AWS IoT)
   - Permission model for controlling topic access
   - Agent discovery for finding agents with specific capabilities

3. **Agent Types**:
   - `TriageAgent`: Processes security findings, assesses severity, and routes high-priority findings
   - `InvestigativeAgent`: Analyzes security findings to determine legitimacy and generates reports

## Directory Structure

- `/agents/`: Contains agent implementations
- `/framework/`: Core framework code
  - `/auth/`: Authentication providers
  - `/core/`: Base agent classes and configuration
  - `/examples/`: Example agent implementations
  - `/messaging/`: Messaging providers and interfaces
- `/mocks/`: Mock data and services for testing
- `/utils/`: Utility functions for agents

## Run Commands

### Running the Example System

```bash
# Run the main example for 30 seconds
python3 main.py --run-time 30

# Run the enhanced example for 30 seconds
python3 -m framework.examples.enhanced_runner --run-time 30
```

### Creating and Running Custom Agents

To create a custom agent:
1. Extend `EnhancedAgent` class
2. Implement required methods (process_message, _setup_subscriptions)
3. Add capabilities and resource authorizations
4. Start and stop the agent properly

### Testing

When implementing new functionality:
1. Test with the in-memory messaging provider first
2. Verify proper topic subscriptions and message handling
3. Ensure proper agent lifecycle management (start/stop)
4. Test agent discovery and capabilities reporting

## Key Concepts

### Agent Lifecycle

Agents follow a specific lifecycle:
1. Initialization (STATUS_INITIALIZED)
2. Starting (STATUS_STARTING) - set up resources, subscribe to topics
3. Running (STATUS_RUNNING) - process messages, perform tasks
4. Stopping (STATUS_STOPPING) - clean up resources, unsubscribe
5. Stopped (STATUS_STOPPED)

### Messaging Patterns

- Control messages: `agents/control/{agent_id}/#`
- Status reports: `agents/status/{agent_id}`
- Presence announcements: `agents/presence/online`, `agents/presence/offline`
- Discovery: `agents/discovery/requests`, `agents/discovery/responses`
- Heartbeats: `agents/heartbeat`

### Resource Authorization

Agents can be authorized to perform specific actions on resources:
- Add authorization: `add_resource_authorization(resource_type, actions)`
- Check authorization: `authorize_resource(resource_type, resource_id, action)`
- Remove authorization: `remove_resource_authorization(resource_type, actions)`