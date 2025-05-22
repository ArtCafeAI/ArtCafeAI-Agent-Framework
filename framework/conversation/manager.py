#!/usr/bin/env python3

import abc
import dataclasses
import json
import logging
from typing import Dict, List, Optional, Tuple, Union

from .message import Message, MessageRole

logger = logging.getLogger("AgentFramework.Conversation.Manager")

@dataclasses.dataclass
class MessageWindow:
    """
    Represents a window of messages in a conversation.
    
    This class is used to track which messages are included in the
    current context window for LLM interactions.
    """
    start_index: int
    end_index: int
    token_count: int
    
    def __post_init__(self):
        """Validate the window after initialization."""
        if self.start_index > self.end_index:
            raise ValueError("start_index must be <= end_index")
        
        if self.token_count < 0:
            raise ValueError("token_count must be >= 0")

class ConversationManager(abc.ABC):
    """
    Abstract base class for conversation management.
    
    This class defines the interface for conversation managers, which are
    responsible for managing the context window of conversation history
    provided to the LLM.
    """
    
    @abc.abstractmethod
    def apply_management(self, messages: List[Dict], system_prompt: Optional[str] = None) -> List[Dict]:
        """
        Apply conversation management to a list of messages.
        
        This method is called before sending messages to the LLM to ensure
        the conversation fits within the context window and includes the
        most relevant content.
        
        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt to include
            
        Returns:
            List[Dict]: The managed list of messages to send to the LLM
        """
        pass
    
    @abc.abstractmethod
    def get_message_window(self, messages: List[Dict], system_prompt: Optional[str] = None) -> MessageWindow:
        """
        Get the current message window.
        
        This method returns information about which messages are included
        in the current context window.
        
        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt to include
            
        Returns:
            MessageWindow: Information about the current window
        """
        pass
    
    @abc.abstractmethod
    def reduce_context(self, messages: List[Dict], max_tokens: int) -> List[Dict]:
        """
        Reduce the context to fit within a token limit.
        
        This method is called when the context window is exceeded to
        reduce the messages to fit within the limit.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum number of tokens allowed
            
        Returns:
            List[Dict]: The reduced list of messages
        """
        pass

