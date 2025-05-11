#!/usr/bin/env python3

import json
import time
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the project directory to the path
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from src.framework.core.enhanced_agent import EnhancedAgent
from src.framework.core.config import AgentConfig
from src.utils.data_loader import get_customer_resource_details

logger = logging.getLogger('EnhancedInvestigativeAgent')

class EnhancedInvestigativeAgent(EnhancedAgent):
    """
    Enhanced investigative agent implementation using the framework.
    
    This agent investigates high-priority GuardDuty findings by analyzing
    customer data, using the enhanced agent framework for messaging, configuration,
    and lifecycle management.
    """
    
    def __init__(self, agent_id: Optional[str] = None, config: Optional[AgentConfig] = None):
        """
        Initialize a new enhanced investigative agent.
        
        Args:
            agent_id: Unique identifier for this agent. If None, a UUID will be generated.
            config: Configuration for this agent, or None to use defaults
        """
        # Initialize with specific agent type
        super().__init__(agent_id=agent_id or "investigative-agent", agent_type="investigative", config=config)
        
        # Register capabilities
        self.add_capability("finding_investigation")
        self.add_capability("customer_data_analysis")
        self.add_capability("threat_assessment")
        
        # Track active investigations to avoid duplicates
        self.active_investigations = set()
        
        # Store investigation results
        self.investigation_results = {}
        
        # Add resource authorizations
        self.add_resource_authorization("finding", ["read", "investigate"])
        self.add_resource_authorization("customer_data", ["read", "analyze"])
        self.add_resource_authorization("alert", ["create"])
        
        logger.info(f"Initialized enhanced investigative agent {self.agent_id}")
    
    def _setup_subscriptions(self) -> None:
        """Set up subscriptions for the investigative agent."""
        super()._setup_subscriptions()
        
        # Subscribe to investigation requests
        self.subscribe("agents/investigation/requests")
    
    def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """
        Process a message received from a topic.
        
        Args:
            topic: The topic the message was received on
            message: The message data
            
        Returns:
            bool: True if the message was processed successfully, False otherwise
        """
        # Call parent method for basic processing
        if not super().process_message(topic, message):
            return False
        
        try:
            # Handle different topics
            if topic == "agents/investigation/requests":
                return self._handle_investigation_request(message["data"])
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message on topic {topic}: {e}", exc_info=True)
            self._record_error(e)
            return False
    
    def _handle_investigation_request(self, request: Dict[str, Any]) -> bool:
        """
        Handle an investigation request from the triage agent.
        
        Args:
            request: The investigation request data
            
        Returns:
            bool: True if the request was handled successfully, False otherwise
        """
        finding_id = request["finding_id"]
        priority = request["priority"]
        finding = request["finding"]
        triage_agent_id = request.get("triage_agent_id", "unknown")
        
        # Skip if we're already investigating this finding
        if finding_id in self.active_investigations:
            logger.info(f"Already investigating finding {finding_id}, ignoring duplicate request")
            return True
        
        logger.info(f"Starting investigation for finding {finding_id} with priority {priority}")
        self.active_investigations.add(finding_id)
        
        # Update metrics
        if "investigations_started" not in self._metrics:
            self._metrics["investigations_started"] = 0
        self._metrics["investigations_started"] += 1
        
        # Perform the investigation
        result = self._investigate_finding(finding)
        
        # Store the result
        self.investigation_results[finding_id] = result
        
        # Publish the investigation report
        self.publish("agents/investigation/reports", {
            "finding_id": finding_id,
            "priority": priority,
            "finding": finding,
            "investigation_result": result,
            "timestamp": time.time(),
            "investigator_id": self.agent_id,
            "triage_agent_id": triage_agent_id
        })
        
        # Also send a direct response to the triage agent
        self.publish("agents/investigation/responses", {
            "finding_id": finding_id,
            "investigation_result": result,
            "timestamp": time.time(),
            "investigator_id": self.agent_id,
            "triage_agent_id": triage_agent_id
        })
        
        # If it's a verified threat, send an alert
        if result["is_threat"]:
            severity = result["severity"]
            topic = f"agents/alerts/{severity.lower()}"
            
            # Publish an alert
            self.publish(topic, {
                "finding_id": finding_id,
                "alert_type": result["threat_type"],
                "severity": severity,
                "recommendation": result["recommendation"],
                "details": result["details"],
                "timestamp": time.time(),
                "agent_id": self.agent_id
            })
            
            # Update metrics
            if "alerts_generated" not in self._metrics:
                self._metrics["alerts_generated"] = 0
            self._metrics["alerts_generated"] += 1
        
        # Remove from active investigations
        self.active_investigations.remove(finding_id)
        
        # Update metrics
        if "investigations_completed" not in self._metrics:
            self._metrics["investigations_completed"] = 0
        self._metrics["investigations_completed"] += 1
        
        return True
    
    def _investigate_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Investigate a finding and return the result.
        
        This is where you would implement more complex investigation logic.
        For this PoC, we'll use simplified checks based on the mock data.
        
        Args:
            finding: The finding data
            
        Returns:
            Dict[str, Any]: The investigation result
        """
        finding_type = finding["type"]
        account_id = finding["accountId"]
        resource_type = finding["resourceType"]
        resource_id = finding["resourceId"]
        
        # Get customer resource details
        resource_details = get_customer_resource_details(account_id, resource_type, resource_id)
        
        if not resource_details:
            # Can't find the resource, suspicious
            return {
                "is_threat": True,
                "severity": "HIGH",
                "threat_type": "UNKNOWN_RESOURCE",
                "details": f"Could not find resource {resource_type}/{resource_id} in customer data",
                "recommendation": "Investigate this resource immediately as it may be unauthorized"
            }
        
        # Handle different finding types
        if finding_type == "UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS":
            return self._investigate_credential_exfiltration(finding, resource_details)
            
        elif finding_type == "Recon:IAMUser/UserPermissions":
            return self._investigate_permission_recon(finding, resource_details)
            
        elif finding_type == "UnauthorizedAccess:EC2/SSHBruteForce":
            return self._investigate_ssh_brute_force(finding, resource_details)
            
        else:
            # Generic investigation for unknown finding types
            return {
                "is_threat": True,
                "severity": "MEDIUM",
                "threat_type": "UNKNOWN_FINDING_TYPE",
                "details": f"Unknown finding type {finding_type}",
                "recommendation": "Contact security team for manual investigation"
            }
    
    def _investigate_credential_exfiltration(self, finding: Dict[str, Any], resource_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Investigate credential exfiltration finding.
        
        Args:
            finding: The finding data
            resource_details: Customer resource details
            
        Returns:
            Dict[str, Any]: The investigation result
        """
        # Check if IP is in allowed ranges
        ip_address = finding["details"]["ipAddressV4"]
        allowed_ips = resource_details.get("authorizedIpRanges", [])
        
        # Very simplified IP check - in real life you'd use proper CIDR matching
        ip_allowed = any(ip_address.startswith(allowed_ip.split('/')[0].rsplit('.', 1)[0]) 
                        for allowed_ip in allowed_ips)
        
        # Check time of day
        event_time = datetime.strptime(finding["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
        event_hour = event_time.hour
        allowed_hours = resource_details.get("normalUsagePatterns", {}).get("timeOfDay", [])
        
        time_allowed = False
        for time_range in allowed_hours:
            start_hour = int(time_range.split(":")[0])
            # Assume each range is 1 hour for simplicity
            if event_hour == start_hour:
                time_allowed = True
                break
        
        if not ip_allowed:
            return {
                "is_threat": True,
                "severity": "CRITICAL",
                "threat_type": "CREDENTIAL_EXFILTRATION",
                "details": (
                    f"Credentials used from unauthorized IP {ip_address}. "
                    f"API calls: {', '.join(call['api'] for call in finding['details']['additionalInfo']['recentApiCalls'])}"
                ),
                "recommendation": "Rotate credentials immediately and investigate possible compromise"
            }
        elif not time_allowed:
            return {
                "is_threat": True,
                "severity": "HIGH",
                "threat_type": "SUSPICIOUS_ACCESS_TIME",
                "details": f"Credentials used at unusual time {event_time.strftime('%H:%M')}",
                "recommendation": "Verify with user if this was legitimate access"
            }
        else:
            return {
                "is_threat": False,
                "severity": "INFO",
                "threat_type": "NONE",
                "details": "Access from authorized IP during normal hours",
                "recommendation": "No action required"
            }
    
    def _investigate_permission_recon(self, finding: Dict[str, Any], resource_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Investigate permission reconnaissance finding.
        
        Args:
            finding: The finding data
            resource_details: Customer resource details
            
        Returns:
            Dict[str, Any]: The investigation result
        """
        # Check if this type of behavior is normal for this user
        recent_apis = [call["api"] for call in finding["details"]["additionalInfo"]["recentApiCalls"]]
        suspicious_apis = ["ListUsers", "ListRoles", "GetPolicy"]
        
        # Check if multiple suspicious APIs were called
        suspicious_api_count = len(set(recent_apis).intersection(set(suspicious_apis)))
        
        # Check if this account has previous alerts
        previous_alerts = resource_details.get("previousAlerts", 0)
        
        if suspicious_api_count >= 2 and previous_alerts > 0:
            return {
                "is_threat": True,
                "severity": "MEDIUM",
                "threat_type": "PERMISSION_RECONNAISSANCE",
                "details": (
                    f"User called suspicious permission-related APIs: {', '.join(set(recent_apis).intersection(set(suspicious_apis)))}. "
                    f"User has {previous_alerts} previous alert(s)."
                ),
                "recommendation": "Investigate user activity and consider restricting permissions"
            }
        else:
            return {
                "is_threat": False,
                "severity": "LOW",
                "threat_type": "NONE",
                "details": "Permission-related API calls appear to be normal admin activity",
                "recommendation": "No action required, but monitor for escalation"
            }
    
    def _investigate_ssh_brute_force(self, finding: Dict[str, Any], resource_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Investigate SSH brute force finding.
        
        Args:
            finding: The finding data
            resource_details: Customer resource details
            
        Returns:
            Dict[str, Any]: The investigation result
        """
        # Check if SSH is expected on this instance
        expected_ports = resource_details.get("expectedTraffic", {}).get("expectedPorts", [])
        publicly_accessible = resource_details.get("publiclyAccessible", False)
        
        if 22 not in expected_ports:
            return {
                "is_threat": True,
                "severity": "CRITICAL",
                "threat_type": "UNEXPECTED_SSH_ACCESS",
                "details": "SSH traffic detected on an instance that should not have SSH traffic",
                "recommendation": "Verify security groups and NACLs, block port 22 immediately"
            }
        elif publicly_accessible:
            return {
                "is_threat": True,
                "severity": "HIGH",
                "threat_type": "SSH_BRUTE_FORCE",
                "details": f"SSH brute force attack from {finding['details']['ipAddressV4']} on publicly accessible instance",
                "recommendation": "Restrict SSH access to specific IPs and implement IP-based rate limiting"
            }
        else:
            return {
                "is_threat": True,
                "severity": "MEDIUM",
                "threat_type": "SSH_BRUTE_FORCE_ATTEMPT",
                "details": f"SSH brute force attempt from {finding['details']['ipAddressV4']}, but instance not publicly accessible",
                "recommendation": "Verify VPC security and implement SSH key-based authentication only"
            }
    
    def _periodic_tasks(self) -> None:
        """Perform periodic tasks for the investigative agent."""
        super()._periodic_tasks()
        
        # Example: Log statistics every 5 minutes
        current_time = time.time()
        last_stats = self._metrics.get("last_stats_time", 0)
        
        if current_time - last_stats > 300:  # 5 minutes
            logger.info(f"Agent {self.agent_id} statistics: "
                      f"Started: {self._metrics.get('investigations_started', 0)}, "
                      f"Completed: {self._metrics.get('investigations_completed', 0)}, "
                      f"Alerts: {self._metrics.get('alerts_generated', 0)}")
            
            self._metrics["last_stats_time"] = current_time

# Import threading here to avoid circular import
import threading

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create and start the agent
    agent = EnhancedInvestigativeAgent()
    agent.start()
    
    try:
        # Keep the agent running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent...")
    finally:
        agent.stop()