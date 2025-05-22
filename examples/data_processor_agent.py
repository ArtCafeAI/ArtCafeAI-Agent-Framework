#!/usr/bin/env python3
"""
Data Processor Agent Template

This agent demonstrates how to process data tasks, handle errors,
and report progress back to the ArtCafe platform.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from artcafe_agent import ArtCafeAgent


class DataProcessorAgent(ArtCafeAgent):
    """
    Example agent that processes data tasks.
    
    Features:
    - Batch data processing
    - Progress reporting
    - Error handling
    - Metrics tracking
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(
            agent_id=config["agent_id"],
            tenant_id=config["tenant_id"],
            private_key_path=config["private_key_path"],
            api_endpoint=config.get("api_endpoint", "https://api.artcafe.ai"),
            log_level=config.get("log_level", "INFO"),
            heartbeat_interval=config.get("heartbeat_interval", 30)
        )
        
        # Register command handlers
        self.register_command("process_batch", self.handle_process_batch)
        self.register_command("process_stream", self.handle_process_stream)
        self.register_command("get_stats", self.handle_get_stats)
        self.register_command("clear_stats", self.handle_clear_stats)
        
        # Initialize state
        self.processing = False
        self.current_task_id = None
        self.stats = {
            "batches_processed": 0,
            "items_processed": 0,
            "errors": 0,
            "total_processing_time": 0,
            "start_time": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"Data Processor Agent initialized: {agent_id}")
    
    async def handle_process_batch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a batch of data items.
        
        Args:
            args: Command arguments containing:
                - data: List of items to process
                - task_id: Unique task identifier
                - options: Processing options (optional)
        
        Returns:
            Result dictionary with processed data
        """
        if self.processing:
            return {
                "status": "error",
                "error": "Agent is already processing a task",
                "current_task": self.current_task_id
            }
        
        # Extract arguments
        data = args.get("data", [])
        task_id = args.get("task_id", f"task-{int(time.time())}")
        options = args.get("options", {})
        
        if not isinstance(data, list):
            return {
                "status": "error",
                "error": "Data must be a list"
            }
        
        # Start processing
        self.processing = True
        self.current_task_id = task_id
        start_time = time.time()
        
        try:
            # Update status
            await self.update_status("busy", task_id=task_id, progress=0)
            
            # Process items
            results = []
            errors = []
            
            for i, item in enumerate(data):
                try:
                    # Process individual item
                    result = await self._process_item(item, options)
                    results.append(result)
                    
                    # Update progress
                    progress = int((i + 1) / len(data) * 100)
                    await self.update_status("busy", task_id=task_id, progress=progress)
                    
                except Exception as e:
                    self.logger.error(f"Error processing item {i}: {e}")
                    errors.append({
                        "index": i,
                        "error": str(e),
                        "item": item
                    })
                    self.stats["errors"] += 1
            
            # Update statistics
            processing_time = time.time() - start_time
            self.stats["batches_processed"] += 1
            self.stats["items_processed"] += len(results)
            self.stats["total_processing_time"] += processing_time
            
            # Return results
            return {
                "status": "success",
                "task_id": task_id,
                "processed": len(results),
                "errors": len(errors),
                "results": results,
                "error_details": errors if errors else None,
                "processing_time": processing_time
            }
        
        except Exception as e:
            self.logger.error(f"Batch processing error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "task_id": task_id
            }
        
        finally:
            # Reset state
            self.processing = False
            self.current_task_id = None
            await self.update_status("online")
    
    async def handle_process_stream(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a stream of data items.
        
        This demonstrates how to handle streaming data processing
        where items arrive over time.
        """
        stream_id = args.get("stream_id")
        topic = args.get("topic", f"streams/{stream_id}")
        
        if not stream_id:
            return {
                "status": "error",
                "error": "stream_id is required"
            }
        
        # Subscribe to the stream
        async def process_stream_item(message):
            try:
                item = message.get("data")
                result = await self._process_item(item, {})
                
                # Publish result
                await self.publish(f"results/{stream_id}", {
                    "stream_id": stream_id,
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                self.stats["items_processed"] += 1
                
            except Exception as e:
                self.logger.error(f"Stream processing error: {e}")
                self.stats["errors"] += 1
                
                # Publish error
                await self.publish(f"errors/{stream_id}", {
                    "stream_id": stream_id,
                    "error": str(e),
                    "item": item,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Subscribe to stream
        subscription = await self.subscribe(topic, process_stream_item)
        
        return {
            "status": "success",
            "stream_id": stream_id,
            "topic": topic,
            "message": "Stream processing started"
        }
    
    async def handle_get_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get agent statistics."""
        # Calculate averages
        avg_processing_time = 0
        if self.stats["batches_processed"] > 0:
            avg_processing_time = (
                self.stats["total_processing_time"] / 
                self.stats["batches_processed"]
            )
        
        error_rate = 0
        total_items = self.stats["items_processed"] + self.stats["errors"]
        if total_items > 0:
            error_rate = self.stats["errors"] / total_items
        
        return {
            "status": "success",
            "stats": {
                **self.stats,
                "average_processing_time": avg_processing_time,
                "error_rate": error_rate,
                "uptime": self.get_uptime(),
                "current_status": self.status,
                "processing": self.processing
            }
        }
    
    async def handle_clear_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Clear agent statistics."""
        self.stats = {
            "batches_processed": 0,
            "items_processed": 0,
            "errors": 0,
            "total_processing_time": 0,
            "start_time": datetime.utcnow().isoformat()
        }
        
        return {
            "status": "success",
            "message": "Statistics cleared"
        }
    
    async def _process_item(self, item: Any, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an individual data item.
        
        This is where you implement your actual data processing logic.
        """
        # Simulate processing time
        processing_delay = options.get("processing_delay", 0.1)
        await asyncio.sleep(processing_delay)
        
        # Example: Transform the data
        if isinstance(item, dict):
            result = {
                "original": item,
                "processed": {
                    k: v.upper() if isinstance(v, str) else v
                    for k, v in item.items()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        elif isinstance(item, str):
            result = {
                "original": item,
                "processed": item.upper(),
                "length": len(item),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            result = {
                "original": item,
                "processed": str(item),
                "type": type(item).__name__,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return result
    
    def get_uptime(self) -> float:
        """Get agent uptime in seconds."""
        if hasattr(self, '_start_time'):
            return time.time() - self._start_time
        return 0


async def main():
    """Main entry point."""
    # Load configuration
    config = {
        "agent_id": "data-processor-001",
        "tenant_id": "your-tenant-id",  # Replace with actual tenant ID
        "private_key_path": "~/.ssh/artcafe_agent_key",  # Replace with actual key path
        "api_endpoint": "https://api.artcafe.ai",
        "log_level": "INFO"
    }
    
    # Try to load from file
    try:
        with open("agent_config.json") as f:
            config.update(json.load(f))
    except FileNotFoundError:
        print("No config file found, using defaults")
    
    # Create and start agent
    agent = DataProcessorAgent(config)
    
    try:
        print(f"Starting Data Processor Agent: {config['agent_id']}")
        await agent.start()
    except KeyboardInterrupt:
        print("\nShutting down agent...")
        await agent.stop()
    except Exception as e:
        print(f"Agent error: {e}")
        await agent.stop()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the agent
    asyncio.run(main())