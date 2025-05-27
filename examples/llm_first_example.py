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
        # Using a simple parser for basic math operations
        # For production, consider using libraries like numexpr or simpleeval
        import re
        
        # Validate expression contains only allowed characters
        if not re.match(r'^[\d\s\+\-\*/\(\)\.]+$', expression):
            raise ValueError("Invalid expression - only numbers and basic operators allowed")
        
        # For this example, we'll just handle simple cases
        # In production, use a proper math expression parser
        try:
            # Remove whitespace
            expr = expression.replace(' ', '')
            
            # Very basic validation and computation
            # This is still limited but safer than eval()
            if '+' in expr and not any(op in expr for op in ['*', '/', '-', '(', ')']):
                parts = expr.split('+')
                return sum(float(p) for p in parts)
            elif '-' in expr and not any(op in expr for op in ['*', '/', '+', '(', ')']):
                parts = expr.split('-')
                result = float(parts[0])
                for p in parts[1:]:
                    result -= float(p)
                return result
            elif '*' in expr and not any(op in expr for op in ['/', '+', '-', '(', ')']):
                parts = expr.split('*')
                result = 1.0
                for p in parts:
                    result *= float(p)
                return result
            elif '/' in expr and not any(op in expr for op in ['*', '+', '-', '(', ')']):
                parts = expr.split('/')
                result = float(parts[0])
                for p in parts[1:]:
                    if float(p) == 0:
                        raise ValueError("Division by zero")
                    result /= float(p)
                return result
            else:
                # Just a number
                return float(expr)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Cannot evaluate expression: {e}")
    
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