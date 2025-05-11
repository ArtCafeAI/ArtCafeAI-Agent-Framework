#!/usr/bin/env python3

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

logger = logging.getLogger("AgentFramework.Config")

class AgentConfig:
    """
    Configuration management for agents.
    
    This class provides functionality for loading, validating, and accessing
    configuration values for agents. It supports loading from files (JSON, YAML)
    or environment variables, with merging of multiple sources.
    
    Attributes:
        config (Dict[str, Any]): The configuration values
        defaults (Dict[str, Any]): Default configuration values
    """
    
    def __init__(self, 
                 config_files: Optional[List[str]] = None,
                 env_prefix: str = "AGENT_",
                 defaults: Optional[Dict[str, Any]] = None):
        """
        Initialize a new configuration manager.
        
        Args:
            config_files: Optional list of configuration file paths to load
            env_prefix: Prefix for environment variables to include
            defaults: Default configuration values
        """
        self.config = {}
        self.defaults = defaults or {}
        
        # Load configuration from files if provided
        if config_files:
            for file_path in config_files:
                self.load_file(file_path)
        
        # Load configuration from environment variables
        self.load_environment(env_prefix)
        
        # Apply defaults for missing values
        self._apply_defaults()
        
        logger.debug(f"Initialized configuration with {len(self.config)} values")
    
    def load_file(self, file_path: str) -> bool:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file (JSON or YAML)
            
        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.warning(f"Configuration file not found: {file_path}")
                return False
            
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    logger.warning(f"Unsupported configuration file format: {path.suffix}")
                    return False
            
            # Update configuration with loaded values
            self._update_config(config_data)
            logger.info(f"Loaded configuration from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading configuration from {file_path}: {str(e)}")
            return False
    
    def load_environment(self, prefix: str = "AGENT_") -> None:
        """
        Load configuration from environment variables.
        
        Environment variables with the specified prefix are added to the
        configuration. The prefix is removed, and the variable name is
        converted to lowercase and split by underscores to form a nested
        configuration structure.
        
        Example:
            AGENT_MESSAGING_PROVIDER=aws_iot becomes {"messaging": {"provider": "aws_iot"}}
        
        Args:
            prefix: Prefix for environment variables to include
        """
        env_config = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()
                
                # Split by underscores to create nested structure
                parts = config_key.split('_')
                
                # Build nested dictionaries
                current = env_config
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        # Try to convert value to appropriate type
                        try:
                            if value.lower() == 'true':
                                current[part] = True
                            elif value.lower() == 'false':
                                current[part] = False
                            elif value.isdigit():
                                current[part] = int(value)
                            elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                                current[part] = float(value)
                            else:
                                current[part] = value
                        except Exception:
                            current[part] = value
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
        
        # Update configuration with environment values
        self._update_config(env_config)
        
        logger.debug(f"Loaded {len(env_config)} configuration values from environment variables")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: The configuration key, can use dot notation for nested values
            default: Default value to return if key is not found
            
        Returns:
            The configuration value, or default if not found
        """
        parts = key.split('.')
        value = self.config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key, can use dot notation for nested values
            value: The value to set
        """
        parts = key.split('.')
        
        # Navigate to the nested dictionary where the value should be set
        current = self.config
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # If the path exists but is not a dictionary, convert it
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
    
    def merge(self, config: Dict[str, Any]) -> None:
        """
        Merge another configuration dictionary into this one.
        
        Args:
            config: The configuration dictionary to merge
        """
        self._update_config(config)
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the complete configuration as a dictionary.
        
        Returns:
            Dict[str, Any]: The configuration dictionary
        """
        return self.config.copy()
    
    def _update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update the configuration with new values, merging nested dictionaries.
        
        Args:
            new_config: The new configuration values to merge
        """
        def _recursive_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = _recursive_update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d
        
        _recursive_update(self.config, new_config)
    
    def _apply_defaults(self) -> None:
        """Apply default values for missing configuration entries."""
        def _recursive_defaults(defaults, config):
            for k, v in defaults.items():
                if k not in config:
                    config[k] = v
                elif isinstance(v, dict) and isinstance(config[k], dict):
                    _recursive_defaults(v, config[k])
        
        _recursive_defaults(self.defaults, self.config)

# Global default configuration values
DEFAULT_CONFIG = {
    "messaging": {
        "provider": "memory",
        "aws_iot": {
            "endpoint": None,
            "region": "us-east-1",
            "cert_path": None,
            "key_path": None,
            "ca_path": None
        }
    },
    "auth": {
        "provider": "simple",
        "jwt": {
            "secret": None,
            "expiration": 3600
        }
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "knowledge": {
        "provider": None,
        "neptune": {
            "endpoint": None,
            "port": 8182,
            "region": "us-east-1"
        },
        "opensearch": {
            "endpoint": None,
            "region": "us-east-1"
        }
    },
    "mcp": {
        "enabled": False,
        "endpoint": None,
        "api_key": None
    }
}