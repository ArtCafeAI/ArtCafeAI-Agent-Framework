#!/usr/bin/env python3

import os
import sys
import argparse
import logging
import yaml
import json
import getpass
import subprocess
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AgentSetup")

def generate_ssh_key(key_path: str, key_name: str, force: bool = False) -> str:
    """
    Generate an SSH key for agent authentication.
    
    Args:
        key_path: Directory to store the key
        key_name: Base name for the key files
        force: Whether to overwrite existing keys
        
    Returns:
        str: Path to the private key
    """
    key_dir = os.path.expanduser(key_path)
    os.makedirs(key_dir, exist_ok=True)
    
    private_key_path = os.path.join(key_dir, key_name)
    public_key_path = f"{private_key_path}.pub"
    
    # Check if keys already exist
    if os.path.exists(private_key_path) and not force:
        logger.info(f"SSH key already exists at {private_key_path}")
        return private_key_path
    
    # Generate SSH key
    logger.info(f"Generating SSH key pair in {key_dir}")
    try:
        subprocess.run([
            "ssh-keygen", 
            "-t", "rsa", 
            "-b", "4096", 
            "-f", private_key_path,
            "-N", ""  # Empty passphrase
        ], check=True)
        
        logger.info(f"SSH key generated successfully:")
        logger.info(f"Private key: {private_key_path}")
        logger.info(f"Public key: {public_key_path}")
        
        # Read public key to display
        with open(public_key_path, "r") as f:
            public_key = f.read().strip()
        
        logger.info("Public key content (copy this to the ArtCafe.ai portal):")
        logger.info(public_key)
        
        return private_key_path
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating SSH key: {e}")
        sys.exit(1)

