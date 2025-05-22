#!/usr/bin/env python3

"""
Exceptions for the LLM module.

This module defines custom exceptions for LLM providers to handle
specific error conditions like rate limiting and context window overflow.
"""

class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""
    
    def __init__(self, message: str, provider: str = None, model: str = None):
        self.provider = provider
        self.model = model
        super().__init__(message)

class ContextWindowExceededError(LLMProviderError):
    """
    Exception raised when the input exceeds the model's context window.
    
    This exception includes information about the maximum context window size
    and the approximate size of the input, when available.
    """
    
    def __init__(self, message: str, provider: str = None, model: str = None,
                max_context_size: int = None, input_size: int = None):
        self.max_context_size = max_context_size
        self.input_size = input_size
        super().__init__(f"Context window exceeded: {message}", provider, model)

class RateLimitExceededError(LLMProviderError):
    """
    Exception raised when the API rate limit is exceeded.
    
    This exception includes information about the rate limit and
    retry-after time, when available.
    """
    
    def __init__(self, message: str, provider: str = None, model: str = None,
                retry_after: int = None, requests_per_minute: int = None):
        self.retry_after = retry_after
        self.requests_per_minute = requests_per_minute
        super().__init__(f"Rate limit exceeded: {message}", provider, model)

class ModelUnavailableError(LLMProviderError):
    """
    Exception raised when the requested model is unavailable.
    
    This exception is raised when the model cannot be accessed,
    either temporarily or permanently.
    """
    
    def __init__(self, message: str, provider: str = None, model: str = None):
        super().__init__(f"Model unavailable: {message}", provider, model)

class InvalidRequestError(LLMProviderError):
    """
    Exception raised when the request to the model is invalid.
    
    This exception is raised for malformed requests, invalid parameters,
    or unsupported functionality.
    """
    
    def __init__(self, message: str, provider: str = None, model: str = None):
        super().__init__(f"Invalid request: {message}", provider, model)

class ContentFilterError(LLMProviderError):
    """
    Exception raised when content is filtered by the model provider.
    
    This exception is raised when the input or output violates the
    provider's content policies.
    """
    
    def __init__(self, message: str, provider: str = None, model: str = None,
                filtered_type: str = None, filtered_categories: list = None):
        self.filtered_type = filtered_type  # "input" or "output"
        self.filtered_categories = filtered_categories or []
        super().__init__(f"Content filtered: {message}", provider, model)

class AuthenticationError(LLMProviderError):
    """
    Exception raised when authentication with the LLM provider fails.
    
    This exception is raised for invalid API keys, expired tokens,
    or other authentication issues.
    """
    
    def __init__(self, message: str, provider: str = None):
        super().__init__(f"Authentication error: {message}", provider)

class NetworkError(LLMProviderError):
    """
    Exception raised when network issues occur when communicating with the LLM provider.
    
    This exception is raised for timeouts, connection failures,
    and other network-related issues.
    """
    
    def __init__(self, message: str, provider: str = None, 
                 status_code: int = None, retry_recommended: bool = True):
        self.status_code = status_code
        self.retry_recommended = retry_recommended
        super().__init__(f"Network error: {message}", provider)