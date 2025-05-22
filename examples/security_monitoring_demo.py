#!/usr/bin/env python3

import time
import logging
import argparse
import threading
import json
from typing import Dict, List, Any

from agents.triage_agent import TriageAgent
from agents.investigative_agent import InvestigativeAgent
from examples.mock_pubsub import subscribe, create_agent_token

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MainSystem')

class SecurityMonitoringSystem:
    """
    Main class that orchestrates the multi-agent security monitoring system.
    
    This class:
    1. Initializes the agents
    2. Subscribes to relevant topics for reporting
    3. Manages the agents' lifecycle
    """
    
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.investigative_agent = InvestigativeAgent()
        
        # Create a monitor token for subscribing to all topics
        self.monitor_token = create_agent_token("system-monitor", ["*"])
        
        # Store all alerts and reports
        self.alerts = []
        self.investigation_reports = []
    
    def start(self):
        """Start the security monitoring system"""
        logger.info("Starting Security Monitoring System...")
        
        # Subscribe to investigation reports
        subscribe(self.monitor_token, "agents/investigation/reports", self._handle_investigation_report)
        
        # Subscribe to all alerts
        subscribe(self.monitor_token, "agents/alerts/#", self._handle_alert)
        
        # Start the agents
        self.investigative_agent.start()
        time.sleep(1)  # Ensure investigative agent is ready before triage agent starts sending requests
        self.triage_agent.start()
        
        logger.info("Security Monitoring System started")
    
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
        logger.info("Stopping Security Monitoring System...")
        
        # Stop the agents
        self.triage_agent.stop()
        self.investigative_agent.stop()
        
        logger.info("Security Monitoring System stopped")
    
    def report(self):
        """Generate a summary report of all activity"""
        alert_count = len(self.alerts)
        report_count = len(self.investigation_reports)
        
        threat_count = sum(1 for report in self.investigation_reports 
                          if report["investigation_result"]["is_threat"])
        
        print("\n===== SECURITY MONITORING SYSTEM REPORT =====")
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

def main():
    """Main entry point for the security monitoring system"""
    parser = argparse.ArgumentParser(description="Multi-agent Security Monitoring System")
    parser.add_argument("--run-time", type=int, default=10, 
                        help="How long to run the system (in seconds)")
    args = parser.parse_args()
    
    system = SecurityMonitoringSystem()
    
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