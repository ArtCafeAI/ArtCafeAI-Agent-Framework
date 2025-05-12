#!/usr/bin/env python3

import json
import logging
import os
from typing import Dict, List, Any, Optional, Union

import aiohttp
import tiktoken

from .llm_provider import LLMProvider

logger = logging.getLogger("AgentFramework.LLM.AnthropicProvider")

class AnthropicProvider(LLMProvider):
    """
    LLM provider implementation for Anthropic Claude models.
    
    This provider implements the LLMProvider interface for Anthropic Claude
    models, using the Anthropic Messages API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Anthropic provider.
        
        Args:
            config: Configuration dictionary for the provider
        """
        super().__init__(config)
        
        self.provider_name = "anthropic"
        self.model = config.get("model", "claude-3-opus-20240229")
        
        # Get API key from config or environment
        self.api_key = config.get("api_key", "")
        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not self.api_key:
                logger.warning("No Anthropic API key provided, LLM calls will fail")
        
        # Initialize API endpoint
        self.api_endpoint = config.get("anthropic", {}).get(
            "api_endpoint", "https://api.anthropic.com")
        
        # Initialize defaults
        self.default_max_tokens = config.get("anthropic", {}).get("max_tokens", 4096)
        self.default_temperature = config.get("anthropic", {}).get("temperature", 0.7)
        
        # Initialize tokenizer
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    async def generate(self, 
                       prompt: str, 
                       system: Optional[str] = None, 
                       max_tokens: Optional[int] = None, 
                       temperature: Optional[float] = None, 
                       stop_sequences: Optional[List[str]] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Generate text from Claude.
        
        Args:
            prompt: The user prompt to send to Claude
            system: Optional system prompt to define context and behavior
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-1)
            stop_sequences: List of strings that will stop generation if encountered
            **kwargs: Additional Claude-specific parameters
            
        Returns:
            Dict[str, Any]: Response containing generated text and metadata
        """
        # Convert to chat format
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(
            messages, system, max_tokens, temperature, stop_sequences, **kwargs)
    
    async def chat(self, 
                   messages: List[Dict[str, str]], 
                   system: Optional[str] = None,
                   max_tokens: Optional[int] = None, 
                   temperature: Optional[float] = None, 
                   stop_sequences: Optional[List[str]] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Generate a response to a chat conversation with Claude.
        
        Args:
            messages: List of message objects with role and content fields
            system: Optional system message to define context and behavior
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-1)
            stop_sequences: List of strings that will stop generation if encountered
            **kwargs: Additional Claude-specific parameters
            
        Returns:
            Dict[str, Any]: Response containing generated text and metadata
        """
        if not self.api_key:
            error = "No Anthropic API key provided"
            logger.error(error)
            return self.format_json_response({}, False, error)
        
        try:
            # Prepare request
            api_url = f"{self.api_endpoint}/v1/messages"
            
            # Set request parameters
            request_data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.default_max_tokens,
                "temperature": temperature or self.default_temperature,
            }
            
            # Add system prompt if provided
            if system:
                request_data["system"] = system
            
            # Add stop sequences if provided
            if stop_sequences:
                request_data["stop_sequences"] = stop_sequences
            
            # Add additional parameters
            for key, value in kwargs.items():
                request_data[key] = value
            
            # Make API request
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, 
                                      headers=headers, 
                                      json=request_data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error = f"Anthropic API error: {response.status} - {error_text}"
                        logger.error(error)
                        return self.format_json_response({}, False, error)
                    
                    result = await response.json()
            
            # Format response
            response_data = {
                "content": result["content"][0]["text"],
                "usage": {
                    "input_tokens": result["usage"]["input_tokens"],
                    "output_tokens": result["usage"]["output_tokens"],
                    "total_tokens": result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
                },
                "model": result["model"],
                "id": result["id"],
                "metadata": {}
            }
            
            # Add metadata if available
            if "metadata" in result:
                response_data["metadata"] = result["metadata"]
            
            return self.format_json_response(response_data)
            
        except Exception as e:
            error = f"Error calling Anthropic API: {str(e)}"
            logger.error(error)
            return self.format_json_response({}, False, error)
    
    async def embed(self, 
                    text: Union[str, List[str]], 
                    **kwargs) -> Dict[str, Any]:
        """
        Generate embeddings for text using Claude.
        
        Args:
            text: Text or list of texts to embed
            **kwargs: Additional Claude-specific parameters
            
        Returns:
            Dict[str, Any]: Response containing embeddings and metadata
        """
        if not self.api_key:
            error = "No Anthropic API key provided"
            logger.error(error)
            return self.format_json_response({}, False, error)
        
        try:
            # Prepare request
            api_url = f"{self.api_endpoint}/v1/embeddings"
            
            # Ensure text is a list
            if isinstance(text, str):
                texts = [text]
            else:
                texts = text
            
            # Set request parameters
            request_data = {
                "model": "claude-3-embeddings-20240229",  # Currently only one embedding model
                "input": texts,
            }
            
            # Add additional parameters
            for key, value in kwargs.items():
                request_data[key] = value
            
            # Make API request
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, 
                                      headers=headers, 
                                      json=request_data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error = f"Anthropic API error: {response.status} - {error_text}"
                        logger.error(error)
                        return self.format_json_response({}, False, error)
                    
                    result = await response.json()
            
            # Format response
            response_data = {
                "embeddings": [item["embedding"] for item in result["embeddings"]],
                "dimensions": len(result["embeddings"][0]["embedding"]) if result["embeddings"] else 0,
                "usage": {
                    "input_tokens": result["usage"]["input_tokens"],
                    "output_tokens": 0,
                    "total_tokens": result["usage"]["input_tokens"]
                },
                "model": result["model"],
                "id": result["id"]
            }
            
            return self.format_json_response(response_data)
            
        except Exception as e:
            error = f"Error calling Anthropic Embeddings API: {str(e)}"
            logger.error(error)
            return self.format_json_response({}, False, error)
    
    def get_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Estimated token count
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.error(f"Error estimating token count: {str(e)}")
            # Estimate based on ratio of 1 token per ~4 characters
            return len(text) // 4