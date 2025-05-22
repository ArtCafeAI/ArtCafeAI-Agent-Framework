#!/usr/bin/env python3

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("AgentFramework.Telemetry.Tracer")

# Global tracer instance
_tracer = None

class Span:
    """
    Represents a trace span.
    
    Spans are used to track operations and their timing in the agent framework.
    They can be nested to create a hierarchical trace of operations.
    """
    
    def __init__(self, 
                name: str, 
                span_id: Optional[str] = None,
                parent_id: Optional[str] = None,
                attributes: Optional[Dict[str, Any]] = None):
        """
        Initialize a new span.
        
        Args:
            name: Name of the span
            span_id: Optional span ID (defaults to a new UUID)
            parent_id: Optional parent span ID
            attributes: Optional span attributes
        """
        self.name = name
        self.span_id = span_id or str(uuid.uuid4())
        self.parent_id = parent_id
        self.attributes = attributes or {}
        self.events = []
        self.status = "ok"
        self.error = None
        
        self.start_time = time.time()
        self.end_time = None
        self.duration = None
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an event to the span.
        
        Args:
            name: Name of the event
            attributes: Optional event attributes
        """
        event = {
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        }
        
        self.events.append(event)
    
    def set_status(self, status: str, error: Optional[str] = None) -> None:
        """
        Set the status of the span.
        
        Args:
            status: Status of the span ("ok", "error")
            error: Optional error message
        """
        self.status = status
        self.error = error
    
    def end(self) -> None:
        """End the span and calculate its duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the span to a dictionary format.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the span
        """
        result = {
            "name": self.name,
            "span_id": self.span_id,
            "start_time": self.start_time,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status
        }
        
        if self.parent_id:
            result["parent_id"] = self.parent_id
            
        if self.end_time:
            result["end_time"] = self.end_time
            result["duration"] = self.duration
            
        if self.error:
            result["error"] = self.error
            
        return result
    
    def __enter__(self) -> 'Span':
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if exc_type:
            self.set_status("error", str(exc_val))
            
        self.end()

class Tracer:
    """
    Distributed tracing for agent operations.
    
    The tracer collects spans from agent operations and can export
    them to various tracing backends.
    """
    
    def __init__(self, 
                service_name: str = "artcafe-agent", 
                exporter: Optional[Any] = None):
        """
        Initialize a new tracer.
        
        Args:
            service_name: Name of the service for trace identification
            exporter: Optional exporter for sending traces to a backend
        """
        self.service_name = service_name
        self.exporter = exporter
        self.spans = {}
        self.active_spans = {}
    
    def create_span(self, 
                   name: str, 
                   parent_id: Optional[str] = None,
                   attributes: Optional[Dict[str, Any]] = None) -> Span:
        """
        Create a new span.
        
        Args:
            name: Name of the span
            parent_id: Optional parent span ID
            attributes: Optional span attributes
            
        Returns:
            Span: The newly created span
        """
        span = Span(name, parent_id=parent_id, attributes=attributes)
        self.spans[span.span_id] = span
        return span
    
    def start_span(self, 
                  name: str, 
                  parent_id: Optional[str] = None,
                  attributes: Optional[Dict[str, Any]] = None) -> Span:
        """
        Start a new span.
        
        Args:
            name: Name of the span
            parent_id: Optional parent span ID
            attributes: Optional span attributes
            
        Returns:
            Span: The newly created span
        """
        span = self.create_span(name, parent_id, attributes)
        self.active_spans[span.span_id] = span
        return span
    
    def end_span(self, span_id: str, error: Optional[str] = None) -> None:
        """
        End a span by its ID.
        
        Args:
            span_id: ID of the span to end
            error: Optional error message
        """
        if span_id in self.active_spans:
            span = self.active_spans[span_id]
            
            if error:
                span.set_status("error", error)
                
            span.end()
            
            if self.exporter:
                self._export_span(span)
                
            del self.active_spans[span_id]
    
    def _export_span(self, span: Span) -> None:
        """
        Export a span to the configured backend.
        
        Args:
            span: The span to export
        """
        if not self.exporter:
            return
            
        try:
            self.exporter.export_span(span.to_dict())
        except Exception as e:
            logger.error(f"Error exporting span: {str(e)}")
    
    def start_llm_span(self, 
                      model: str, 
                      prompt: str, 
                      parent_id: Optional[str] = None,
                      attributes: Optional[Dict[str, Any]] = None) -> Span:
        """
        Start a span for an LLM interaction.
        
        Args:
            model: Name of the LLM model
            prompt: Prompt sent to the model
            parent_id: Optional parent span ID
            attributes: Optional span attributes
            
        Returns:
            Span: The newly created span
        """
        span_attributes = {
            "llm.model": model,
            "llm.prompt_length": len(prompt),
            **(attributes or {})
        }
        
        return self.start_span("llm.generate", parent_id, span_attributes)
    
    def start_tool_span(self, 
                       tool_name: str, 
                       arguments: Any, 
                       parent_id: Optional[str] = None,
                       attributes: Optional[Dict[str, Any]] = None) -> Span:
        """
        Start a span for a tool execution.
        
        Args:
            tool_name: Name of the tool
            arguments: Arguments passed to the tool
            parent_id: Optional parent span ID
            attributes: Optional span attributes
            
        Returns:
            Span: The newly created span
        """
        span_attributes = {
            "tool.name": tool_name,
            **(attributes or {})
        }
        
        span = self.start_span(f"tool.{tool_name}", parent_id, span_attributes)
        
        # Add arguments as an event
        span.add_event("tool.arguments", {"arguments": arguments})
        
        return span
    
    def start_agent_span(self, 
                        agent_id: str, 
                        operation: str, 
                        parent_id: Optional[str] = None,
                        attributes: Optional[Dict[str, Any]] = None) -> Span:
        """
        Start a span for an agent operation.
        
        Args:
            agent_id: ID of the agent
            operation: Name of the operation
            parent_id: Optional parent span ID
            attributes: Optional span attributes
            
        Returns:
            Span: The newly created span
        """
        span_attributes = {
            "agent.id": agent_id,
            "agent.operation": operation,
            **(attributes or {})
        }
        
        return self.start_span(f"agent.{operation}", parent_id, span_attributes)
    
    def get_active_spans(self) -> Dict[str, Span]:
        """
        Get all active spans.
        
        Returns:
            Dict[str, Span]: Dictionary of active spans, keyed by span ID
        """
        return self.active_spans.copy()

def init_tracer(service_name: str = "artcafe-agent", exporter: Optional[Any] = None) -> Tracer:
    """
    Initialize the global tracer.
    
    Args:
        service_name: Name of the service for trace identification
        exporter: Optional exporter for sending traces to a backend
        
    Returns:
        Tracer: The initialized tracer
    """
    global _tracer
    
    if _tracer is None:
        _tracer = Tracer(service_name, exporter)
        logger.info(f"Initialized tracer for service {service_name}")
    
    return _tracer

def get_tracer() -> Optional[Tracer]:
    """
    Get the global tracer instance.
    
    Returns:
        Optional[Tracer]: The global tracer, or None if not initialized
    """
    return _tracer