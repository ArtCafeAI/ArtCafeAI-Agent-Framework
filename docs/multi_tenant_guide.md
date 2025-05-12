# Multi-Tenant Integration Guide

This guide explains how to integrate the ArtCafe.ai Agent Framework with multi-tenant environments, focusing on authentication, tenant isolation, and web portal integration.

## Table of Contents

1. [Multi-Tenant Concepts](#multi-tenant-concepts)
2. [Tenant Registration](#tenant-registration)
3. [Agent Registration Process](#agent-registration-process)
4. [SSH Key Management](#ssh-key-management)
5. [Tenant Isolation](#tenant-isolation)
6. [Web Portal Integration](#web-portal-integration)
7. [Best Practices](#best-practices)

## Multi-Tenant Concepts

### What is Multi-Tenancy?

Multi-tenancy is an architecture where a single instance of software serves multiple customers (tenants). In the context of the ArtCafe.ai Agent Framework:

- Each **tenant** represents a separate organization or customer
- **Agents** belong to specific tenants and operate within their boundaries
- **Resources** (data, messages, configurations) are isolated between tenants
- **Authentication** ensures agents only access their tenant's resources

### Key Components

1. **Tenant**: An organization or customer using the platform
2. **Agent**: A service that performs tasks on behalf of a tenant
3. **SSH Key**: Secure credential for agent authentication
4. **JWT Token**: Time-limited access credential with tenant scope
5. **Topics**: Communication channels with tenant isolation

## Tenant Registration

### Registering a New Tenant

Before deploying agents, you need to register a tenant in the ArtCafe.ai platform:

1. Visit the [ArtCafe.ai Portal](https://portal.artcafe.ai)
2. Click "Register New Organization"
3. Provide organization details:
   - Organization name
   - Admin email address
   - Subscription plan
4. Verify the admin email address
5. Complete the onboarding process
6. Save the **Tenant ID** provided during registration

### Tenant Settings

After registration, configure tenant-specific settings:

1. Navigate to "Tenant Settings"
2. Set up tenant-wide policies:
   - Default agent permissions
   - Resource quotas
   - Allowed messaging topics
   - Messaging retention period
3. Invite team members (optional)
4. Configure billing information

## Agent Registration Process

### From Web Portal to Agent

The complete agent registration process involves both the web portal and the agent framework:

1. **Web Portal**: Register the agent and generate agent ID
2. **Local**: Generate SSH key pair
3. **Web Portal**: Register the public SSH key
4. **Local**: Configure agent with tenant ID, agent ID, and private key
5. **Runtime**: Agent authenticates using the SSH key
6. **Runtime**: Agent operates within tenant boundaries

### Registering an Agent

To register a new agent in the web portal:

1. Log in to the [ArtCafe.ai Portal](https://portal.artcafe.ai)
2. Navigate to "Agents" section
3. Click "Register New Agent"
4. Provide agent details:
   - Agent name
   - Description
   - Type (e.g., worker, processor, connector)
   - Capabilities (e.g., data processing, text analysis)
5. Submit to generate an **Agent ID**
6. Save the Agent ID for configuration

### Agent Configuration

After registering the agent in the portal, configure it locally:

1. Run the setup script with your tenant and agent IDs:
   ```bash
   ./setup_agent.py --agent-id "your-agent-id" --tenant-id "your-tenant-id"
   ```

2. Or create a configuration file manually:
   ```yaml
   # ~/.artcafe/config.yaml
   auth:
     agent_id: "your-agent-id"     # From ArtCafe.ai portal
     tenant_id: "your-tenant-id"   # From ArtCafe.ai portal
     ssh_key:
       private_key_path: "~/.ssh/artcafe_agent"
       key_type: "agent"
   
   api:
     endpoint: "https://api.artcafe.ai"
   ```

## SSH Key Management

### Key Generation

Generate an SSH key pair for agent authentication:

```bash
# Using the setup script
./setup_agent.py --generate-key

# Or manually
ssh-keygen -t rsa -b 4096 -f ~/.ssh/artcafe_agent
```

Key parameters:
- **Type**: RSA, ED25519
- **Bits**: 4096 (for RSA)
- **Format**: PEM
- **Passphrase**: Optional, but increases security

### Key Registration

Register the public key in the ArtCafe.ai portal:

1. Navigate to "SSH Keys" section
2. Click "Add New Key"
3. Provide key details:
   - Name (e.g., "Agent Key")
   - Key type: "Agent"
   - Associated agent: Select your agent ID
4. Paste the public key content:
   ```
   ssh-rsa AAAAB3NzaC1yc2EAAAADA...your key content...
   ```
5. Submit to register the key

### Key Rotation and Revocation

For security, rotate keys periodically and revoke compromised keys:

**Key Rotation**:
1. Generate a new key pair
2. Register the new public key in the portal
3. Update agent configuration to use the new private key
4. Test authentication with the new key
5. Revoke the old key in the portal

**Key Revocation**:
1. Navigate to the SSH key in the portal
2. Click "Revoke Key"
3. Provide reason for revocation
4. Confirm revocation

## Tenant Isolation

### Topic Isolation

The messaging system enforces tenant isolation through topic structure:

- **Tenant Prefix**: Topics include tenant ID prefix
- **Access Control**: Agents can only subscribe to their tenant's topics
- **Authentication**: JWT tokens include tenant scope

Example topic structure:
```
tenants/{tenant_id}/agents/{agent_id}/status
tenants/{tenant_id}/data/processing/input
tenants/{tenant_id}/data/processing/output
```

### Data Isolation

Ensure data isolation in your agent implementation:

```python
# Ensure tenant ID is included in messages
async def publish_result(self, result_data):
    message = {
        "tenant_id": self.tenant_id,  # Always include tenant ID
        "result": result_data,
        "timestamp": datetime.now().isoformat()
    }
    await self.publish(f"tenants/{self.tenant_id}/results", message)
```

### Resource Isolation

The framework enforces resource isolation:

1. **API Requests**: Include tenant ID in all requests
2. **Storage**: Use tenant-specific paths for any local storage
3. **Caching**: Segregate cache by tenant ID
4. **Rate Limiting**: Apply rate limits per tenant

Example resource isolation in code:
```python
# Use tenant-specific storage paths
storage_path = os.path.join(base_path, self.tenant_id, self.agent_id)
os.makedirs(storage_path, exist_ok=True)

# Tenant-specific cache keys
cache_key = f"{self.tenant_id}:{entity_id}"
```

## Web Portal Integration

### Agent Management UI

The ArtCafe.ai web portal provides a comprehensive agent management UI:

- **Dashboard**: Overall view of all agents and their status
- **Agent Details**: Detailed view of a specific agent
- **Configuration**: Update agent settings
- **Logs**: View agent logs
- **Metrics**: Monitor agent performance

### Monitoring Agents

Monitor your agents through the web portal:

1. Navigate to "Dashboard" section
2. View real-time agent status
3. Click on an agent to view details:
   - Current status
   - Message throughput
   - Error rate
   - Resource usage
   - Recent log entries

### Agent Controls

Control agents remotely through the web portal:

1. Navigate to an agent's detail page
2. Use action buttons:
   - Start/Stop: Control agent lifecycle
   - Restart: Restart a problematic agent
   - Configure: Update agent configuration
   - Send Command: Send a direct command to the agent

### Logs and Metrics

Access agent logs and metrics:

1. Navigate to an agent's "Logs" tab
2. Filter logs by:
   - Time range
   - Log level
   - Source component
   - Contains text
3. View metrics under the "Metrics" tab:
   - Message processing rate
   - Response time
   - Error rate
   - Resource usage

## Best Practices

### Security Recommendations

Follow these security best practices for multi-tenant deployments:

1. **Key Protection**:
   - Store private keys securely with restricted permissions
   - Use passphrase-protected keys for increased security
   - Never share private keys across agents

2. **Authentication**:
   - Implement key rotation every 30-90 days
   - Use the shortest viable JWT token lifetime
   - Validate all authentication responses

3. **Topic Security**:
   - Use specific topic permissions rather than wildcards
   - Subscribe only to required topics
   - Validate message origins

### Operational Recommendations

Ensure smooth operations with these practices:

1. **Agent Naming**:
   - Use descriptive, consistent naming conventions
   - Include purpose and environment in names
   - Example: `prod-data-processor-01`

2. **Configuration Management**:
   - Version control your configuration files
   - Use environment-specific config files
   - Avoid hardcoded credentials

3. **Monitoring**:
   - Set up alerts for agent failures
   - Monitor authentication failures
   - Track message processing rate and errors

### Scaling Recommendations

For larger deployments:

1. **Agent Groups**:
   - Organize agents into functional groups
   - Implement leader/follower patterns for group coordination
   - Configure shared group settings

2. **Load Distribution**:
   - Deploy multiple instances of high-traffic agents
   - Use sharding techniques for data processing
   - Implement back-pressure mechanisms

3. **Resource Optimization**:
   - Configure appropriate QoS levels for message types
   - Batch operations when possible
   - Cache frequently accessed data with tenant isolation