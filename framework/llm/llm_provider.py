#!/usr/bin/env python3

import abc
import json
import logging
import asyncio
from typing import Dict, List, Any, AsyncIterator, Callable, Optional, Union

from .exceptions import (
    ContextWindowExceededError,
    RateLimitExceededError,
    InvalidRequestError,
    ModelUnavailableError,
    ContentFilterError,
    AuthenticationError,
    NetworkError
)

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
    
    async def generate_stream(self, 
                            prompt: str, 
                            system: Optional[str] = None, 
                            max_tokens: Optional[int] = None, 
                            temperature: Optional[float] = None, 
                            stop_sequences: Optional[List[str]] = None,
                            **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate streaming text from the LLM.
        
        Default implementation yields a single chunk with the complete response.
        Providers supporting streaming should override this method.
        
        Args:
            prompt: The user prompt to send to the LLM
            system: Optional system prompt to define context and behavior
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-1)
            stop_sequences: List of strings that will stop generation if encountered
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Dict[str, Any]: Token chunks from the stream
        """
        # Default implementation calls non-streaming version and yields its result
        response = await self.generate(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences,
            **kwargs
        )
        
        # Convert to stream format with token type
        if response["success"]:
            yield {
                "type": "token",
                "token": response["data"]["content"],
                "is_complete": True
            }
        else:
            yield {
                "type": "error",
                "error": response.get("error", "Unknown error")
            }
    
    @abc.abstractmethod
    async def chat(self, 
                 messages: List[Dict[str, Any]], 
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
    
    async def chat_stream(self, 
                        messages: List[Dict[str, Any]], 
                        system: Optional[str] = None,
                        max_tokens: Optional[int] = None, 
                        temperature: Optional[float] = None, 
                        stop_sequences: Optional[List[str]] = None,
                        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                        **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate a streaming response to a chat conversation.
        
        Default implementation yields a single chunk with the complete response.
        Providers supporting streaming should override this method.
        
        Args:
            messages: List of message objects with role and content fields
            system: Optional system message to define context and behavior
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-1)
            stop_sequences: List of strings that will stop generation if encountered
            callback: Optional callback function for token events
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Dict[str, Any]: Token chunks from the stream
        """
        # Default implementation calls non-streaming version and yields its result
        response = await self.chat(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences,
            **kwargs
        )
        
        # Convert to stream format with token type
        if response["success"]:
            token_data = {
                "type": "token",
                "token": response["data"]["content"],
                "is_complete": True
            }
            
            # Call callback if provided
            if callback:
                callback(token_data)
                
            yield token_data
        else:
            error_data = {
                "type": "error",
                "error": response.get("error", "Unknown error")
            }
            
            # Call callback if provided
            if callback:
                callback(error_data)
                
            yield error_data
    
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
    
    def get_conversation_token_count(self, messages: List[Dict[str, Any]], system: Optional[str] = None) -> int:
        """
        Estimate the number of tokens in a conversation.
        
        Args:
            messages: List of message objects with role and content fields
            system: Optional system message
            
        Returns:
            int: Estimated token count for the entire conversation
        """
        # Count system prompt tokens
        total_tokens = 0
        if system:
            total_tokens += self.get_token_count(system)
        
        # Count message tokens
        for message in messages:
            # Count role tokens (varies by model, but typically 1-4 tokens)
            role_tokens = 4  # Approximate
            
            # Count content tokens
            content = message.get("content", "")
            if isinstance(content, str):
                content_tokens = self.get_token_count(content)
            else:
                # Handle structured content (like tool calls)
                content_tokens = self.get_token_count(json.dumps(content))
            
            total_tokens += role_tokens + content_tokens
        
        # Add tokens for format overhead (typically 10-20 tokens)
        format_tokens = 20  # Approximate
        total_tokens += format_tokens
        
        return total_tokens
    
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
    
    async def retry_with_exponential_backoff(self,
                                          func: Callable,
                                          max_retries: int = 5,
                                          initial_delay: float = 1.0,
                                          max_delay: float = 60.0,
                                          backoff_factor: float = 2.0,
                                          retry_on_exceptions: tuple = (RateLimitExceededError, NetworkError),
                                          *args, **kwargs) -> Any:
        """
        Retry a function with exponential backoff on certain exceptions.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retries
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Factor to multiply delay by after each retry
            retry_on_exceptions: Tuple of exceptions to retry on
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Any: Result of the function if successful
            
        Raises:
            Exception: Last caught exception if all retries fail
        """
        delay = initial_delay
        last_exception = None
        
        for retry in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except retry_on_exceptions as e:
                last_exception = e
                
                # Get retry-after from rate limit error if available
                retry_after = None
                if isinstance(e, RateLimitExceededError) and e.retry_after:
                    retry_after = e.retry_after
                
                # Calculate delay
                if retry_after:
                    # Use provider's recommended retry time
                    actual_delay = retry_after
                else:
                    # Use exponential backoff
                    actual_delay = min(delay, max_delay)
                    delay *= backoff_factor
                
                logger.warning(
                    f"Retry {retry+1}/{max_retries} in {actual_delay}s due to {e.__class__.__name__}: {str(e)}")
                await asyncio.sleep(actual_delay)
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        
        # Should never get here
        raise RuntimeError("Unexpected error in retry logic")