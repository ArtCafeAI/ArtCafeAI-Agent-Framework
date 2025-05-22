#!/usr/bin/env python3

import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

from .decorator import tool

logger = logging.getLogger("AgentFramework.Tools.Registry")

class ToolRegistry:
    """
    Registry for agent tools.
    
    This class manages tool registration, discovery, and lookup. It supports:
    - Registering tools decorated with @tool
    - Loading tools from Python modules
    - Looking up tools by name
    - Providing tool specifications for LLM consumption
    
    Tools can be registered directly or discovered from modules or directories.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self.tools: Dict[str, Callable] = {}
        self.tool_specs: Dict[str, Dict[str, Any]] = {}
        self.loaded_modules: Set[str] = set()
    
    def register_tool(self, tool_func: Callable) -> bool:
        """
        Register a tool function in the registry.
        
        Args:
            tool_func: Function decorated with @tool
            
        Returns:
            bool: True if registration was successful, False otherwise
            
        Raises:
            ValueError: If the tool is not properly decorated
        """
        if not hasattr(tool_func, "tool_spec"):
            raise ValueError(f"Function {tool_func.__name__} is not decorated with @tool")
        
        tool_spec = getattr(tool_func, "tool_spec")
        tool_name = tool_spec["name"]
        
        if tool_name in self.tools:
            logger.warning(f"Tool {tool_name} is already registered. Overwriting.")
        
        self.tools[tool_name] = tool_func
        self.tool_specs[tool_name] = tool_spec
        
        logger.info(f"Registered tool: {tool_name}")
        return True
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool by name.
        
        Args:
            tool_name: Name of the tool to unregister
            
        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            del self.tool_specs[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        else:
            logger.warning(f"Tool {tool_name} not found in registry.")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """
        Get a tool function by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            Optional[Callable]: The tool function if found, None otherwise
        """
        return self.tools.get(tool_name)
    
    def get_tool_spec(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a tool specification by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: The tool specification if found, None otherwise
        """
        return self.tool_specs.get(tool_name)
    
    def get_all_tool_specs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tool specifications.
        
        Returns:
            Dict[str, Dict[str, Any]]: All registered tool specifications
        """
        return self.tool_specs
    
    def load_from_module(self, module_name: str) -> List[str]:
        """
        Load tools from a Python module.
        
        Args:
            module_name: Name of the module to load tools from
            
        Returns:
            List[str]: Names of the tools loaded from the module
            
        Raises:
            ImportError: If the module cannot be imported
        """
        # Check if already loaded
        if module_name in self.loaded_modules:
            logger.debug(f"Module {module_name} already loaded.")
            return []
        
        try:
            # Import the module
            module = importlib.import_module(module_name)
            self.loaded_modules.add(module_name)
            
            # Find all tool functions in the module
            loaded_tools = []
            for name, obj in inspect.getmembers(module):
                if hasattr(obj, "tool_spec") and callable(obj):
                    self.register_tool(obj)
                    loaded_tools.append(obj.tool_spec["name"])
            
            logger.info(f"Loaded {len(loaded_tools)} tools from module {module_name}")
            return loaded_tools
            
        except ImportError as e:
            logger.error(f"Error importing module {module_name}: {str(e)}")
            raise
    
    def load_from_directory(self, directory: Union[str, Path], recursive: bool = True) -> List[str]:
        """
        Load tools from Python files in a directory.
        
        Args:
            directory: Path to the directory containing Python files
            recursive: Whether to search subdirectories
            
        Returns:
            List[str]: Names of the tools loaded from the directory
        """
        directory = Path(directory)
        loaded_tools = []
        
        if not directory.exists() or not directory.is_dir():
            logger.error(f"Directory {directory} does not exist or is not a directory.")
            return loaded_tools
        
        # Get Python files
        pattern = "**/*.py" if recursive else "*.py"
        for py_file in directory.glob(pattern):
            if py_file.name.startswith("_"):
                continue
                
            # Convert file path to module name
            relative_path = py_file.relative_to(directory)
            module_parts = list(relative_path.parts)
            module_parts[-1] = module_parts[-1].replace(".py", "")
            module_name = ".".join(module_parts)
            
            # Add directory to path temporarily
            sys.path.insert(0, str(directory))
            
            try:
                # Load tools from module
                tools = self.load_from_module(module_name)
                loaded_tools.extend(tools)
            except ImportError as e:
                logger.error(f"Error loading module {module_name}: {str(e)}")
            finally:
                # Remove directory from path
                sys.path.pop(0)
        
        logger.info(f"Loaded {len(loaded_tools)} tools from directory {directory}")
        return loaded_tools
    
    def create_tool_schemas_for_llm(self) -> List[Dict[str, Any]]:
        """
        Create tool schemas in the format expected by LLMs.
        
        Returns:
            List[Dict[str, Any]]: List of tool schemas formatted for LLM consumption
        """
        tool_schemas = []
        
        for tool_name, tool_spec in self.tool_specs.items():
            llm_tool_spec = {
                "name": tool_spec["name"],
                "description": tool_spec["description"],
                "parameters": tool_spec["schema"]
            }
            tool_schemas.append(llm_tool_spec)
        
        return tool_schemas