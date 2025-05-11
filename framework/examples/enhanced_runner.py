#!/usr/bin/env python3

import sys
import os
import time
import logging
import argparse
import threading
import json
from typing import Dict, List, Any

# Add the project directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from src.framework import initialize as initialize_framework
from src.framework.core.config import AgentConfig
from src.framework.core.enhanced_agent import EnhancedAgent
from src.framework.messaging import get_messaging, subscribe, create_token
from src.framework.examples.enhanced_triage_agent import EnhancedTriageAgent
from src.framework.examples.enhanced_investigative_agent import EnhancedInvestigativeAgent

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('EnhancedSystem')

class EnhancedSecurityMonitoringSystem:
    """
    Enhanced security monitoring system using the agent framework.
    
    This class:
    1. Initializes the framework and agents
    2. Subscribes to relevant topics for reporting
    3. Manages the agents' lifecycle
    4. Provides a unified interface for controlling the system
    """
    
    def __init__(self, config_file: str = None):
        """
        Initialize a new enhanced security monitoring system.
        
        Args:
            config_file: Path to the configuration file, or None to use defaults
        """
        # Initialize the framework
        config_files = [config_file] if config_file else None
        self.config = initialize_framework(config_files)
        
        # Create messaging interface
        self.messaging = get_messaging("system-monitor")
        
        # Create authorization token
        self.monitor_token = create_token("system-monitor", ["*"])
        
        # Initialize agents
        self.triage_agent = EnhancedTriageAgent(config=self.config)
        self.investigative_agent = EnhancedInvestigativeAgent(config=self.config)
        
        # Store all alerts and reports
        self.alerts = []
        self.investigation_reports = []
        
        logger.info("Initialized enhanced security monitoring system")
    
    def start(self):
        """Start the security monitoring system"""
        logger.info("Starting Enhanced Security Monitoring System...")
        
        # Authenticate messaging interface
        self.messaging.authenticate(["*"])
        
        # Subscribe to investigation reports
        subscribe(self.monitor_token, "agents/investigation/reports", self._handle_investigation_report)
        
        # Subscribe to all alerts
        subscribe(self.monitor_token, "agents/alerts/#", self._handle_alert)
        
        # Start the agents
        self.investigative_agent.start()
        time.sleep(1)  # Ensure investigative agent is ready before triage agent starts sending requests
        self.triage_agent.start()
        
        logger.info("Enhanced Security Monitoring System started")
    
    def _handle_investigation_report(self, message: Dict[str, Any]):
        """Handle investigation reports"""
        report = message["data"]
        self.investigation_reports.append(report)
        
        finding_id = report["finding_id"]
        is_threat = report["investigation_result"]["is_threat"]
        severity = report["investigation_result"]["severity"]
        
        if is_threat:
            logger.info(f"Investigation {finding_id} concluded: THREAT CONFIRMED ({severity})")
        else:
            logger.info(f"Investigation {finding_id} concluded: NO THREAT ({severity})")
    
    def _handle_alert(self, message: Dict[str, Any]):
        """Handle security alerts"""
        alert = message["data"]
        self.alerts.append(alert)
        
        finding_id = alert["finding_id"]
        alert_type = alert["alert_type"]
        severity = alert["severity"]
        recommendation = alert["recommendation"]
        
        logger.warning(f"ALERT ({severity}): {alert_type} - {recommendation}")
    
    def stop(self):
        """Stop the security monitoring system"""
        logger.info("Stopping Enhanced Security Monitoring System...")
        
        # Stop the agents
        self.triage_agent.stop()
        self.investigative_agent.stop()
        
        logger.info("Enhanced Security Monitoring System stopped")
    
    def report(self):
        """Generate a summary report of all activity"""
        alert_count = len(self.alerts)
        report_count = len(self.investigation_reports)
        
        threat_count = sum(1 for report in self.investigation_reports 
                          if report["investigation_result"]["is_threat"])
        
        print("\n===== ENHANCED SECURITY MONITORING SYSTEM REPORT =====")
        print(f"Total GuardDuty findings processed: {report_count}")
        print(f"Confirmed threats: {threat_count}")
        print(f"Total alerts generated: {alert_count}")
        
        if threat_count > 0:
            print("\n----- THREAT DETAILS -----")
            for report in self.investigation_reports:
                if report["investigation_result"]["is_threat"]:
                    result = report["investigation_result"]
                    print(f"\nFinding ID: {report['finding_id']}")
                    print(f"Threat Type: {result['threat_type']}")
                    print(f"Severity: {result['severity']}")
                    print(f"Details: {result['details']}")
                    print(f"Recommendation: {result['recommendation']}")
        
        print("\n==========================================")
        
        # Also print agent statistics
        print("\n----- AGENT STATISTICS -----")
        print(f"Triage Agent: {self.triage_agent.agent_id}")
        print(f"  Status: {self.triage_agent.status}")
        print(f"  Messages processed: {self.triage_agent._metrics.get('messages_processed', 0)}")
        print(f"  Messages sent: {self.triage_agent._metrics.get('messages_sent', 0)}")
        
        print(f"\nInvestigative Agent: {self.investigative_agent.agent_id}")
        print(f"  Status: {self.investigative_agent.status}")
        print(f"  Investigations started: {self.investigative_agent._metrics.get('investigations_started', 0)}")
        print(f"  Investigations completed: {self.investigative_agent._metrics.get('investigations_completed', 0)}")
        print(f"  Alerts generated: {self.investigative_agent._metrics.get('alerts_generated', 0)}")
        
        print("\n==========================================")

def main():
    """Main entry point for the enhanced security monitoring system"""
    parser = argparse.ArgumentParser(description="Enhanced Multi-agent Security Monitoring System")
    parser.add_argument("--run-time", type=int, default=10, 
                        help="How long to run the system (in seconds)")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to configuration file")
    args = parser.parse_args()
    
    system = EnhancedSecurityMonitoringSystem(config_file=args.config)
    
    try:
        # Start the system
        system.start()
        
        # Run for the specified time
        logger.info(f"System will run for {args.run_time} seconds...")
        time.sleep(args.run_time)
        
    except KeyboardInterrupt:
        logger.info("System interrupted by user")
    finally:
        # Generate final report
        system.report()
        
        # Stop the system
        system.stop()

if __name__ == "__main__":
    main()