#!/usr/bin/env python3
"""
Example: Agent with Automatic Heartbeat Support

This example demonstrates how to use the HeartbeatAgent for reliable
status tracking with automatic heartbeats.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add framework to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.core.heartbeat_agent import HeartbeatAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitoringAgent(HeartbeatAgent):
    """Example agent that monitors system health with reliable heartbeats."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_count = 0
        self.start_time = datetime.now()
    
    async def setup(self):
        """Set up agent handlers."""
        
        @self.on_message("system.health")
        async def handle_health_check(subject, data):
            """Handle system health check requests."""
            logger.info(f"Health check request: {data}")
            
            # Respond with agent health
            health = self.get_connection_health()
            await self.publish("system.health.response", {
                "agent_id": self.agent_id,
                "status": "healthy" if health['healthy'] else "unhealthy",
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "messages_processed": self.message_count,
                "connection_health": health
            })
            self.message_count += 1
        
        @self.on_message("system.broadcast")
        async def handle_broadcast(subject, data):
            """Handle system broadcasts."""
            logger.info(f"System broadcast: {data.get('message', 'No message')}")
            self.message_count += 1
        
        # Subscribe to team-specific channels
        @self.on_message(f"team.{self.agent_id}")
        async def handle_team_message(subject, data):
            """Handle team-specific messages."""
            logger.info(f"Team message on {subject}: {data}")
            
            # Echo back to confirm receipt
            await self.publish(f"team.{self.agent_id}.response", {
                "received": data,
                "processed_at": datetime.now().isoformat()
            })
            self.message_count += 1
    
    async def periodic_status_report(self):
        """Send periodic status reports."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Report every minute
                
                health = self.get_connection_health()
                report = {
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat(),
                    "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                    "messages_processed": self.message_count,
                    "connection_healthy": health['healthy'],
                    "heartbeat_status": {
                        "last_ack": health['last_heartbeat_ack'],
                        "seconds_since_ack": health['seconds_since_ack']
                    }
                }
                
                # Publish status report
                await self.publish("monitoring.status", report)
                logger.info(f"Published status report: {report}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in status report: {e}")
    
    async def run(self):
        """Run the agent with periodic reporting."""
        # Set up handlers
        await self.setup()
        
        # Start status reporting task
        status_task = asyncio.create_task(self.periodic_status_report())
        
        try:
            # Run the agent
            await super().run()
        finally:
            # Clean up status task
            status_task.cancel()
            try:
                await status_task
            except asyncio.CancelledError:
                pass


async def main():
    """Run the example monitoring agent."""
    
    # Configuration from environment or defaults
    agent_id = os.getenv("AGENT_ID", "monitoring-agent-001")
    org_id = os.getenv("ORGANIZATION_ID", "demo-org")
    private_key_path = os.getenv("PRIVATE_KEY_PATH", "keys/agent_private_key.pem")
    
    # Validate private key exists
    if not os.path.exists(private_key_path):
        logger.error(f"Private key not found at {private_key_path}")
        logger.info("Generate a key pair with: openssl genrsa -out agent_private_key.pem 2048")
        logger.info("Then extract public key: openssl rsa -in agent_private_key.pem -pubout -out agent_public_key.pem")
        return
    
    # Create agent with custom heartbeat settings
    agent = MonitoringAgent(
        agent_id=agent_id,
        private_key_path=private_key_path,
        organization_id=org_id,
        heartbeat_interval=30,  # Send heartbeat every 30 seconds
        heartbeat_timeout_multiplier=3.0,  # Timeout after 90 seconds
        auto_reconnect=True,  # Automatically reconnect on connection loss
        capabilities=["monitoring", "health_check", "status_reporting"],
        metadata={
            "version": "1.0.0",
            "environment": "production",
            "host": os.uname().nodename
        }
    )
    
    logger.info(f"Starting monitoring agent: {agent_id}")
    logger.info("Features:")
    logger.info("- Automatic heartbeats every 30 seconds")
    logger.info("- Connection health monitoring")
    logger.info("- Auto-reconnection on connection loss")
    logger.info("- Periodic status reports")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await agent.stop()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())