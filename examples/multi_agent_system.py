#!/usr/bin/env python3

"""
Multi-Agent System Example

This example demonstrates how to create a system of multiple agents
that collaborate through the messaging system.
"""

import asyncio
import logging
import os
import sys
import json
import random

# Add parent directory to path to allow importing the framework
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from artcafe.framework.core.enhanced_agent import EnhancedAgent
from artcafe.framework.core.config import AgentConfig
from artcafe.framework.event_loop import EventLoop
from artcafe.framework.event_loop.callback import ConsoleCallbackHandler
from artcafe.framework.llm import get_llm_provider
from artcafe.framework.tools import tool, ToolRegistry, ToolHandler

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MultiAgentSystem")

# ------------------------------------------------------------------------
# Agent 1: Data Gathering Agent
# ------------------------------------------------------------------------

class DataGatheringAgent(EnhancedAgent):
    """An agent that gathers and provides data."""
    
    def __init__(self, agent_id=None, config=None):
        """Initialize the data gathering agent."""
        super().__init__(agent_id=agent_id, agent_type="data_gatherer", config=config)
        
        # Add capabilities
        self.add_capability("data_gathering")
        
        # Data sources (simplified for the example)
        self.data_sources = {
            "weather": ["sunny", "cloudy", "rainy", "snowy", "windy"],
            "stock_prices": [
                {"symbol": "AAPL", "price": 150 + random.random() * 20},
                {"symbol": "GOOGL", "price": 2500 + random.random() * 100},
                {"symbol": "AMZN", "price": 3000 + random.random() * 200},
                {"symbol": "MSFT", "price": 280 + random.random() * 30},
                {"symbol": "TSLA", "price": 700 + random.random() * 50},
            ],
            "news_topics": ["technology", "business", "science", "health", "politics"]
        }
    
    async def process_message(self, topic, message):
        """Process incoming messages."""
        # Call parent method for basic processing
        if await super().process_message(topic, message):
            # Handle data requests
            if topic == "data/request":
                await self._handle_data_request(message)
                return True
            # Handle discovery requests
            elif topic == "agents/discovery/requests":
                self._respond_to_discovery(message.get("data", {}))
                return True
        return False
    
    async def _handle_data_request(self, message):
        """Handle data requests."""
        try:
            data_type = message.get("data_type")
            if not data_type:
                logger.warning("Received data request without data type")
                await self.publish("data/error", {
                    "error": "No data type specified",
                    "agent_id": self.agent_id
                })
                return
            
            # Get the requested data
            if data_type in self.data_sources:
                data = self.data_sources[data_type]
                
                # For demonstration, update stock prices with random fluctuations
                if data_type == "stock_prices":
                    for stock in data:
                        # Add small random fluctuation
                        stock["price"] += (random.random() - 0.5) * 10
                        stock["price"] = round(stock["price"], 2)
                
                # Publish the data
                await self.publish("data/response", {
                    "data_type": data_type,
                    "data": data,
                    "timestamp": asyncio.get_event_loop().time(),
                    "agent_id": self.agent_id
                })
                
                logger.info(f"Sent {data_type} data")
            else:
                logger.warning(f"Unknown data type requested: {data_type}")
                await self.publish("data/error", {
                    "error": f"Unknown data type: {data_type}",
                    "agent_id": self.agent_id
                })
        except Exception as e:
            logger.error(f"Error handling data request: {str(e)}")
            await self.publish("data/error", {
                "error": str(e),
                "agent_id": self.agent_id
            })

# ------------------------------------------------------------------------
# Agent 2: Analysis Agent
# ------------------------------------------------------------------------

