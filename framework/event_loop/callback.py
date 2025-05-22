#!/usr/bin/env python3

import abc
import logging
import sys
from typing import Any, Dict, Optional

from .event_loop import Event, EventType

logger = logging.getLogger("AgentFramework.EventLoop.Callback")

class CallbackHandler(abc.ABC):
    """
    Abstract base class for event loop callbacks.
    
    Callback handlers receive events from the event loop and process them
    based on the event type. They can be used for logging, monitoring,
    user interface updates, etc.
    """
    
    @abc.abstractmethod
    def handle_event(self, event: Event) -> None:
        """
        Handle an event from the event loop.
        
        Args:
            event: The event to handle
        """
        pass
    
    def __call__(self, event: Event) -> None:
        """
        Call operator makes the callback handler callable.
        
        Args:
            event: The event to handle
        """
        return self.handle_event(event)

class ConsoleCallbackHandler(CallbackHandler):
    """
    Callback handler that prints events to the console.
    
    This handler is useful for debugging and demonstrations, as it provides
    real-time visibility into the event loop's execution.
    """
    
    def __init__(self, verbose: bool = False, output=sys.stdout):
        """
        Initialize the console callback handler.
        
        Args:
            verbose: Whether to print detailed information
            output: Output stream (defaults to stdout)
        """
        self.verbose = verbose
        self.output = output
        self.cycle_id: Optional[str] = None
    
    def handle_event(self, event: Event) -> None:
        """
        Handle an event by printing it to the console.
        
        Args:
            event: The event to handle
        """
        if event.event_type == EventType.CYCLE_START:
            self.cycle_id = event.data.get("cycle_id")
            print(f"\n===== Starting Cycle {self.cycle_id[:8]} =====", file=self.output)
            print(f"User: {event.data.get('user_message')}", file=self.output)
        
        elif event.event_type == EventType.LLM_START:
            if self.verbose:
                print(f"\n--> Sending to LLM...", file=self.output)
        
        elif event.event_type == EventType.LLM_TOKEN:
            token = event.data.get("token", "")
            print(token, end="", flush=True, file=self.output)
        
        elif event.event_type == EventType.LLM_END:
            if self.verbose:
                print(f"\n<-- Received LLM response", file=self.output)
            else:
                response = event.data.get("response", {})
                content = response.get("data", {}).get("content", "")
                print(f"\nAssistant: {content}", file=self.output)
        
        elif event.event_type == EventType.TOOL_START:
            tool_calls = event.data.get("tool_calls", [])
            print(f"\n--> Executing {len(tool_calls)} tool(s)...", file=self.output)
            
            if self.verbose:
                for i, tool_call in enumerate(tool_calls):
                    print(f"  Tool {i+1}: {tool_call.get('tool_name')}", file=self.output)
                    print(f"  Input: {tool_call.get('input')}", file=self.output)
        
        elif event.event_type == EventType.TOOL_END:
            if self.verbose:
                tool_results = event.data.get("tool_results", [])
                print(f"\n<-- Tool execution completed", file=self.output)
                
                for i, result in enumerate(tool_results):
                    status = result.get("status", "unknown")
                    print(f"  Tool {i+1} result: {status}", file=self.output)
                    
                    if status == "error":
                        print(f"  Error: {result.get('error')}", file=self.output)
                    elif self.verbose:
                        print(f"  Data: {result.get('data')}", file=self.output)
        
        elif event.event_type == EventType.ERROR:
            error = event.data.get("error", "Unknown error")
            print(f"\n!!! ERROR: {error}", file=self.output)
        
        elif event.event_type == EventType.CYCLE_END:
            final_response = event.data.get("final_response", "")
            if not self.verbose:
                # Already printed in LLM_END event
                pass
            print(f"\n===== Cycle {self.cycle_id[:8]} Completed =====\n", file=self.output)
            self.cycle_id = None