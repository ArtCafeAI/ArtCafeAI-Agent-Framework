#!/usr/bin/env python3

import json
import time
import logging
import os
from typing import Dict, List, Any, Optional

# Add the project directory to the path
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from src.framework.core.enhanced_agent import EnhancedAgent
from src.framework.core.config import AgentConfig
from src.utils.data_loader import load_guardduty_findings

logger = logging.getLogger('EnhancedTriageAgent')

class EnhancedTriageAgent(EnhancedAgent):
    """
    Enhanced triage agent implementation using the framework.
    
    This agent analyzes AWS GuardDuty findings and determines which ones warrant
    investigation, using the enhanced agent framework for messaging, configuration,
    and lifecycle management.
    """
    
    def __init__(self, agent_id: Optional[str] = None, config: Optional[AgentConfig] = None):
        """
        Initialize a new enhanced triage agent.
        
        Args:
            agent_id: Unique identifier for this agent. If None, a UUID will be generated.
            config: Configuration for this agent, or None to use defaults
        """
        # Initialize with specific agent type
        super().__init__(agent_id=agent_id or "triage-agent", agent_type="triage", config=config)
        
        # Register capabilities
        self.add_capability("finding_triage")
        self.add_capability("severity_assessment")
        
        # Define severity thresholds for different finding types
        self.severity_thresholds = self.config.get("triage.severity_thresholds", {
            "UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS": 5.0,
            "Recon:IAMUser/UserPermissions": 2.0,
            "UnauthorizedAccess:EC2/SSHBruteForce": 4.0,
            # Default threshold for any other finding type
            "default": 7.0
        })
        
        # Cache for findings we've already processed (to avoid duplicate processing)
        self.processed_findings = set()
        
        # Flag to control whether to load mock findings on startup
        self.skip_loading = self.config.get("triage.skip_loading", False)
        
        # Add resource authorizations
        self.add_resource_authorization("finding", ["read", "triage"])
        self.add_resource_authorization("investigation", ["request"])
        
        logger.info(f"Initialized enhanced triage agent {self.agent_id}")
    
    def _setup_subscriptions(self) -> None:
        """Set up subscriptions for the triage agent."""
        super()._setup_subscriptions()
        
        # Subscribe to new findings topic
        self.subscribe("agents/findings/new")
        
        # Subscribe to investigation responses
        self.subscribe("agents/investigation/responses")
    
    def start(self) -> bool:
        """
        Start the triage agent.
        
        Returns:
            bool: True if the agent was started successfully, False otherwise
        """
        if not super().start():
            return False
        
        # For demo purposes, simulate receiving findings from GuardDuty
        if not self.skip_loading:
            threading.Thread(target=self._load_mock_findings).start()
        
        return True
    
    def _load_mock_findings(self) -> None:
        """Load and process mock findings for demonstration."""
        findings = load_guardduty_findings()
        logger.info(f"Loaded {len(findings)} mock GuardDuty findings")
        
        # Publish each finding to the new findings topic
        for finding in findings:
            self.publish("agents/findings/new", finding)
            # Small delay to simulate findings arriving over time
            time.sleep(0.5)
    
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
            if topic == "agents/findings/new":
                return self._process_finding(message["data"])
            elif topic == "agents/investigation/responses":
                return self._process_investigation_response(message["data"])
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message on topic {topic}: {e}", exc_info=True)
            self._record_error(e)
            return False
    
    def _process_finding(self, finding: Dict[str, Any]) -> bool:
        """
        Process a GuardDuty finding.
        
        Args:
            finding: The finding data
            
        Returns:
            bool: True if the finding was processed successfully, False otherwise
        """
        finding_id = finding["id"]
        
        # Skip if we've already processed this finding
        if finding_id in self.processed_findings:
            logger.debug(f"Skipping already processed finding: {finding_id}")
            return True
        
        logger.info(f"Processing finding: {finding_id} ({finding['type']})")
        self.processed_findings.add(finding_id)
        
        # Apply triage rules to determine if investigation is needed
        if self._requires_investigation(finding):
            logger.info(f"Finding {finding_id} requires investigation")
            
            # Publish to the investigation requests topic
            self.publish("agents/investigation/requests", {
                "finding_id": finding_id,
                "priority": self._calculate_priority(finding),
                "finding": finding,
                "triage_agent_id": self.agent_id,
                "timestamp": time.time()
            })
        else:
            logger.info(f"Finding {finding_id} does not require investigation")
            
            # Publish as a low-severity finding for tracking
            self.publish("agents/findings/low_severity", finding)
        
        return True
    
    def _process_investigation_response(self, response: Dict[str, Any]) -> bool:
        """
        Process an investigation response.
        
        Args:
            response: The investigation response data
            
        Returns:
            bool: True if the response was processed successfully, False otherwise
        """
        finding_id = response["finding_id"]
        investigation_result = response["investigation_result"]
        
        logger.info(f"Received investigation response for finding {finding_id}")
        
        # Update metrics
        if "investigation_responses" not in self._metrics:
            self._metrics["investigation_responses"] = 0
        self._metrics["investigation_responses"] += 1
        
        # Additional processing can be added here
        
        return True
    
    def _requires_investigation(self, finding: Dict[str, Any]) -> bool:
        """
        Determine if a finding requires investigation based on rules.
        
        Rules:
        1. Severity exceeds the threshold for the finding type
        2. Type-specific rules (e.g., specific resource types, regions, or patterns)
        
        Args:
            finding: The finding data
            
        Returns:
            bool: True if the finding requires investigation, False otherwise
        """
        finding_type = finding["type"]
        finding_severity = finding["severity"]
        
        # Get the threshold for this finding type (or default)
        threshold = self.severity_thresholds.get(finding_type, self.severity_thresholds["default"])
        
        # Check severity threshold
        if finding_severity >= threshold:
            return True
        
        # Apply type-specific rules
        if finding_type == "UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS":
            # Always investigate credential exfiltration regardless of severity
            return True
        
        elif finding_type == "Recon:IAMUser/UserPermissions":
            # Investigate if the specific IAM APIs being called are suspicious
            suspicious_apis = ["ListUsers", "ListRoles", "GetPolicy"]
            
            if "details" in finding and "additionalInfo" in finding["details"]:
                recent_apis = [call["api"] for call in finding["details"]["additionalInfo"].get("recentApiCalls", [])]
                
                # Check if multiple suspicious APIs were called
                return len(set(recent_apis).intersection(set(suspicious_apis))) >= 2
        
        elif finding_type == "UnauthorizedAccess:EC2/SSHBruteForce":
            # Check if the source location is from a high-risk country
            high_risk_countries = ["RU", "CN", "KP", "IR"]
            
            if "details" in finding and "location" in finding["details"]:
                country = finding["details"]["location"].get("country")
                return country in high_risk_countries
            
        return False
    
    def _calculate_priority(self, finding: Dict[str, Any]) -> str:
        """
        Calculate priority of a finding: HIGH, MEDIUM, or LOW.
        
        Args:
            finding: The finding data
            
        Returns:
            str: The priority level
        """
        finding_severity = finding["severity"]
        
        if finding_severity >= 7.0:
            return "HIGH"
        elif finding_severity >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"

# Import threading here to avoid circular import
import threading

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create and start the agent
    agent = EnhancedTriageAgent()
    agent.start()
    
    try:
        # Keep the agent running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent...")
    finally:
        agent.stop()