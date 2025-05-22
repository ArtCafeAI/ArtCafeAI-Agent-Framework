#!/usr/bin/env python3
"""
LLM-First Example

Demonstrates starting with an augmented LLM and adding capabilities,
following Anthropic's best practices.
"""

import asyncio
import os
from framework import create_llm_agent


async def main():
    # Create an LLM agent (uses environment variable for API key)
    agent = create_llm_agent(
        provider="anthropic",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )
    
    # Add tools that the LLM can use
    @agent.tool
    def calculate(expression: str) -> float:
        """Safely evaluate a mathematical expression."""
        # In production, use a safe math parser
        allowed_chars = "0123456789+-*/(). "
        if all(c in allowed_chars for c in expression):
            return eval(expression)
        else:
            raise ValueError("Invalid expression")
    
    @agent.tool
    def get_weather(city: str) -> str:
        """Get current weather for a city (mock implementation)."""
        # In production, call a weather API
        return f"The weather in {city} is sunny and 72°F"
    
    # Chat with the agent
    print("LLM Agent ready. Type 'quit' to exit.\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
            
        response = await agent.chat(user_input)
        print(f"Agent: {response}\n")
    
    # Example of using the think method for complex reasoning
    task = "Plan a weekend trip to Paris including flights, hotel, and activities"
    print(f"\nComplex task: {task}")
    result = await agent.think(task)
    print(f"Agent reasoning: {result['reasoning']}")


if __name__ == "__main__":
    asyncio.run(main())