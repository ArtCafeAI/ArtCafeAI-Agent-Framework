#!/usr/bin/env python3

import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("AgentFramework.Core.ConfigLoader")

class ConfigLoader:
    """
    Configuration loader for the agent framework.
    
    Loads configuration from various sources in order of precedence:
    1. Command-line arguments
    2. Environment variables
    3. Configuration file
    4. Default values
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "api": {
            "endpoint": "https://api.artcafe.ai",
            "version": "v1",
            "websocket_endpoint": "wss://api.artcafe.ai/ws",
        },
        "auth": {
            "agent_id": "",
            "tenant_id": "",
            "ssh_key": {
                "private_key_path": "~/.ssh/artcafe_agent",
                "key_type": "agent"
            },
            "retry_attempts": 5,
            "retry_delay": 1000,
            "token_refresh_margin": 300
        },
        "messaging": {
            "provider": "memory",
            "heartbeat_interval": 30,
            "batch_size": 10,
            "message_ttl": 3600
        },
        "llm": {
            "provider": "anthropic",
            "model": "claude-3-opus-20240229",
            "api_key": "",
            "anthropic": {
                "api_endpoint": "https://api.anthropic.com",
                "max_tokens": 4096,
                "temperature": 0.7
            },
            "openai": {
                "api_endpoint": "https://api.openai.com",
                "model": "gpt-4",
                "max_tokens": 4096,
                "temperature": 0.7
            },
            "bedrock": {
                "region": "us-west-2",
                "model_id": "anthropic.claude-3-opus-20240229",
                "max_tokens": 4096,
                "temperature": 0.7
            },
            "local": {
                "endpoint": "http://localhost:8000",
                "model": "local-model"
            }
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "",
            "max_size": 10,
            "backup_count": 5
        },
        "security": {
            "validate_server_cert": True,
            "sensitive_keys": [
                "api_key",
                "private_key",
                "token",
                "password"
            ]
        },
        "resources": {
            "cpu_limit": 0,
            "memory_limit": 0,
            "storage_path": "~/.artcafe/storage"
        }
    }
    
    def __init__(self):
        """Initialize the configuration loader."""
        self.config = {}
    
    def load(self, args: Optional[Dict[str, Any]] = None, 
             env_prefix: str = "ARTCAFE_", 
             config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from various sources.
        
        Args:
            args: Command-line arguments as a dictionary
            env_prefix: Prefix for environment variables
            config_file: Path to configuration file
            
        Returns:
            Dict[str, Any]: Merged configuration
        """
        # Start with default config
        self.config = self._deep_copy(self.DEFAULT_CONFIG)
        
        # Load from config file
        if config_file:
            self._load_from_file(config_file)
        else:
            # Try standard locations
            config_locations = [
                os.path.join(os.getcwd(), "config.yaml"),
                os.path.join(os.getcwd(), "config.yml"),
                os.path.join(os.getcwd(), "config.json"),
                os.path.expanduser("~/.artcafe/config.yaml"),
                os.path.expanduser("~/.artcafe/config.yml"),
                os.path.expanduser("~/.artcafe/config.json"),
                "/etc/artcafe/config.yaml",
                "/etc/artcafe/config.yml",
                "/etc/artcafe/config.json"
            ]
            
            for location in config_locations:
                if os.path.exists(location):
                    self._load_from_file(location)
                    break
        
        # Load from environment variables
        self._load_from_env(env_prefix)
        
        # Load from command-line arguments
        if args:
            self._load_from_args(args)
        
        # Validate configuration
        self._validate_config()
        
        return self.config
    
    def _load_from_file(self, file_path: str) -> None:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file
        """
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith(('.yaml', '.yml')):
                    file_config = yaml.safe_load(f)
                elif file_path.endswith('.json'):
                    file_config = json.load(f)
                else:
                    logger.warning(f"Unsupported file format: {file_path}")
                    return
            
            # Merge with current config
            if file_config:
                self._deep_merge(self.config, file_config)
                
            logger.info(f"Loaded configuration from {file_path}")
            
        except Exception as e:
            logger.warning(f"Failed to load configuration from {file_path}: {str(e)}")
    
    def _load_from_env(self, prefix: str) -> None:
        """
        Load configuration from environment variables.
        
        Args:
            prefix: Prefix for environment variables
        """
        env_vars = {k: v for k, v in os.environ.items() if k.startswith(prefix)}
        
        for key, value in env_vars.items():
            # Remove prefix and split by underscore
            key = key[len(prefix):]
            parts = key.lower().split('_')
            
            # Parse value based on type
            typed_value = self._parse_value(value)
            
            # Navigate to the correct config location
            current = self.config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value
            current[parts[-1]] = typed_value
        
        if env_vars:
            logger.info(f"Loaded {len(env_vars)} configuration values from environment variables")
    
    def _load_from_args(self, args: Dict[str, Any]) -> None:
        """
        Load configuration from command-line arguments.
        
        Args:
            args: Command-line arguments as a dictionary
        """
        # Filter out None values
        filtered_args = {k: v for k, v in args.items() if v is not None}
        
        for key, value in filtered_args.items():
            # Convert keys like "api_endpoint" to nested dict structure
            if '_' in key:
                parts = key.split('_')
                
                # Navigate to the correct config location
                current = self.config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set the value
                current[parts[-1]] = value
            else:
                # Top-level keys
                self.config[key] = value
        
        if filtered_args:
            logger.info(f"Loaded {len(filtered_args)} configuration values from command-line arguments")
    
    def _parse_value(self, value: str) -> Any:
        """
        Parse a string value into the appropriate type.
        
        Args:
            value: String value to parse
            
        Returns:
            The parsed value
        """
        # Try to parse as JSON first
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # Check for boolean values
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        if value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # Check for numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
        """
        Recursively merge two dictionaries.
        
        Args:
            base: Base dictionary to merge into
            overlay: Dictionary to merge from
        """
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _deep_copy(self, obj: Any) -> Any:
        """
        Create a deep copy of a dictionary or list.
        
        Args:
            obj: Object to copy
            
        Returns:
            A deep copy of the object
        """
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(v) for v in obj]
        else:
            return obj
    
    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        # Check for required values
        if not self.config.get("api", {}).get("endpoint"):
            logger.warning("Missing API endpoint in configuration")
        
        # Check for sensitive values
        self._mask_sensitive_values()
    
    def _mask_sensitive_values(self) -> None:
        """Mask sensitive values in logs."""
        sensitive_keys = self.config.get("security", {}).get("sensitive_keys", [])
        
        def mask_dict(d: Dict[str, Any], keys: List[str]) -> None:
            for k, v in d.items():
                if k.lower() in keys and isinstance(v, str) and v:
                    logger.debug(f"Masking sensitive value for key: {k}")
                    d[k] = "********"
                elif isinstance(v, dict):
                    mask_dict(v, keys)
        
        # Create a copy for logging
        log_config = self._deep_copy(self.config)
        mask_dict(log_config, [k.lower() for k in sensitive_keys])
        
        # Log the configuration (without sensitive values)
        logger.debug(f"Loaded configuration: {json.dumps(log_config, indent=2)}")
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        Get the default configuration.
        
        Returns:
            Dict[str, Any]: Default configuration
        """
        return ConfigLoader._deep_copy(ConfigLoader, ConfigLoader.DEFAULT_CONFIG)