"""
Augmented LLM Agent - Start with an LLM and add capabilities.

Following Anthropic's guidance to start with an "augmented LLM" that has
retrieval and tool use capabilities built in.
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable, Union
from .simple_agent import SimpleAgent
from ..llm.factory import get_llm_provider
from ..tools import Tool, ToolRegistry


class AugmentedLLMAgent(SimpleAgent):
    """
    An agent that starts with LLM capabilities and builds from there.
    
    This follows Anthropic's best practice of starting with an augmented LLM
    rather than complex messaging infrastructure.
    
    Example:
        ```python
        agent = AugmentedLLMAgent(
            llm_provider="anthropic",
            api_key="your-api-key"
        )
        
        @agent.tool
        def search_web(query: str) -> str:
            # Your search implementation
            return f"Results for: {query}"
        
        response = await agent.chat("Search for AI agents")
        ```
    """
    
    def __init__(
        self,
        agent_id: str = None,
        llm_provider: str = "anthropic",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize an LLM-first agent.
        
        Args:
            agent_id: Optional agent ID
            llm_provider: LLM provider name (anthropic, openai, bedrock)
            api_key: API key for the LLM provider
            model: Optional model override
            **kwargs: Additional configuration
        """
        super().__init__(agent_id=agent_id, agent_type="llm", **kwargs)
        
        # Initialize LLM provider
        llm_config = {
            "provider": llm_provider,
            llm_provider: {
                "api_key": api_key or "",
                "model": model
            }
        }
        
        self.llm = get_llm_provider(llm_config)
        self.tools = ToolRegistry()
        self.context = []  # Conversation context
        self.max_context_length = kwargs.get("max_context_length", 10)
        
        # Add retrieval capability
        self.add_capability("chat")
        self.add_capability("tool_use")
        self.add_capability("retrieval")
        
    def tool(self, func: Callable) -> Callable:
        """
        Decorator to register a tool for the LLM to use.
        
        Example:
            ```python
            @agent.tool
            def calculate(expression: str) -> float:
                return eval(expression)
            ```
        """
        tool = Tool(
            name=func.__name__,
            description=func.__doc__ or f"Tool: {func.__name__}",
            func=func
        )
        self.tools.register(tool)
        return func
    
    async def chat(
        self, 
        message: str,
        context: Optional[List[Dict[str, str]]] = None,
        use_tools: bool = True
    ) -> str:
        """
        Chat with the LLM agent.
        
        Args:
            message: User message
            context: Optional conversation context
            use_tools: Whether to allow tool use
            
        Returns:
            LLM response
        """
        # Build conversation context
        messages = context or self.context.copy()
        messages.append({"role": "user", "content": message})
        
        # Prepare tool descriptions if enabled
        tools_desc = ""
        if use_tools and self.tools.list_tools():
            tools_desc = "\n\nAvailable tools:\n"
            for tool in self.tools.list_tools():
                tools_desc += f"- {tool.name}: {tool.description}\n"
            
            messages[0] = {
                "role": "system",
                "content": f"You are a helpful AI assistant with access to tools.{tools_desc}"
            }
        
        # Generate response
        response = await self.llm.chat(messages)
        
        # Check if response requests tool use
        if use_tools and self._contains_tool_request(response):
            tool_result = await self._execute_tools(response)
            
            # Add tool result to context and get final response
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Tool result: {tool_result}"})
            response = await self.llm.chat(messages)
        
        # Update context
        self.context = messages[-self.max_context_length:]
        self.context.append({"role": "assistant", "content": response})
        
        return response
    
    async def retrieve(
        self,
        query: str,
        source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information for a query.
        
        This is a placeholder for RAG functionality. Override in subclasses
        to implement actual retrieval from vector stores, databases, etc.
        
        Args:
            query: Search query
            source: Optional source to search in
            
        Returns:
            List of relevant documents/chunks
        """
        # Publish retrieval request for other agents to handle
        await self.publish("retrieval/request", {
            "query": query,
            "source": source,
            "agent_id": self.agent_id
        })
        
        # In a real implementation, this would search vector stores
        return []
    
    async def think(
        self,
        task: str,
        max_steps: int = 5
    ) -> Dict[str, Any]:
        """
        Use chain-of-thought reasoning to solve a task.
        
        Args:
            task: Task description
            max_steps: Maximum reasoning steps
            
        Returns:
            Dictionary with reasoning steps and final answer
        """
        reasoning_prompt = f"""
        Task: {task}
        
        Think through this step-by-step:
        1. Understand what is being asked
        2. Break down the problem
        3. Consider what tools or information you need
        4. Work through the solution
        5. Provide a clear answer
        
        Show your reasoning at each step.
        """
        
        response = await self.chat(reasoning_prompt, use_tools=True)
        
        return {
            "task": task,
            "reasoning": response,
            "tools_used": [t.name for t in self.tools.list_tools()],
            "timestamp": asyncio.get_event_loop().time()
        }
    
    def _contains_tool_request(self, response: str) -> bool:
        """Check if the response contains a tool use request."""
        # Simple heuristic - improve this for production
        tool_names = [tool.name for tool in self.tools.list_tools()]
        return any(f"use {name}" in response.lower() for name in tool_names)
    
    async def _execute_tools(self, response: str) -> str:
        """Execute requested tools from the response."""
        # This is a simple implementation - enhance for production
        results = []
        
        for tool in self.tools.list_tools():
            if tool.name in response:
                try:
                    # Extract arguments (simplified)
                    result = await tool.func()
                    results.append(f"{tool.name}: {result}")
                except Exception as e:
                    results.append(f"{tool.name} error: {str(e)}")
        
        return "; ".join(results) if results else "No tools executed"
    
    async def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """Process messages with LLM reasoning."""
        if topic == "chat/request":
            # Handle chat requests
            response = await self.chat(message.get("content", ""))
            await self.publish("chat/response", {
                "content": response,
                "agent_id": self.agent_id
            })
            return True
        
        elif topic == "think/request":
            # Handle reasoning requests
            result = await self.think(message.get("task", ""))
            await self.publish("think/response", result)
            return True
        
        return await super().process_message(topic, message)


def create_llm_agent(
    provider: str = "anthropic",
    api_key: Optional[str] = None,
    **kwargs
) -> AugmentedLLMAgent:
    """
    Factory function to create an LLM-first agent.
    
    Example:
        ```python
        from artcafe import create_llm_agent
        
        agent = create_llm_agent(
            provider="anthropic",
            api_key="your-key"
        )
        
        response = await agent.chat("Hello!")
        ```
    """
    return AugmentedLLMAgent(
        llm_provider=provider,
        api_key=api_key,
        **kwargs
    )