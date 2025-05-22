#!/usr/bin/env python3
"""
Notification Agent Template

This agent demonstrates how to send notifications through various channels
like email, SMS, and webhooks based on events from the ArtCafe platform.
"""

import asyncio
import logging
import json
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from artcafe_agent import ArtCafeAgent


class NotificationAgent(ArtCafeAgent):
    """
    Agent that handles sending notifications through various channels.
    
    Features:
    - Email notifications
    - SMS notifications (via Twilio)
    - Webhook notifications
    - Rate limiting
    - Retry logic
    - Template support
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(
            agent_id=config["agent_id"],
            tenant_id=config["tenant_id"],
            private_key_path=config["private_key_path"],
            api_endpoint=config.get("api_endpoint", "https://api.artcafe.ai"),
            log_level=config.get("log_level", "INFO")
        )
        
        # Register command handlers
        self.register_command("send_notification", self.handle_send_notification)
        self.register_command("send_bulk", self.handle_send_bulk)
        self.register_command("set_template", self.handle_set_template)
        self.register_command("get_templates", self.handle_get_templates)
        self.register_command("get_stats", self.handle_get_stats)
        
        # Initialize configuration
        self.smtp_config = config.get("smtp", {})
        self.twilio_config = config.get("twilio", {})
        self.webhook_timeout = config.get("webhook_timeout", 30)
        
        # Initialize state
        self.templates = {}
        self.stats = {
            "emails_sent": 0,
            "sms_sent": 0,
            "webhooks_sent": 0,
            "errors": 0,
            "last_error": None
        }
        
        # Rate limiting
        self.rate_limits = {
            "email": {"limit": 100, "window": 3600, "sent": []},
            "sms": {"limit": 50, "window": 3600, "sent": []},
            "webhook": {"limit": 200, "window": 3600, "sent": []}
        }
        
        self.logger.info(f"Notification Agent initialized: {config['agent_id']}")
    
    async def handle_send_notification(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a single notification.
        
        Args:
            args: Command arguments containing:
                - channel: Notification channel (email, sms, webhook)
                - recipient: Recipient address/number/URL
                - subject: Subject line (for email)
                - message: Message content
                - template: Template name (optional)
                - template_data: Template variables (optional)
                - priority: Priority level (optional)
        """
        channel = args.get("channel")
        recipient = args.get("recipient")
        message = args.get("message")
        template = args.get("template")
        template_data = args.get("template_data", {})
        
        if not channel or not recipient:
            return {
                "status": "error",
                "error": "Channel and recipient are required"
            }
        
        # Check rate limit
        if not self._check_rate_limit(channel):
            return {
                "status": "error",
                "error": f"Rate limit exceeded for {channel}"
            }
        
        # Process template if specified
        if template:
            template_content = self.templates.get(template)
            if template_content:
                message = self._process_template(template_content, template_data)
            else:
                return {
                    "status": "error",
                    "error": f"Template not found: {template}"
                }
        
        # Send notification based on channel
        try:
            if channel == "email":
                result = await self._send_email(
                    recipient=recipient,
                    subject=args.get("subject", "Notification"),
                    body=message
                )
            elif channel == "sms":
                result = await self._send_sms(
                    phone_number=recipient,
                    message=message
                )
            elif channel == "webhook":
                result = await self._send_webhook(
                    url=recipient,
                    payload={
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat(),
                        "priority": args.get("priority", "normal")
                    }
                )
            else:
                return {
                    "status": "error",
                    "error": f"Unknown channel: {channel}"
                }
            
            # Update stats
            self.stats[f"{channel}s_sent"] += 1
            self._update_rate_limit(channel)
            
            return {
                "status": "success",
                "channel": channel,
                "recipient": recipient,
                "result": result
            }
        
        except Exception as e:
            self.logger.error(f"Error sending {channel} notification: {e}")
            self.stats["errors"] += 1
            self.stats["last_error"] = {
                "channel": channel,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def handle_send_bulk(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send bulk notifications.
        
        Args:
            args: Command arguments containing:
                - notifications: List of notification objects
                - batch_size: Number of concurrent sends (optional)
        """
        notifications = args.get("notifications", [])
        batch_size = args.get("batch_size", 10)
        
        if not notifications:
            return {
                "status": "error",
                "error": "No notifications provided"
            }
        
        results = []
        errors = []
        
        # Process in batches
        for i in range(0, len(notifications), batch_size):
            batch = notifications[i:i + batch_size]
            
            # Send batch concurrently
            tasks = []
            for notification in batch:
                task = asyncio.create_task(
                    self.handle_send_notification(notification)
                )
                tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    errors.append({
                        "index": i + j,
                        "error": str(result)
                    })
                elif result.get("status") == "error":
                    errors.append({
                        "index": i + j,
                        "error": result.get("error")
                    })
                else:
                    results.append(result)
        
        return {
            "status": "success" if not errors else "partial",
            "sent": len(results),
            "errors": len(errors),
            "error_details": errors if errors else None
        }
    
    async def handle_set_template(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set a notification template.
        
        Args:
            args: Command arguments containing:
                - name: Template name
                - content: Template content with {variables}
                - description: Template description (optional)
        """
        name = args.get("name")
        content = args.get("content")
        
        if not name or not content:
            return {
                "status": "error",
                "error": "Name and content are required"
            }
        
        self.templates[name] = {
            "content": content,
            "description": args.get("description", ""),
            "created_at": datetime.utcnow().isoformat()
        }
        
        return {
            "status": "success",
            "template": name,
            "message": "Template saved"
        }
    
    async def handle_get_templates(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get all notification templates."""
        return {
            "status": "success",
            "templates": self.templates
        }
    
    async def handle_get_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get notification statistics."""
        # Calculate totals
        total_sent = (
            self.stats["emails_sent"] + 
            self.stats["sms_sent"] + 
            self.stats["webhooks_sent"]
        )
        
        # Get rate limit status
        rate_limit_status = {}
        for channel, limits in self.rate_limits.items():
            # Clean old entries
            cutoff = datetime.utcnow() - timedelta(seconds=limits["window"])
            limits["sent"] = [
                ts for ts in limits["sent"] 
                if datetime.fromisoformat(ts) > cutoff
            ]
            
            rate_limit_status[channel] = {
                "limit": limits["limit"],
                "window": limits["window"],
                "used": len(limits["sent"]),
                "remaining": limits["limit"] - len(limits["sent"])
            }
        
        return {
            "status": "success",
            "stats": {
                **self.stats,
                "total_sent": total_sent,
                "rate_limits": rate_limit_status,
                "uptime": self.get_uptime()
            }
        }
    
    async def _send_email(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Send an email notification."""
        msg = MIMEMultipart()
        msg['From'] = self.smtp_config.get("from_address")
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server
        with smtplib.SMTP(
            self.smtp_config.get("host"),
            self.smtp_config.get("port", 587)
        ) as server:
            if self.smtp_config.get("use_tls", True):
                server.starttls()
            
            if self.smtp_config.get("username"):
                server.login(
                    self.smtp_config.get("username"),
                    self.smtp_config.get("password")
                )
            
            server.send_message(msg)
        
        return {
            "message_id": msg['Message-ID'],
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def _send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send an SMS notification using Twilio."""
        # This is a mock implementation
        # In production, you would use the Twilio API
        
        self.logger.info(f"SMS to {phone_number}: {message}")
        
        # Simulate API call
        await asyncio.sleep(0.5)
        
        return {
            "message_id": f"sms-{datetime.utcnow().timestamp()}",
            "sent_at": datetime.utcnow().isoformat()
        }
    
    async def _send_webhook(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a webhook notification."""
        async with httpx.AsyncClient(timeout=self.webhook_timeout) as client:
            response = await client.post(url, json=payload)
            
            return {
                "status_code": response.status_code,
                "sent_at": datetime.utcnow().isoformat()
            }
    
    def _check_rate_limit(self, channel: str) -> bool:
        """Check if rate limit allows sending."""
        limits = self.rate_limits.get(channel, {})
        cutoff = datetime.utcnow() - timedelta(seconds=limits.get("window", 3600))
        
        # Clean old entries
        limits["sent"] = [
            ts for ts in limits.get("sent", [])
            if datetime.fromisoformat(ts) > cutoff
        ]
        
        return len(limits["sent"]) < limits.get("limit", 100)
    
    def _update_rate_limit(self, channel: str) -> None:
        """Update rate limit tracking."""
        limits = self.rate_limits.get(channel, {})
        limits.setdefault("sent", []).append(datetime.utcnow().isoformat())
    
    def _process_template(self, template: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Process a template with variables."""
        content = template.get("content", "")
        
        # Simple variable replacement
        for key, value in data.items():
            content = content.replace(f"{{{key}}}", str(value))
        
        return content


async def main():
    """Main entry point."""
    # Load configuration
    config = {
        "agent_id": "notification-agent-001",
        "tenant_id": "your-tenant-id",
        "private_key_path": "~/.ssh/artcafe_agent_key",
        "smtp": {
            "host": "smtp.gmail.com",
            "port": 587,
            "use_tls": True,
            "username": "your-email@gmail.com",
            "password": "your-app-password",
            "from_address": "notifications@yourcompany.com"
        },
        "twilio": {
            "account_sid": "your-twilio-sid",
            "auth_token": "your-twilio-token",
            "from_number": "+1234567890"
        }
    }
    
    # Try to load from file
    try:
        with open("notification_config.json") as f:
            config.update(json.load(f))
    except FileNotFoundError:
        print("No config file found, using defaults")
    
    # Create and start agent
    agent = NotificationAgent(config)
    
    try:
        print(f"Starting Notification Agent: {config['agent_id']}")
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