class AnalysisAgent(EnhancedAgent):
    """An agent that analyzes data."""
    
    def __init__(self, agent_id=None, config=None):
        """Initialize the analysis agent."""
        super().__init__(agent_id=agent_id, agent_type="analyzer", config=config)
        
        # Add capabilities
        self.add_capability("data_analysis")
        
        # Initialize LLM provider
        self.llm = get_llm_provider(self.config.get("llm", {}))
        
        # Initialize event loop
        self.event_loop = EventLoop(
            llm_provider=self.llm,
            callback_handler=ConsoleCallbackHandler(verbose=False)
        )
        
        # Initialize data cache
        self.data_cache = {}
    
    async def process_message(self, topic, message):
        """Process incoming messages."""
        # Call parent method for basic processing
        if await super().process_message(topic, message):
            # Handle data responses
            if topic == "data/response":
                await self._handle_data_response(message)
                return True
            # Handle analysis requests
            elif topic == "analysis/request":
                await self._handle_analysis_request(message)
                return True
            # Handle discovery requests
            elif topic == "agents/discovery/requests":
                self._respond_to_discovery(message.get("data", {}))
                return True
        return False
    
    async def _handle_data_response(self, message):
        """Handle data responses from the data gathering agent."""
        data_type = message.get("data_type")
        data = message.get("data")
        
        if data_type and data:
            # Cache the data
            self.data_cache[data_type] = {
                "data": data,
                "timestamp": message.get("timestamp", asyncio.get_event_loop().time())
            }
            
            logger.info(f"Cached {data_type} data from agent {message.get('agent_id')}")
    
    async def _handle_analysis_request(self, message):
        """Handle analysis requests."""
        try:
            analysis_type = message.get("analysis_type")
            data_type = message.get("data_type")
            
            if not analysis_type or not data_type:
                logger.warning("Received analysis request without analysis or data type")
                await self.publish("analysis/error", {
                    "error": "Analysis and data type are required",
                    "agent_id": self.agent_id
                })
                return
            
            # Check if we have the requested data
            if data_type not in self.data_cache:
                # Request the data from the data gathering agent
                await self.publish("data/request", {
                    "data_type": data_type,
                    "agent_id": self.agent_id
                })
                
                # Wait for data to arrive (with timeout)
                start_time = asyncio.get_event_loop().time()
                while data_type not in self.data_cache and asyncio.get_event_loop().time() - start_time < 10:
                    await asyncio.sleep(0.5)
                
                if data_type not in self.data_cache:
                    logger.warning(f"Timed out waiting for {data_type} data")
                    await self.publish("analysis/error", {
                        "error": f"Could not retrieve {data_type} data",
                        "agent_id": self.agent_id
                    })
                    return
            
            # Get the data
            data = self.data_cache[data_type]["data"]
            
            # Perform the analysis using LLM
            prompt = f"""
            Analyze the following {data_type} data: {json.dumps(data)}
            
            Provide a brief {analysis_type} analysis of this data.
            Keep your response concise and focused on the key insights.
            """
            
            conversation = []
            response, _ = await self.event_loop.process_message(
                user_message=prompt,
                conversation_history=conversation,
                system_prompt="You are a data analysis assistant. Provide clear, concise analyses."
            )
            
            # Publish the analysis results
            await self.publish("analysis/response", {
                "analysis_type": analysis_type,
                "data_type": data_type,
                "analysis": response,
                "agent_id": self.agent_id
            })
            
            logger.info(f"Sent {analysis_type} analysis of {data_type} data")
            
        except Exception as e:
            logger.error(f"Error handling analysis request: {str(e)}")
            await self.publish("analysis/error", {
                "error": str(e),
                "agent_id": self.agent_id
            })

# ------------------------------------------------------------------------
# Agent 3: Client-Facing Agent
# ------------------------------------------------------------------------

