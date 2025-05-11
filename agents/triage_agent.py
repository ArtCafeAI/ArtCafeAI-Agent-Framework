#!/usr/bin/env python3

import json
import time
import logging
from typing import Dict, List, Any, Callable

import sys
import os

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.pubsub import create_agent_token, subscribe, publish, unsubscribe
from src.utils.data_loader import load_guardduty_findings

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TriageAgent')

class TriageAgent:
    """
    Agent that triages AWS GuardDuty findings and determines whether they warrant investigation.
    
    This agent:
    1. Receives GuardDuty findings (mocked in this implementation)
    2. Applies deterministic rules to assess severity and priority
    3. Sends high-priority findings to the investigative agent via pub/sub
    """
    
    def __init__(self, agent_id: str = "triage-agent"):
        self.agent_id = agent_id
        self.token = create_agent_token(agent_id, [
            "publish:agents/findings/#",
            "subscribe:agents/findings/new",
            "publish:agents/investigation/requests"
        ])
        
        # Define severity thresholds for different finding types
        self.severity_thresholds = {
            "UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS": 5.0,
            "Recon:IAMUser/UserPermissions": 2.0,
            "UnauthorizedAccess:EC2/SSHBruteForce": 4.0,
            # Default threshold for any other finding type
            "default": 7.0
        }
        
        # Cache for findings we've already processed (to avoid duplicate processing)
        self.processed_findings = set()
        
        # Flag to control whether to load mock findings on startup
        self.skip_loading = False
    
    def set_skip_loading(self, skip: bool):
        """Set whether to skip loading mock findings on startup"""
        self.skip_loading = skip
    
    def start(self):
        """Start the triage agent"""
        logger.info(f"Starting {self.agent_id}...")
        
        # Subscribe to new findings topic
        subscribe(self.token, "agents/findings/new", self._process_finding)
        
        # For demo purposes, simulate receiving findings from GuardDuty
        if not self.skip_loading:
            self._load_mock_findings()
        
        logger.info(f"{self.agent_id} started and ready to process findings")
    
    def _load_mock_findings(self):
        """Load and process mock findings for demonstration"""
        findings = load_guardduty_findings()
        logger.info(f"Loaded {len(findings)} mock GuardDuty findings")
        
        # Publish each finding to the new findings topic
        for finding in findings:
            publish(self.token, "agents/findings/new", finding)
            # Small delay to simulate findings arriving over time
            time.sleep(0.5)
    
    def _process_finding(self, message: Dict[str, Any]):
        """Process a GuardDuty finding"""
        finding = message["data"]
        finding_id = finding["id"]
        
        # Skip if we've already processed this finding
        if finding_id in self.processed_findings:
            return
        
        logger.info(f"Processing finding: {finding_id} ({finding['type']})")
        self.processed_findings.add(finding_id)
        
        # Apply triage rules to determine if investigation is needed
        if self._requires_investigation(finding):
            logger.info(f"Finding {finding_id} requires investigation")
            
            # Publish to the investigation requests topic
            publish(self.token, "agents/investigation/requests", {
                "finding_id": finding_id,
                "priority": self._calculate_priority(finding),
                "finding": finding
            })
        else:
            logger.info(f"Finding {finding_id} does not require investigation")
            
            # Publish as a low-severity finding for tracking
            publish(self.token, "agents/findings/low_severity", finding)
    
    def _requires_investigation(self, finding: Dict[str, Any]) -> bool:
        """
        Determine if a finding requires investigation based on rules
        
        Rules:
        1. Severity exceeds the threshold for the finding type
        2. Type-specific rules (e.g., specific resource types, regions, or patterns)
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
            recent_apis = [call["api"] for call in finding["details"]["additionalInfo"]["recentApiCalls"]]
            
            # Check if multiple suspicious APIs were called
            return len(set(recent_apis).intersection(set(suspicious_apis))) >= 2
        
        elif finding_type == "UnauthorizedAccess:EC2/SSHBruteForce":
            # Check if the source location is from a high-risk country
            high_risk_countries = ["RU", "CN", "KP", "IR"]
            return finding["details"]["location"]["country"] in high_risk_countries
            
        return False
    
    def _calculate_priority(self, finding: Dict[str, Any]) -> str:
        """Calculate priority of a finding: HIGH, MEDIUM, or LOW"""
        finding_type = finding["type"]
        finding_severity = finding["severity"]
        
        if finding_severity >= 7.0:
            return "HIGH"
        elif finding_severity >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"
    
    def stop(self):
        """Stop the triage agent"""
        logger.info(f"Stopping {self.agent_id}...")
        unsubscribe(self.token, "agents/findings/new")
        logger.info(f"{self.agent_id} stopped")

if __name__ == "__main__":
    # When run directly, instantiate and start the agent
    agent = TriageAgent()
    agent.start()
    
    try:
        # Keep the agent running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent...")
    finally:
        agent.stop()