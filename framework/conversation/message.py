#!/usr/bin/env python3

import enum
from typing import Any, Dict, List, Optional, Union

class MessageRole(enum.Enum):
    """Enum for message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class Message:
    """
    Represents a message in a conversation.
    
    This class provides a structured way to represent and manipulate
    conversation messages, with support for different content types
    and roles.
    """
    
    def __init__(self, 
                role: Union[MessageRole, str], 
                content: Union[str, List[Dict[str, Any]], Dict[str, Any]],
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a message.
        
        Args:
            role: The role of the sender (system, user, assistant, or tool)
            content: The message content (string or structured content)
            metadata: Optional metadata about the message
        """
        # Convert string role to enum
        if isinstance(role, str):
            try:
                self.role = MessageRole(role)
            except ValueError:
                # Default to user for unknown roles
                self.role = MessageRole.USER
        else:
            self.role = role
        
        # Process content
        self.content = content
        
        # Store metadata
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary format.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the message
        """
        result = {
            "role": self.role.value,
            "content": self.content
        }
        
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Create a message from a dictionary.
        
        Args:
            data: Dictionary with message data
            
        Returns:
            Message: New message instance
        """
        return cls(
            role=data.get("role", MessageRole.USER),
            content=data.get("content", ""),
            metadata=data.get("metadata")
        )
    
    @property
    def is_text_only(self) -> bool:
        """
        Check if the message contains only text.
        
        Returns:
            bool: True if the message is text only, False otherwise
        """
        return isinstance(self.content, str)
    
    @property
    def text_content(self) -> str:
        """
        Get the text content of the message.
        
        For structured content, this returns a JSON string representation.
        
        Returns:
            str: The text content
        """
        if self.is_text_only:
            return self.content
        
        # For structured content, return first text content if available
        if isinstance(self.content, list):
            for item in self.content:
                if isinstance(item, dict) and "text" in item:
                    return item["text"]
            
            # If no text found, return empty string
            return ""
        
        # For dict content with text field
        if isinstance(self.content, dict) and "text" in self.content:
            return self.content["text"]
        
        # Fall back to string representation
        import json
        return json.dumps(self.content)
    
    def __str__(self) -> str:
        """
        Get a string representation of the message.
        
        Returns:
            str: String representation in the format "ROLE: content"
        """
        content_str = self.text_content
        if len(content_str) > 50:
            content_str = content_str[:47] + "..."
            
        return f"{self.role.value.upper()}: {content_str}"