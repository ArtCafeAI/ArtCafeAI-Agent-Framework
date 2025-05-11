#!/usr/bin/env python3

import json
import time
import logging
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime

import sys
import os

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.pubsub import create_agent_token, subscribe, publish, unsubscribe
from src.utils.data_loader import get_customer_resource_details

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InvestigativeAgent')

class InvestigativeAgent:
    """
    Agent that investigates high-priority GuardDuty findings by analyzing customer data.
    
    This agent:
    1. Receives investigation requests from the triage agent
    2. Pulls relevant customer data
    3. Analyzes the data to determine if it's a legitimate threat
    4. Produces investigation reports
    """
    
    def __init__(self, agent_id: str = "investigative-agent"):
        self.agent_id = agent_id
        self.token = create_agent_token(agent_id, [
            "subscribe:agents/investigation/requests",
            "publish:agents/investigation/reports",
            "publish:agents/alerts/#"
        ])
        
        # Track active investigations to avoid duplicates
        self.active_investigations = set()
        
        # Store investigation results
        self.investigation_results = {}
    
    def start(self):
        """Start the investigative agent"""
        logger.info(f"Starting {self.agent_id}...")
        
        # Subscribe to investigation requests
        subscribe(self.token, "agents/investigation/requests", self._handle_investigation_request)
        
        logger.info(f"{self.agent_id} started and ready to process investigation requests")
    
    def _handle_investigation_request(self, message: Dict[str, Any]):
        """Handle an investigation request from the triage agent"""
        # Extract the actual data from the message wrapper
        request = message["data"]
        finding_id = request["finding_id"]
        priority = request["priority"]
        finding = request["finding"]
        
        # Skip if we're already investigating this finding
        if finding_id in self.active_investigations:
            logger.info(f"Already investigating finding {finding_id}, ignoring duplicate request")
            return
        
        logger.info(f"Starting investigation for finding {finding_id} with priority {priority}")
        self.active_investigations.add(finding_id)
        
        # Perform the investigation
        result = self._investigate_finding(finding)
        
        # Store the result
        self.investigation_results[finding_id] = result
        
        # Publish the investigation report
        publish(self.token, "agents/investigation/reports", {
            "finding_id": finding_id,
            "priority": priority,
            "finding": finding,
            "investigation_result": result,
            "timestamp": time.time(),
            "investigator_id": self.agent_id
        })
        
        # If it's a verified threat, send an alert
        if result["is_threat"]:
            severity = result["severity"]
            topic = f"agents/alerts/{severity.lower()}"
            
            # Publish an alert
            publish(self.token, topic, {
                "finding_id": finding_id,
                "alert_type": result["threat_type"],
                "severity": severity,
                "recommendation": result["recommendation"],
                "details": result["details"],
                "timestamp": time.time()
            })
        
        # Remove from active investigations
        self.active_investigations.remove(finding_id)
    
    def _investigate_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Investigate a finding and return the result
        
        This is where you would implement more complex investigation logic.
        For this PoC, we'll use simplified checks based on the mock data.
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
        """Investigate credential exfiltration finding"""
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
        """Investigate permission reconnaissance finding"""
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
        """Investigate SSH brute force finding"""
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
    
    def stop(self):
        """Stop the investigative agent"""
        logger.info(f"Stopping {self.agent_id}...")
        unsubscribe(self.token, "agents/investigation/requests")
        logger.info(f"{self.agent_id} stopped")

if __name__ == "__main__":
    # When run directly, instantiate and start the agent
    agent = InvestigativeAgent()
    agent.start()
    
    try:
        # Keep the agent running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent...")
    finally:
        agent.stop()