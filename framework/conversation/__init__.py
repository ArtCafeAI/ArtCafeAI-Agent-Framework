"""
Conversation management module for ArtCafe Agent Framework.

This module provides classes and utilities for managing conversation history,
including tokenization, truncation, and context window management.
"""

from .manager import ConversationManager, SlidingWindowManager, MessageWindow
from .message import Message, MessageRole

__all__ = [
    "ConversationManager", 
    "SlidingWindowManager", 
    "MessageWindow",
    "Message",
    "MessageRole"
]