class ClientAgent(EnhancedAgent):
    """An agent that interacts with clients and coordinates with other agents."""
    
    def __init__(self, agent_id=None, config=None):
        """Initialize the client agent."""
        super().__init__(agent_id=agent_id, agent_type="client_agent", config=config)
        
        # Add capabilities
        self.add_capability("client_interaction")
        self.add_capability("agent_coordination")
        
        # Initialize LLM provider
        self.llm = get_llm_provider(self.config.get("llm", {}))
        
        # Initialize event loop
        self.event_loop = EventLoop(
            llm_provider=self.llm,
            callback_handler=ConsoleCallbackHandler(verbose=False)
        )
        
        # Initialize conversations and response tracking
        self.conversations = {}
        self.pending_responses = {}
    
    async def process_message(self, topic, message):
        """Process incoming messages."""
        # Call parent method for basic processing
        if await super().process_message(topic, message):
            # Handle client requests
            if topic.startswith("client/request"):
                await self._handle_client_request(topic, message)
                return True
            # Handle analysis responses
            elif topic == "analysis/response":
                await self._handle_analysis_response(message)
                return True
            # Handle discovery requests
            elif topic == "agents/discovery/requests":
                self._respond_to_discovery(message.get("data", {}))
                return True
        return False
    
    async def _handle_client_request(self, topic, message):
        """Handle client requests."""
        try:
            # Extract client ID from topic
            parts = topic.split('/')
            if len(parts) >= 3:
                client_id = parts[2]
            else:
                client_id = "default"
            
            # Get or initialize conversation
            if client_id not in self.conversations:
                self.conversations[client_id] = []
            
            # Get client message
            client_message = message.get("message", "")
            if not client_message:
                logger.warning("Received empty client request")
                return
            
            logger.info(f"Processing request from client {client_id}: {client_message}")
            
            # Process message through LLM to understand the request
            system_prompt = """
            You are a helpful assistant in a multi-agent system. Your role is to:
            1. Understand what the client is asking for
            2. Determine if we need data and analysis from other agents
            3. If so, specify what data_type and analysis_type we need
            4. If not, respond directly to the client's question
            
            Available data types: weather, stock_prices, news_topics
            Available analysis types: summary, trend, comparison, forecast
            
            Respond in JSON format with the following structure:
            {
                "needs_data": true/false,
                "data_type": "weather/stock_prices/news_topics",
                "analysis_type": "summary/trend/comparison/forecast",
                "direct_response": "Your direct response if no data needed"
            }
            """
            
            response, updated_history = await self.event_loop.process_message(
                user_message=client_message,
                conversation_history=self.conversations[client_id],
                system_prompt=system_prompt
            )
            
            # Update conversation history
            self.conversations[client_id] = updated_history
            
            # Parse the response to determine next actions
            try:
                parsed_response = json.loads(response)
                
                if parsed_response.get("needs_data", False):
                    # Request analysis from the analysis agent
                    data_type = parsed_response.get("data_type")
                    analysis_type = parsed_response.get("analysis_type")
                    
                    if data_type and analysis_type:
                        # Track the pending response
                        response_id = f"{client_id}_{data_type}_{analysis_type}"
                        self.pending_responses[response_id] = {
                            "client_id": client_id,
                            "data_type": data_type,
                            "analysis_type": analysis_type,
                            "request_time": asyncio.get_event_loop().time()
                        }
                        
                        # Request the analysis
                        await self.publish("analysis/request", {
                            "data_type": data_type,
                            "analysis_type": analysis_type,
                            "agent_id": self.agent_id
                        })
                        
                        # Inform client that we're processing their request
                        await self.publish(f"client/response/{client_id}", {
                            "message": f"I'm retrieving {analysis_type} analysis of {data_type} data for you. This will take a moment...",
                            "agent_id": self.agent_id,
                            "is_final": False
                        })
                        
                        logger.info(f"Requested {analysis_type} analysis of {data_type} data for client {client_id}")
                    else:
                        # Handle missing data or analysis type
                        await self.publish(f"client/response/{client_id}", {
                            "message": "I couldn't determine what data or analysis you need. Could you please clarify your request?",
                            "agent_id": self.agent_id,
                            "is_final": True
                        })
                else:
                    # Provide direct response to client
                    direct_response = parsed_response.get("direct_response", "I don't have a response for that.")
                    
                    await self.publish(f"client/response/{client_id}", {
                        "message": direct_response,
                        "agent_id": self.agent_id,
                        "is_final": True
                    })
                    
                    logger.info(f"Sent direct response to client {client_id}")
                    
            except json.JSONDecodeError:
                # Handle invalid JSON response from LLM
                await self.publish(f"client/response/{client_id}", {
                    "message": "I'm having trouble understanding your request. Could you please rephrase it?",
                    "agent_id": self.agent_id,
                    "is_final": True
                })
                
                logger.warning(f"Failed to parse LLM response as JSON: {response}")
            
        except Exception as e:
            logger.error(f"Error handling client request: {str(e)}")
            # Send error response to client
            await self.publish(f"client/response/{client_id}", {
                "message": f"Sorry, I encountered an error processing your request: {str(e)}",
                "agent_id": self.agent_id,
                "is_final": True
            })
    
    async def _handle_analysis_response(self, message):
        """Handle analysis responses from the analysis agent."""
        data_type = message.get("data_type")
        analysis_type = message.get("analysis_type")
        analysis = message.get("analysis")
        
        # Find matching pending response
        for response_id, pending in list(self.pending_responses.items()):
            if pending["data_type"] == data_type and pending["analysis_type"] == analysis_type:
                client_id = pending["client_id"]
                
                # Build response message
                response_message = f"Here's the {analysis_type} analysis of {data_type} data you requested:\n\n{analysis}"
                
                # Send response to client
                await self.publish(f"client/response/{client_id}", {
                    "message": response_message,
                    "agent_id": self.agent_id,
                    "data_type": data_type,
                    "analysis_type": analysis_type,
                    "is_final": True
                })
                
                logger.info(f"Sent {analysis_type} analysis of {data_type} data to client {client_id}")
                
                # Remove from pending responses
                del self.pending_responses[response_id]

