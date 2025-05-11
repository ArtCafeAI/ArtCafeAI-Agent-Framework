#!/usr/bin/env python3

"""
MCP (Model Control Plane) Integration Module

This module provides integration with MCP services for managed AI models.
"""

import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("AgentFramework.MCP")

__all__ = [
    'MCPClient',
    'initialize',
    'get_client'
]

class MCPClient:
    """
    Client for MCP (Model Control Plane) services.
    
    This client provides a unified interface for interacting with different
    AI model providers, such as AWS Bedrock, OpenAI, etc., through a consistent API.
    
    Attributes:
        _config: Configuration for MCP integration
        _endpoint: MCP service endpoint
        _api_key: API key for authentication
        _session: Request session for API calls
    """
    
    def __init__(self, endpoint: str, api_key: str):
        """
        Initialize a new MCP client.
        
        Args:
            endpoint: MCP service endpoint URL
            api_key: API key for authentication
        """
        self._endpoint = endpoint
        self._api_key = api_key
        
        try:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
        except ImportError:
            logger.error("Requests library not found, MCP client will not function correctly")
            self._session = None
        
        logger.debug(f"Initialized MCP client with endpoint {endpoint}")
    
    def invoke_model(self, model_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke an AI model with parameters.
        
        Args:
            model_id: ID of the model to invoke
            parameters: Model-specific parameters
            
        Returns:
            Dict[str, Any]: Model response
            
        Raises:
            ValueError: If the MCP client is not properly initialized
            RuntimeError: If the model invocation fails
        """
        if not self._session:
            raise ValueError("MCP client is not properly initialized")
        
        try:
            import json
            
            # Prepare request data
            request_data = {
                "model_id": model_id,
                "parameters": parameters
            }
            
            # Make API request
            response = self._session.post(
                f"{self._endpoint}/invoke",
                data=json.dumps(request_data)
            )
            
            # Check for errors
            if response.status_code != 200:
                raise RuntimeError(f"MCP API error: {response.status_code} - {response.text}")
            
            # Parse response
            result = response.json()
            
            logger.debug(f"Invoked model {model_id} successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error invoking model {model_id}: {str(e)}")
            raise RuntimeError(f"Error invoking model: {str(e)}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available AI models.
        
        Returns:
            List[Dict[str, Any]]: List of available models with metadata
            
        Raises:
            ValueError: If the MCP client is not properly initialized
            RuntimeError: If the API request fails
        """
        if not self._session:
            raise ValueError("MCP client is not properly initialized")
        
        try:
            # Make API request
            response = self._session.get(f"{self._endpoint}/models")
            
            # Check for errors
            if response.status_code != 200:
                raise RuntimeError(f"MCP API error: {response.status_code} - {response.text}")
            
            # Parse response
            result = response.json()
            
            logger.debug(f"Listed {len(result.get('models', []))} available models")
            return result.get("models", [])
            
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            raise RuntimeError(f"Error listing models: {str(e)}")
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Get information about a specific AI model.
        
        Args:
            model_id: ID of the model to get information about
            
        Returns:
            Dict[str, Any]: Model information
            
        Raises:
            ValueError: If the MCP client is not properly initialized
            RuntimeError: If the API request fails
        """
        if not self._session:
            raise ValueError("MCP client is not properly initialized")
        
        try:
            # Make API request
            response = self._session.get(f"{self._endpoint}/models/{model_id}")
            
            # Check for errors
            if response.status_code != 200:
                raise RuntimeError(f"MCP API error: {response.status_code} - {response.text}")
            
            # Parse response
            result = response.json()
            
            logger.debug(f"Got information for model {model_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting model info for {model_id}: {str(e)}")
            raise RuntimeError(f"Error getting model info: {str(e)}")

# Global client instance
_mcp_client = None

def initialize(endpoint: str, api_key: str) -> MCPClient:
    """
    Initialize the MCP client.
    
    Args:
        endpoint: MCP service endpoint URL
        api_key: API key for authentication
        
    Returns:
        MCPClient: The initialized client
    """
    global _mcp_client
    
    if _mcp_client is None:
        _mcp_client = MCPClient(endpoint, api_key)
        logger.info(f"Initialized MCP client with endpoint {endpoint}")
    
    return _mcp_client

def get_client() -> Optional[MCPClient]:
    """
    Get the MCP client instance.
    
    Returns:
        Optional[MCPClient]: The MCP client, or None if not initialized
    """
    return _mcp_client