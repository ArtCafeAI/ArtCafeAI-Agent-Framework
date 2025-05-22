#!/usr/bin/env python3
"""
Simple Hello World Example

Demonstrates the simplest way to create an agent with the ArtCafe framework.
This follows Anthropic's recommendation to "start simple".
"""

from framework import create_agent


def main():
    # Create a simple agent with minimal configuration
    agent = create_agent("hello-agent")
    
    # Register a message handler using decorator
    @agent.on_message("greet")
    def handle_greeting(message):
        name = message.get("name", "World")
        return {
            "greeting": f"Hello, {name}!",
            "agent": agent.agent_id
        }
    
    # Register another handler
    @agent.on_message("calculate/*")
    def handle_calculation(message):
        operation = message.get("operation", "add")
        a = message.get("a", 0)
        b = message.get("b", 0)
        
        if operation == "add":
            result = a + b
        elif operation == "multiply":
            result = a * b
        else:
            result = None
            
        return {"result": result, "operation": operation}
    
    print(f"Starting {agent.agent_id}...")
    print("Press Ctrl+C to stop")
    
    # Run the agent (blocks until interrupted)
    agent.run()


if __name__ == "__main__":
    main()