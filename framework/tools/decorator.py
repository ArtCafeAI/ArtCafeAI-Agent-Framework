#!/usr/bin/env python3

import functools
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, get_type_hints

# Create logger
logger = logging.getLogger("AgentFramework.Tools.Decorator")

# Type variable for callable
T = TypeVar('T', bound=Callable)

def tool(func: Optional[Callable] = None, *, name: Optional[str] = None, description: Optional[str] = None) -> Callable:
    """
    Decorator to transform a Python function into an ArtCafe tool.
    
    This decorator extracts metadata from the function signature and docstring
    to create a standardized tool specification. The decorated function can be
    used both as a regular Python function and as an agent tool.
    
    Args:
        func: The function to decorate
        name: Optional custom name for the tool (defaults to function name)
        description: Optional custom description (defaults to function docstring)
    
    Returns:
        The decorated function with attached tool specification
        
    Example:
        @tool
        def fetch_weather(location: str, units: str = "metric") -> Dict[str, Any]:
            '''
            Get current weather for a location.
            
            Args:
                location: City name or geographic coordinates
                units: Unit system (metric, imperial)
                
            Returns:
                Weather information dictionary
            '''
            # Implementation...
            return weather_data
    """
    def decorator(fn: Callable) -> Callable:
        # Extract function metadata
        fn_name = name or fn.__name__
        fn_doc = inspect.getdoc(fn) or ""
        fn_signature = inspect.signature(fn)
        fn_type_hints = get_type_hints(fn)
        
        # Generate input schema
        parameters = {}
        required_params = []
        
        for param_name, param in fn_signature.parameters.items():
            # Skip special parameters
            if param_name in ('self', 'cls'):
                continue
                
            # Get parameter type and default
            param_type = fn_type_hints.get(param_name, str)
            has_default = param.default is not inspect.Parameter.empty
            
            # Map Python types to JSON schema types
            if param_type in (str, Optional[str]):
                param_schema = {"type": "string"}
            elif param_type in (int, Optional[int]):
                param_schema = {"type": "integer"}
            elif param_type in (float, Optional[float]):
                param_schema = {"type": "number"}
            elif param_type in (bool, Optional[bool]):
                param_schema = {"type": "boolean"}
            elif param_type in (list, List, Optional[list], Optional[List]):
                param_schema = {"type": "array", "items": {"type": "string"}}
            elif param_type in (dict, Dict, Optional[dict], Optional[Dict]):
                param_schema = {"type": "object"}
            else:
                # Default to string for unknown types
                param_schema = {"type": "string"}
            
            # Extract parameter description from docstring if available
            param_desc = f"Parameter {param_name}"
            for line in fn_doc.split('\n'):
                if f"{param_name}:" in line or f"{param_name} -" in line or f"{param_name} –" in line:
                    parts = line.split(':', 1) if ':' in line else line.split('-', 1) if '-' in line else line.split('–', 1)
                    if len(parts) > 1:
                        param_desc = parts[1].strip()
                        break
            
            param_schema["description"] = param_desc
            
            # Add to parameter definitions
            parameters[param_name] = param_schema
            
            # Track required parameters
            if not has_default:
                required_params.append(param_name)
        
        # Create JSON schema
        schema = {
            "type": "object",
            "properties": parameters,
            "required": required_params
        }
        
        # Create tool specification
        tool_spec = {
            "name": fn_name,
            "description": description or fn_doc,
            "schema": schema
        }
        
        # Attach tool spec to the function
        fn.tool_spec = tool_spec
        
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Check if this is being called as a tool (through agent framework)
            if len(args) == 1 and isinstance(args[0], dict) and "input" in args[0]:
                tool_input = args[0]
                tool_id = tool_input.get("tool_id", "unknown")
                
                try:
                    # Extract input parameters
                    params = tool_input.get("input", {})
                    
                    # Call the function
                    result = fn(**params)
                    
                    # Format the result for agent framework
                    if isinstance(result, dict) and "status" in result:
                        # Result is already properly formatted
                        result["tool_id"] = tool_id
                        return result
                    else:
                        # Wrap the result in standard format
                        return {
                            "tool_id": tool_id,
                            "status": "success",
                            "data": result
                        }
                        
                except Exception as e:
                    logger.error(f"Error executing tool {fn_name}: {str(e)}")
                    return {
                        "tool_id": tool_id,
                        "status": "error",
                        "error": str(e)
                    }
            else:
                # Regular function call
                return fn(*args, **kwargs)
        
        # Add tool specification to the wrapper
        wrapper.tool_spec = tool_spec
        
        return wrapper
    
    # Handle both @tool and @tool() syntax
    if func is None:
        return decorator
    else:
        return decorator(func)