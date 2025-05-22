#!/usr/bin/env python3

import logging
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("AgentFramework.Telemetry.Metrics")

# Global metrics collector instance
_metrics_collector = None

class MetricsCollector:
    """
    Collector for agent and LLM metrics.
    
    This class collects and aggregates metrics from agents and LLM interactions,
    and can export them to various metrics backends.
    """
    
    def __init__(self, 
                service_name: str = "artcafe-agent", 
                exporter: Optional[Any] = None):
        """
        Initialize a new metrics collector.
        
        Args:
            service_name: Name of the service for metrics identification
            exporter: Optional exporter for sending metrics to a backend
        """
        self.service_name = service_name
        self.exporter = exporter
        
        # Metrics storage
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
        
        # Initialize default metrics
        self._init_default_metrics()
    
    def _init_default_metrics(self) -> None:
        """Initialize default metrics."""
        # Agent metrics
        self.create_counter("agent.message.count", "Number of messages processed by agents")
        self.create_counter("agent.tool.count", "Number of tool executions by agents")
        self.create_counter("agent.error.count", "Number of errors encountered by agents")
        
        # LLM metrics
        self.create_counter("llm.request.count", "Number of requests to LLM providers")
        self.create_counter("llm.token.count", "Number of tokens processed by LLMs")
        self.create_counter("llm.error.count", "Number of errors from LLM providers")
        
        # Performance metrics
        self.create_histogram("llm.latency", "Latency of LLM requests in seconds")
        self.create_histogram("tool.latency", "Latency of tool executions in seconds")
    
    def create_counter(self, name: str, description: str, labels: Optional[List[str]] = None) -> None:
        """
        Create a new counter metric.
        
        Args:
            name: Name of the metric
            description: Description of the metric
            labels: Optional list of label names for the metric
        """
        self.counters[name] = {
            "description": description,
            "labels": labels or [],
            "values": {}
        }
    
    def create_gauge(self, name: str, description: str, labels: Optional[List[str]] = None) -> None:
        """
        Create a new gauge metric.
        
        Args:
            name: Name of the metric
            description: Description of the metric
            labels: Optional list of label names for the metric
        """
        self.gauges[name] = {
            "description": description,
            "labels": labels or [],
            "values": {}
        }
    
    def create_histogram(self, name: str, description: str, labels: Optional[List[str]] = None) -> None:
        """
        Create a new histogram metric.
        
        Args:
            name: Name of the metric
            description: Description of the metric
            labels: Optional list of label names for the metric
        """
        self.histograms[name] = {
            "description": description,
            "labels": labels or [],
            "values": {},
            "sum": {},
            "count": {}
        }
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Name of the metric
            value: Value to increment by
            labels: Optional labels for the metric
        """
        if name not in self.counters:
            logger.warning(f"Counter {name} not found")
            return
        
        label_key = self._get_label_key(labels)
        
        if label_key not in self.counters[name]["values"]:
            self.counters[name]["values"][label_key] = 0.0
        
        self.counters[name]["values"][label_key] += value
        
        # Export if exporter configured
        if self.exporter:
            self._export_metric("counter", name, self.counters[name]["values"][label_key], labels)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric.
        
        Args:
            name: Name of the metric
            value: Value to set
            labels: Optional labels for the metric
        """
        if name not in self.gauges:
            logger.warning(f"Gauge {name} not found")
            return
        
        label_key = self._get_label_key(labels)
        
        self.gauges[name]["values"][label_key] = value
        
        # Export if exporter configured
        if self.exporter:
            self._export_metric("gauge", name, value, labels)
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a value in a histogram metric.
        
        Args:
            name: Name of the metric
            value: Value to record
            labels: Optional labels for the metric
        """
        if name not in self.histograms:
            logger.warning(f"Histogram {name} not found")
            return
        
        label_key = self._get_label_key(labels)
        
        if label_key not in self.histograms[name]["values"]:
            self.histograms[name]["values"][label_key] = []
            self.histograms[name]["sum"][label_key] = 0.0
            self.histograms[name]["count"][label_key] = 0
        
        self.histograms[name]["values"][label_key].append(value)
        self.histograms[name]["sum"][label_key] += value
        self.histograms[name]["count"][label_key] += 1
        
        # Export if exporter configured
        if self.exporter:
            self._export_metric("histogram", name, value, labels)
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        Get the current value of a counter metric.
        
        Args:
            name: Name of the metric
            labels: Optional labels for the metric
            
        Returns:
            float: Current value of the counter
        """
        if name not in self.counters:
            logger.warning(f"Counter {name} not found")
            return 0.0
        
        label_key = self._get_label_key(labels)
        
        return self.counters[name]["values"].get(label_key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        Get the current value of a gauge metric.
        
        Args:
            name: Name of the metric
            labels: Optional labels for the metric
            
        Returns:
            float: Current value of the gauge
        """
        if name not in self.gauges:
            logger.warning(f"Gauge {name} not found")
            return 0.0
        
        label_key = self._get_label_key(labels)
        
        return self.gauges[name]["values"].get(label_key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """
        Get statistics for a histogram metric.
        
        Args:
            name: Name of the metric
            labels: Optional labels for the metric
            
        Returns:
            Dict[str, float]: Statistics for the histogram
        """
        if name not in self.histograms:
            logger.warning(f"Histogram {name} not found")
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
        
        label_key = self._get_label_key(labels)
        
        values = self.histograms[name]["values"].get(label_key, [])
        count = self.histograms[name]["count"].get(label_key, 0)
        sum_value = self.histograms[name]["sum"].get(label_key, 0.0)
        
        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
        
        return {
            "count": count,
            "sum": sum_value,
            "avg": sum_value / count,
            "min": min(values),
            "max": max(values)
        }
    
    def _get_label_key(self, labels: Optional[Dict[str, str]] = None) -> str:
        """
        Get a unique key for a set of labels.
        
        Args:
            labels: Optional labels for the metric
            
        Returns:
            str: Unique key for the labels
        """
        if not labels:
            return ""
        
        # Sort labels by key for consistent key generation
        sorted_labels = sorted(labels.items())
        
        return ",".join(f"{k}={v}" for k, v in sorted_labels)
    
    def _export_metric(self, 
                      metric_type: str, 
                      name: str, 
                      value: Any, 
                      labels: Optional[Dict[str, str]] = None) -> None:
        """
        Export a metric to the configured backend.
        
        Args:
            metric_type: Type of metric (counter, gauge, histogram)
            name: Name of the metric
            value: Value of the metric
            labels: Optional labels for the metric
        """
        if not self.exporter:
            return
            
        try:
            self.exporter.export_metric(metric_type, name, value, labels or {})
        except Exception as e:
            logger.error(f"Error exporting metric: {str(e)}")
    
    def record_llm_request(self, 
                         model: str, 
                         tokens: int, 
                         latency: float, 
                         success: bool = True) -> None:
        """
        Record metrics for an LLM request.
        
        Args:
            model: Name of the LLM model
            tokens: Number of tokens processed
            latency: Latency of the request in seconds
            success: Whether the request was successful
        """
        labels = {"model": model}
        
        # Increment request count
        self.increment_counter("llm.request.count", 1.0, labels)
        
        # Increment token count
        self.increment_counter("llm.token.count", float(tokens), labels)
        
        # Record latency
        self.record_histogram("llm.latency", latency, labels)
        
        # Increment error count if needed
        if not success:
            self.increment_counter("llm.error.count", 1.0, labels)
    
    def record_tool_execution(self, 
                            tool_name: str, 
                            latency: float, 
                            success: bool = True) -> None:
        """
        Record metrics for a tool execution.
        
        Args:
            tool_name: Name of the tool
            latency: Latency of the execution in seconds
            success: Whether the execution was successful
        """
        labels = {"tool": tool_name}
        
        # Increment tool count
        self.increment_counter("agent.tool.count", 1.0, labels)
        
        # Record latency
        self.record_histogram("tool.latency", latency, labels)
        
        # Increment error count if needed
        if not success:
            self.increment_counter("agent.error.count", 1.0, labels)

def init_metrics(service_name: str = "artcafe-agent", exporter: Optional[Any] = None) -> MetricsCollector:
    """
    Initialize the global metrics collector.
    
    Args:
        service_name: Name of the service for metrics identification
        exporter: Optional exporter for sending metrics to a backend
        
    Returns:
        MetricsCollector: The initialized metrics collector
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(service_name, exporter)
        logger.info(f"Initialized metrics collector for service {service_name}")
    
    return _metrics_collector

def get_metrics_collector() -> Optional[MetricsCollector]:
    """
    Get the global metrics collector instance.
    
    Returns:
        Optional[MetricsCollector]: The global metrics collector, or None if not initialized
    """
    return _metrics_collector