async def main():
    """Run the multi-agent system."""
    # Create configuration
    config = AgentConfig()
    
    # Set LLM configuration (using Anthropic by default)
    config.set("llm.provider", "anthropic")
    config.set("llm.model", "claude-3-opus-20240229")
    
    # Create agents
    data_agent = DataGatheringAgent(agent_id="data_agent", config=config)
    analysis_agent = AnalysisAgent(agent_id="analysis_agent", config=config)
    client_agent = ClientAgent(agent_id="client_agent", config=config)
    
    # Start agents
    await data_agent.start()
    await analysis_agent.start()
    await client_agent.start()
    
    logger.info("All agents started")
    
    try:
        # Set up subscriptions
        await data_agent.subscribe("data/request")
        await data_agent.subscribe("agents/discovery/requests")
        
        await analysis_agent.subscribe("data/response")
        await analysis_agent.subscribe("analysis/request")
        await analysis_agent.subscribe("agents/discovery/requests")
        
        await client_agent.subscribe("client/request/#")
        await client_agent.subscribe("analysis/response")
        await client_agent.subscribe("agents/discovery/requests")
        
        # Broadcast agent presence
        await data_agent.publish("agents/presence/online", {
            "agent_id": data_agent.agent_id,
            "agent_type": data_agent.agent_type,
            "capabilities": data_agent.get_capabilities()
        })
        
        await analysis_agent.publish("agents/presence/online", {
            "agent_id": analysis_agent.agent_id,
            "agent_type": analysis_agent.agent_type,
            "capabilities": analysis_agent.get_capabilities()
        })
        
        await client_agent.publish("agents/presence/online", {
            "agent_id": client_agent.agent_id,
            "agent_type": client_agent.agent_type,
            "capabilities": client_agent.get_capabilities()
        })
        
        # Simulate client requests
        client_requests = [
            "What's the weather like today?",
            "Can you give me a summary of the current stock prices?",
            "What are the trending news topics?",
            "I'm looking for investment advice based on the latest stock market data.",
        ]
        
        for i, request in enumerate(client_requests):
            client_id = f"client_{i+1}"
            
            # Send client request
            await client_agent.publish(f"client/request/{client_id}", {
                "message": request,
                "client_id": client_id
            })
            
            # Wait a bit between requests
            await asyncio.sleep(10)
        
        # Keep the system running for a while to process all requests
        logger.info("Waiting for all requests to be processed...")
        await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        logger.info("Stopping agents...")
    finally:
        # Stop all agents
        await data_agent.stop()
        await analysis_agent.stop()
        await client_agent.stop()
        
        logger.info("All agents stopped")

if __name__ == "__main__":
    asyncio.run(main())