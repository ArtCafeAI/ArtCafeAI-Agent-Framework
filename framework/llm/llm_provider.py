#!/usr/bin/env python3

import abc
import json
import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger("AgentFramework.LLM.LLMProvider")

class LLMProvider(abc.ABC):
    """
    Abstract base class for LLM providers.
    
    This class defines the interface for all LLM providers. Concrete implementations
    must implement the required methods to interact with specific LLM services.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM provider.
        
        Args:
            config: Configuration dictionary for the provider
        """
        self.config = config
        self.model = config.get("model", "")
        self.provider_name = "base"
    
    @abc.abstractmethod
    async def generate(self, 
                       prompt: str, 
                       system: Optional[str] = None, 
                       max_tokens: Optional[int] = None, 
                       temperature: Optional[float] = None, 
                       stop_sequences: Optional[List[str]] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Generate text from the LLM.
        
        Args:
            prompt: The user prompt to send to the LLM
            system: Optional system prompt to define context and behavior
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-1)
            stop_sequences: List of strings that will stop generation if encountered
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict[str, Any]: Response containing generated text and metadata
        """
        pass
    
    @abc.abstractmethod
    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   system: Optional[str] = None,
                   max_tokens: Optional[int] = None, 
                   temperature: Optional[float] = None, 
                   stop_sequences: Optional[List[str]] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Generate a response to a chat conversation.
        
        Args:
            messages: List of message objects with role and content fields
            system: Optional system message to define context and behavior
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-1)
            stop_sequences: List of strings that will stop generation if encountered
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict[str, Any]: Response containing generated text and metadata
        """
        pass
    
    @abc.abstractmethod
    async def embed(self, 
                    text: Union[str, List[str]], 
                    **kwargs) -> Dict[str, Any]:
        """
        Generate embeddings for text.
        
        Args:
            text: Text or list of texts to embed
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict[str, Any]: Response containing embeddings and metadata
        """
        pass
    
    @abc.abstractmethod
    def get_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Estimated token count
        """
        pass
    
    def format_json_response(self, 
                             data: Dict[str, Any], 
                             success: bool = True, 
                             error: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a response in a standard structure.
        
        Args:
            data: The response data
            success: Whether the request was successful
            error: Error message if request failed
            
        Returns:
            Dict[str, Any]: Formatted response
        """
        response = {
            "provider": self.provider_name,
            "model": self.model,
            "success": success,
            "data": data
        }
        
        if error:
            response["error"] = error
        
        return response