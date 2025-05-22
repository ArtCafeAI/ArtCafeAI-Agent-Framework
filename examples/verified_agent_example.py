#!/usr/bin/env python3
"""
Verified Agent Example

Demonstrates how to build agents with verification and ground truth checks
to prevent error propagation.
"""

import asyncio
from framework import VerifiedAgent, verify_input, verify_output


class DataProcessingAgent(VerifiedAgent):
    """An agent that processes data with verification at each step."""
    
    def __init__(self):
        super().__init__(agent_type="data_processor", fail_fast=False)
        
        # Add global verification rules
        self.add_input_verifier(
            lambda msg: "data" in msg,
            topic_pattern="*"
        )
        
        # Add topic-specific rules
        self.add_input_verifier(
            lambda msg: isinstance(msg.get("data"), list),
            topic_pattern="process/list"
        )
        
        self.add_output_verifier(
            lambda output: output is not None and "processed" in output,
            topic_pattern="process/*"
        )
    
    async def process_message(self, topic: str, message):
        """Process with automatic verification."""
        if topic == "process/list":
            # This will be automatically verified
            data = message.get("data", [])
            processed = [item.upper() if isinstance(item, str) else str(item) 
                        for item in data]
            
            # Store output for verification
            self._last_message_output = {
                "processed": processed,
                "count": len(processed),
                "original_count": len(data)
            }
            
            await self.publish("process/result", self._last_message_output)
            return True
            
        return await super().process_message(topic, message)


# Example using decorators for verification
class CalculationAgent(VerifiedAgent):
    """An agent that performs calculations with verification."""
    
    @verify_input(lambda msg: all(k in msg for k in ["a", "b"]))
    @verify_output(lambda result: isinstance(result, (int, float)))
    async def add_numbers(self, message):
        """Add two numbers with verification."""
        return message["a"] + message["b"]
    
    @verify_input(lambda msg: "values" in msg and len(msg["values"]) > 0)
    @verify_output(lambda result: "average" in result)
    async def calculate_average(self, message):
        """Calculate average with verification."""
        values = message["values"]
        avg = sum(values) / len(values)
        return {"average": avg, "count": len(values)}


async def main():
    # Create and start the agent
    agent = DataProcessingAgent()
    await agent.start_async()
    
    # Test with valid data
    print("Testing with valid data:")
    await agent.messaging.publish("process/list", {
        "data": ["hello", "world", "test"]
    })
    
    # Test with invalid data (missing 'data' field)
    print("\nTesting with invalid data:")
    try:
        await agent.messaging.publish("process/list", {
            "items": ["should", "fail"]
        })
    except Exception as e:
        print(f"Caught expected error: {e}")
    
    # Check verification statistics
    stats = agent.get_verification_stats()
    print(f"\nVerification stats: {stats}")
    
    # Cleanup
    await agent.stop_async()


if __name__ == "__main__":
    asyncio.run(main())