class SlidingWindowManager(ConversationManager):
    """
    Sliding window conversation manager.
    
    This manager maintains a sliding window of messages in the conversation,
    ensuring that the most recent messages are always included in the context
    while staying within token limits.
    """
    
    def __init__(self, 
                token_counter: callable,
                max_tokens: int = 8000,
                system_prompt_tokens: int = 1000, 
                reserve_tokens: int = 1000):
        """
        Initialize the sliding window manager.
        
        Args:
            token_counter: Function to count tokens in text
            max_tokens: Maximum tokens allowed in the context window
            system_prompt_tokens: Tokens to reserve for system prompt
            reserve_tokens: Tokens to reserve for LLM response
        """
        self.token_counter = token_counter
        self.max_tokens = max_tokens
        self.system_prompt_tokens = system_prompt_tokens
        self.reserve_tokens = reserve_tokens
        
        # Maintain window state
        self.current_window = MessageWindow(0, 0, 0)
    
    def apply_management(self, messages: List[Dict], system_prompt: Optional[str] = None) -> List[Dict]:
        """
        Apply sliding window management to messages.
        
        This method adjusts the messages to fit within the context window
        while keeping the most recent messages.
        
        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt to include
            
        Returns:
            List[Dict]: The managed list of messages
        """
        if not messages:
            return []
        
        # Get available tokens (accounting for system prompt and reserve)
        system_tokens = self._count_system_tokens(system_prompt)
        available_tokens = self.max_tokens - system_tokens - self.reserve_tokens
        
        if available_tokens <= 0:
            logger.warning("No tokens available for messages after system prompt and reserve")
            return []
        
        # Count tokens for all messages
        message_tokens = self._count_message_tokens(messages)
        
        # If all messages fit, return them all
        total_tokens = sum(message_tokens)
        if total_tokens <= available_tokens:
            self.current_window = MessageWindow(0, len(messages) - 1, total_tokens)
            return messages
        
        # Otherwise, create a sliding window from the most recent message backward
        cumulative_tokens = 0
        end_index = len(messages) - 1
        start_index = end_index
        
        while start_index >= 0:
            cumulative_tokens += message_tokens[start_index]
            
            if cumulative_tokens > available_tokens:
                # We've exceeded the limit, go back one message
                start_index += 1
                cumulative_tokens -= message_tokens[start_index - 1]
                break
                
            start_index -= 1
            
            if start_index < 0:
                # We've included all messages
                start_index = 0
                break
        
        # Update window state
        self.current_window = MessageWindow(start_index, end_index, cumulative_tokens)
        
        # Return the window of messages
        return messages[start_index:]
    
    def get_message_window(self, messages: List[Dict], system_prompt: Optional[str] = None) -> MessageWindow:
        """
        Get the current message window.
        
        This method returns the current window without modifying it.
        
        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt to include
            
        Returns:
            MessageWindow: Information about the current window
        """
        return self.current_window
    
    def reduce_context(self, messages: List[Dict], max_tokens: int) -> List[Dict]:
        """
        Reduce the context to fit within a token limit.
        
        This method is called when the context window is exceeded to
        create a smaller window of messages.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum number of tokens allowed
            
        Returns:
            List[Dict]: The reduced list of messages
        """
        # Special case: if max_tokens is very small, keep only the most recent message
        if max_tokens <= 100:
            logger.warning("Max tokens too small, keeping only the most recent message")
            if messages:
                return [messages[-1]]
            return []
        
        # Get token counts for all messages
        message_tokens = self._count_message_tokens(messages)
        
        # Create a window from the most recent message backward
        cumulative_tokens = 0
        end_index = len(messages) - 1
        start_index = end_index
        
        # Leave some room for response tokens
        reserve = min(max_tokens // 2, self.reserve_tokens)
        available_tokens = max_tokens - reserve
        
        while start_index >= 0:
            cumulative_tokens += message_tokens[start_index]
            
            if cumulative_tokens > available_tokens:
                # We've exceeded the limit, go back one message
                start_index += 1
                cumulative_tokens -= message_tokens[start_index - 1]
                break
                
            start_index -= 1
            
            if start_index < 0:
                # We've included all messages
                start_index = 0
                break
        
        # Update window state
        self.current_window = MessageWindow(start_index, end_index, cumulative_tokens)
        
        # Return the window of messages
        reduced_messages = messages[start_index:]
        logger.info(f"Reduced context from {len(messages)} to {len(reduced_messages)} messages")
        
        return reduced_messages
    
    def _count_system_tokens(self, system_prompt: Optional[str]) -> int:
        """
        Count tokens in the system prompt.
        
        Args:
            system_prompt: The system prompt text
            
        Returns:
            int: Number of tokens in the system prompt
        """
        if not system_prompt:
            return 0
            
        try:
            return self.token_counter(system_prompt)
        except Exception as e:
            logger.error(f"Error counting system prompt tokens: {e}")
            return self.system_prompt_tokens  # Fall back to default
    
    def _count_message_tokens(self, messages: List[Dict]) -> List[int]:
        """
        Count tokens for each message.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List[int]: List of token counts for each message
        """
        token_counts = []
        
        for message in messages:
            try:
                # Add tokens for role name (approximately 4 tokens)
                role_tokens = 4
                
                # Count content tokens
                content = message.get("content", "")
                if isinstance(content, str):
                    content_tokens = self.token_counter(content)
                else:
                    # Handle structured content
                    content_tokens = self.token_counter(json.dumps(content))
                
                # Add tokens for message formatting (approximately 5 tokens)
                format_tokens = 5
                
                # Sum all tokens for this message
                message_tokens = role_tokens + content_tokens + format_tokens
                token_counts.append(message_tokens)
                
            except Exception as e:
                logger.error(f"Error counting message tokens: {e}")
                # Approximation: 1 token per 4 characters
                if isinstance(content, str):
                    approx_tokens = len(content) // 4 + 10  # 10 for role and formatting
                    token_counts.append(approx_tokens)
                else:
                    # Default estimate for structured content
                    token_counts.append(100)  # Approximate for complex messages
        
        return token_counts