def create_config(
    config_path: str, 
    agent_id: str,
    tenant_id: str,
    ssh_key_path: str,
    api_endpoint: str,
    llm_provider: str,
    force: bool = False
) -> str:
    """
    Create a configuration file for the agent.
    
    Args:
        config_path: Path to write the configuration file
        agent_id: Agent ID from ArtCafe.ai
        tenant_id: Tenant ID from ArtCafe.ai
        ssh_key_path: Path to the SSH private key
        api_endpoint: API endpoint for ArtCafe.ai
        llm_provider: LLM provider to use
        force: Whether to overwrite existing config
        
    Returns:
        str: Path to the created config file
    """
    config_dir = os.path.dirname(os.path.expanduser(config_path))
    os.makedirs(config_dir, exist_ok=True)
    
    expanded_path = os.path.expanduser(config_path)
    
    # Check if config already exists
    if os.path.exists(expanded_path) and not force:
        logger.info(f"Configuration file already exists at {expanded_path}")
        return expanded_path
    
    # Create default config
    config = {
        "api": {
            "endpoint": api_endpoint,
            "version": "v1",
            "websocket_endpoint": api_endpoint.replace("http", "ws") + "/ws"
        },
        "auth": {
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "ssh_key": {
                "private_key_path": ssh_key_path,
                "key_type": "agent"
            }
        },
        "messaging": {
            "provider": "artcafe_pubsub",
            "heartbeat_interval": 30
        },
        "llm": {
            "provider": llm_provider,
            "model": "claude-3-opus-20240229" if llm_provider == "anthropic" else "gpt-4"
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    # Write config file
    with open(expanded_path, "w") as f:
        if expanded_path.endswith(".json"):
            json.dump(config, f, indent=2)
        else:
            yaml.dump(config, f, default_flow_style=False)
    
    logger.info(f"Configuration file created at {expanded_path}")
    return expanded_path

def prompt_for_info() -> dict:
    """
    Prompt the user for agent setup information.
    
    Returns:
        dict: User-provided setup information
    """
    print("\n=== ArtCafe.ai Agent Setup ===\n")
    print("This script will help you set up an agent for the ArtCafe.ai platform.")
    print("You'll need to provide some information from the ArtCafe.ai portal.\n")
    
    # Agent ID
    agent_id = input("Agent ID (from ArtCafe.ai portal): ")
    while not agent_id:
        print("Agent ID is required.")
        agent_id = input("Agent ID (from ArtCafe.ai portal): ")
    
    # Tenant ID
    tenant_id = input("Tenant ID (from ArtCafe.ai portal): ")
    while not tenant_id:
        print("Tenant ID is required.")
        tenant_id = input("Tenant ID (from ArtCafe.ai portal): ")
    
    # API Endpoint
    default_endpoint = "https://api.artcafe.ai"
    api_endpoint = input(f"API Endpoint [{default_endpoint}]: ")
    api_endpoint = api_endpoint or default_endpoint
    
    # SSH Key
    default_key_path = "~/.ssh"
    key_path = input(f"SSH Key Directory [{default_key_path}]: ")
    key_path = key_path or default_key_path
    
    default_key_name = "artcafe_agent"
    key_name = input(f"SSH Key Name [{default_key_name}]: ")
    key_name = key_name or default_key_name
    
    # LLM Provider
    valid_providers = ["anthropic", "openai", "bedrock", "local"]
    default_provider = "anthropic"
    
    llm_provider = input(f"LLM Provider {valid_providers} [{default_provider}]: ")
    llm_provider = llm_provider or default_provider
    
    while llm_provider not in valid_providers:
        print(f"Invalid provider. Please choose from: {', '.join(valid_providers)}")
        llm_provider = input(f"LLM Provider {valid_providers} [{default_provider}]: ")
        llm_provider = llm_provider or default_provider
    
    # API Key for LLM
    if llm_provider in ["anthropic", "openai"]:
        env_var = f"{llm_provider.upper()}_API_KEY"
        if os.environ.get(env_var):
            print(f"Using {env_var} from environment variables.")
        else:
            api_key = getpass.getpass(f"{llm_provider.capitalize()} API Key: ")
            os.environ[env_var] = api_key
    
    # Config path
    default_config_path = "~/.artcafe/config.yaml"
    config_path = input(f"Configuration File Path [{default_config_path}]: ")
    config_path = config_path or default_config_path
    
    return {
        "agent_id": agent_id,
        "tenant_id": tenant_id,
        "api_endpoint": api_endpoint,
        "key_path": key_path,
        "key_name": key_name,
        "llm_provider": llm_provider,
        "config_path": config_path
    }

def main():
    parser = argparse.ArgumentParser(description="Set up an ArtCafe.ai agent")
    
    parser.add_argument("--agent-id", help="Agent ID from ArtCafe.ai")
    parser.add_argument("--tenant-id", help="Tenant ID from ArtCafe.ai")
    parser.add_argument("--api-endpoint", default="https://api.artcafe.ai", help="API endpoint for ArtCafe.ai")
    parser.add_argument("--ssh-key-path", default="~/.ssh", help="Directory to store SSH key")
    parser.add_argument("--ssh-key-name", default="artcafe_agent", help="Name for the SSH key")
    parser.add_argument("--llm-provider", default="anthropic", choices=["anthropic", "openai", "bedrock", "local"], help="LLM provider to use")
    parser.add_argument("--config-path", default="~/.artcafe/config.yaml", help="Path to write the configuration file")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--interactive", action="store_true", help="Use interactive mode to prompt for values")
    
    args = parser.parse_args()
    
    if args.interactive or not (args.agent_id and args.tenant_id):
        info = prompt_for_info()
        
        # Use provided values or defaults from prompt
        agent_id = info["agent_id"]
        tenant_id = info["tenant_id"]
        api_endpoint = info["api_endpoint"]
        key_path = info["key_path"]
        key_name = info["key_name"]
        llm_provider = info["llm_provider"]
        config_path = info["config_path"]
    else:
        # Use command-line arguments
        agent_id = args.agent_id
        tenant_id = args.tenant_id
        api_endpoint = args.api_endpoint
        key_path = args.ssh_key_path
        key_name = args.ssh_key_name
        llm_provider = args.llm_provider
        config_path = args.config_path
    
    # Generate SSH key
    private_key_path = generate_ssh_key(key_path, key_name, args.force)
    
    # Create config file
    config_file = create_config(
        config_path,
        agent_id,
        tenant_id,
        private_key_path,
        api_endpoint,
        llm_provider,
        args.force
    )
    
    # Instructions for next steps
    print("\n=== Setup Complete ===")
    print(f"Agent configuration file: {config_file}")
    print(f"SSH private key: {private_key_path}")
    print(f"SSH public key: {private_key_path}.pub")
    print("\nNext Steps:")
    print("1. Copy the public key content to the ArtCafe.ai portal under SSH Keys")
    print("2. Associate the key with your agent")
    print(f"3. Run your agent: python -m framework.examples.enhanced_runner --config {config_file}")
    print("\nThanks for using ArtCafe.ai!")

if __name__ == "__main__":
    main()