#!/usr/bin/env python3

import asyncio
import enum
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ..llm.llm_provider import LLMProvider
from ..tools.handler import ToolHandler

logger = logging.getLogger("AgentFramework.EventLoop")

class EventType(enum.Enum):
    """Event types for the event loop."""
    CYCLE_START = "cycle_start"
    CYCLE_END = "cycle_end"
    LLM_START = "llm_start"
    LLM_TOKEN = "llm_token"
    LLM_END = "llm_end"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    ERROR = "error"

class Event:
    """
    Event class for the event loop.
    
    Events represent stages in the agent's processing cycle and carry
    data related to that stage.
    """
    
    def __init__(self, 
                 event_type: EventType, 
                 data: Optional[Dict[str, Any]] = None, 
                 event_id: Optional[str] = None):
        """
        Initialize a new event.
        
        Args:
            event_type: Type of the event
            data: Data associated with the event
            event_id: Optional unique ID for the event
        """
        self.event_type = event_type
        self.data = data or {}
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = asyncio.get_event_loop().time()

class EventLoop:
    """
    Event loop for agent-LLM interactions.
    
    The event loop manages the flow of interactions between the agent,
    the LLM, and tools. It provides a structured way to:
    - Process user messages
    - Generate LLM responses
    - Execute tools based on LLM requests
    - Handle errors and recovery
    """
    
    def __init__(self, 
                 llm_provider: LLMProvider, 
                 tool_handler: Optional[ToolHandler] = None,
                 callback_handler: Optional[Callable[[Event], None]] = None):
        """
        Initialize the event loop.
        
        Args:
            llm_provider: Provider for LLM interactions
            tool_handler: Handler for tool execution
            callback_handler: Function to call for events
        """
        self.llm_provider = llm_provider
        self.tool_handler = tool_handler or ToolHandler()
        self.callback_handler = callback_handler or (lambda _: None)
    
    async def process_message(self, 
                             user_message: str, 
                             conversation_history: List[Dict[str, Any]],
                             system_prompt: Optional[str] = None,
                             temperature: Optional[float] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process a user message through a complete cycle.
        
        This method implements a complete interaction cycle:
        1. Add user message to conversation history
        2. Generate LLM response
        3. Check for tool usage requests
        4. Execute tools if requested
        5. Continue conversation with tool results
        
        Args:
            user_message: The message from the user
            conversation_history: The conversation history
            system_prompt: Optional system instructions for the LLM
            temperature: Optional temperature for the LLM
        
        Returns:
            Tuple[str, List[Dict[str, Any]]]: The final response and updated conversation history
        """
        # Create cycle start event
        cycle_id = str(uuid.uuid4())
        cycle_start_event = Event(
            EventType.CYCLE_START,
            {"cycle_id": cycle_id, "user_message": user_message}
        )
        self.callback_handler(cycle_start_event)
        
        # Add user message to conversation history
        conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Generate LLM response
        llm_start_event = Event(
            EventType.LLM_START,
            {"cycle_id": cycle_id, "conversation": conversation_history}
        )
        self.callback_handler(llm_start_event)
        
        response = await self.llm_provider.chat(
            messages=conversation_history,
            system=system_prompt,
            temperature=temperature
        )
        
        llm_end_event = Event(
            EventType.LLM_END,
            {"cycle_id": cycle_id, "response": response}
        )
        self.callback_handler(llm_end_event)
        
        # Extract response content
        content = response["data"]["content"]
        
        # Check for tool usage
        tool_calls = self._extract_tool_calls(content)
        
        if tool_calls:
            # Execute tools
            tool_start_event = Event(
                EventType.TOOL_START,
                {"cycle_id": cycle_id, "tool_calls": tool_calls}
            )
            self.callback_handler(tool_start_event)
            
            tool_results = await self.tool_handler.execute_tools(tool_calls)
            
            tool_end_event = Event(
                EventType.TOOL_END,
                {"cycle_id": cycle_id, "tool_results": tool_results}
            )
            self.callback_handler(tool_end_event)
            
            # Add assistant message with tool calls to conversation
            conversation_history.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls
            })
            
            # Add tool results to conversation
            conversation_history.append({
                "role": "tool",
                "content": None,
                "tool_results": tool_results
            })
            
            # Continue conversation with tool results
            llm_start_event = Event(
                EventType.LLM_START,
                {"cycle_id": cycle_id, "conversation": conversation_history}
            )
            self.callback_handler(llm_start_event)
            
            response = await self.llm_provider.chat(
                messages=conversation_history,
                system=system_prompt,
                temperature=temperature
            )
            
            llm_end_event = Event(
                EventType.LLM_END,
                {"cycle_id": cycle_id, "response": response}
            )
            self.callback_handler(llm_end_event)
            
            # Extract final response content
            content = response["data"]["content"]
        
        # Add assistant response to conversation history
        conversation_history.append({
            "role": "assistant",
            "content": content
        })
        
        # Create cycle end event
        cycle_end_event = Event(
            EventType.CYCLE_END,
            {"cycle_id": cycle_id, "final_response": content}
        )
        self.callback_handler(cycle_end_event)
        
        return content, conversation_history
    
    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from LLM response content.
        
        This method parses the LLM's response to identify requests to use tools.
        It supports both function calling formats and custom formatting.
        
        Args:
            content: The LLM response content
            
        Returns:
            List[Dict[str, Any]]: List of extracted tool calls
        """
        # This is a simplified implementation that assumes tools are called in a specific format
        # A more robust implementation would use regex or structured response formats
        
        tool_calls = []
        
        # Simple detection of tool calls in the format:
        # TOOL: tool_name
        # INPUT: {...}
        
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("TOOL:") or line.startswith("USE TOOL:"):
                tool_parts = line.split(":", 1)
                if len(tool_parts) > 1:
                    tool_name = tool_parts[1].strip()
                    
                    # Look for input on next lines
                    input_data = {}
                    j = i + 1
                    
                    # Find INPUT: line
                    while j < len(lines) and not lines[j].strip().startswith("INPUT:"):
                        j += 1
                    
                    if j < len(lines) and lines[j].strip().startswith("INPUT:"):
                        # Extract input text
                        input_text = lines[j].split(":", 1)[1].strip()
                        
                        # Handle multi-line JSON input
                        if input_text.startswith("{"):
                            # Collect JSON across multiple lines
                            json_lines = [input_text]
                            k = j + 1
                            brace_count = input_text.count("{") - input_text.count("}")
                            
                            while k < len(lines) and brace_count > 0:
                                line = lines[k].strip()
                                json_lines.append(line)
                                brace_count += line.count("{") - line.count("}")
                                k += 1
                            
                            try:
                                import json
                                input_data = json.loads(" ".join(json_lines))
                            except json.JSONDecodeError:
                                # Fallback to string input if JSON parsing fails
                                input_data = {"text": " ".join(json_lines)}
                        else:
                            # Handle simple string input
                            input_data = {"text": input_text}
                    
                    # Create tool call
                    tool_call = {
                        "tool_name": tool_name,
                        "input": input_data,
                        "tool_id": str(uuid.uuid4())
                    }
                    
                    tool_calls.append(tool_call)
            
            i += 1
        
        return tool_calls