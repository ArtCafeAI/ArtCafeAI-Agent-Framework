import json
import os
import uuid
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("BedrockClient")

class BedrockClient:
    """
    A client for Amazon Bedrock to interact with Claude 3.7 Sonnet.
    
    This implementation uses boto3 to call Amazon Bedrock API.
    """
    
    def __init__(self):
        # Claude 3.7 Sonnet model ID - using us region model ID
        self.model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        
        # Initialize the Bedrock client
        try:
            self.bedrock_runtime = boto3.client('bedrock-runtime')
            logger.info(f"Successfully initialized Bedrock runtime client")
        except Exception as e:
            logger.error(f"Error initializing Bedrock client: {e}")
            logger.warning("Falling back to mock implementation")
            self.bedrock_runtime = None
    
    def generate_finding(self, scenario_description: str) -> Dict[str, Any]:
        """
        Generate a realistic AWS GuardDuty finding based on the scenario description.
        
        Uses Claude 3.7 via Bedrock to generate the finding.
        """
        logger.info(f"Generating GuardDuty finding for scenario: {scenario_description}")
        
        # If Bedrock client initialization failed, fall back to mock implementation
        if self.bedrock_runtime is None:
            logger.warning("Using mock implementation for generate_finding")
            return self._mock_generate_finding(scenario_description)
        
        try:
            # Create the prompt for Claude
            prompt = f"""Create a realistic AWS GuardDuty finding JSON for this scenario: {scenario_description}

The JSON should have these fields:
- id: a UUID
- type: a realistic GuardDuty finding type (e.g., "UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B")
- severity: a float between 1.0 and 8.9
- region: an AWS region
- resourceType: the type of resource involved (e.g., "AccessKey", "Instance")
- createdAt: current ISO timestamp
- description: detailed description of the finding
- accountId: "123456789012"
- resourceId: appropriate ID for the resource type
- details: object with appropriate details for this type of finding

Note: Only respond with the JSON object. No markdown formatting, no explanations, just the raw JSON.
"""
            # Call Bedrock with correct Claude 3.7 parameters format
            body_params = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.2,  # Lower temperature for more deterministic JSON
                "system": "You are an AWS GuardDuty finding generator. Create realistic, detailed AWS GuardDuty findings in JSON format.",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            logger.info(f"Calling Bedrock with parameters: {json.dumps(body_params)}")
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body_params)
            )
            
            # Parse the response
            response_bytes = response['body'].read()
            response_body = json.loads(response_bytes)
            
            # Debug the response structure
            logger.info(f"Response keys: {list(response_body.keys())}")
            
            # Extract content based on the response structure
            if 'content' in response_body and len(response_body['content']) > 0:
                llm_response = response_body['content'][0]['text']
                logger.info(f"Using content[0].text for response")
            elif 'completion' in response_body:
                llm_response = response_body['completion']
                logger.info(f"Using completion for response")
            else:
                logger.error(f"Unexpected response format: {response_body}")
                raise ValueError(f"Unexpected response format from Bedrock")
            
            # Extract JSON from response
            try:
                # Try to parse the response as JSON
                finding = json.loads(llm_response)
                
                # Ensure all required fields are present
                required_fields = ['id', 'type', 'severity', 'region', 'resourceType', 
                                 'createdAt', 'description', 'accountId', 'resourceId']
                
                for field in required_fields:
                    if field not in finding:
                        raise ValueError(f"Missing required field: {field}")
                
                # Ensure details is an object
                if 'details' not in finding or not isinstance(finding['details'], dict):
                    finding['details'] = {
                        "ipAddressV4": "203.0.113.1",
                        "additionalInfo": {}
                    }
                
                logger.info(f"Successfully generated finding with Bedrock: {finding['id']} of type {finding['type']}")
                return finding
                
            except json.JSONDecodeError:
                logger.error("Failed to parse Bedrock response as JSON")
                logger.debug(f"Raw response: {llm_response}")
                # Fall back to mock implementation
                return self._mock_generate_finding(scenario_description)
                
        except Exception as e:
            logger.error(f"Error calling Bedrock: {e}")
            # Fall back to mock implementation
            return self._mock_generate_finding(scenario_description)
    
    def _mock_generate_finding(self, scenario_description: str) -> Dict[str, Any]:
        """
        Mock implementation for generating a GuardDuty finding when Bedrock is unavailable.
        """
        logger.info(f"Using mock implementation to generate finding for: {scenario_description}")
        
        # Define common finding types with their typical severity ranges
        finding_types = [
            {
                "type": "UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B",
                "severity_range": (4.0, 7.0),
                "description_template": "AWS Management Console was successfully accessed by a user from an unusual location.",
                "resource_type": "AccessKey",
                "details": {
                    "location": {"country": "RU", "city": "Moscow"},
                    "additionalInfo": {
                        "recentApiCalls": [
                            {"api": "ConsoleLogin", "count": 1},
                            {"api": "ListUsers", "count": 2},
                            {"api": "DescribeInstances", "count": 3}
                        ]
                    }
                }
            },
            {
                "type": "CredentialAccess:IAMUser/AnomalousBehavior",
                "severity_range": (5.0, 8.0),
                "description_template": "An API commonly used to access credentials was invoked in an unusual way.",
                "resource_type": "AccessKey",
                "details": {
                    "service": "iam.amazonaws.com",
                    "additionalInfo": {
                        "recentApiCalls": [
                            {"api": "GetCredentialReport", "count": 1},
                            {"api": "ListAccessKeys", "count": 3},
                            {"api": "GetUser", "count": 2}
                        ]
                    }
                }
            },
            {
                "type": "Discovery:S3/BucketEnumeration",
                "severity_range": (3.0, 5.0),
                "description_template": "An IAM entity invoked an S3 API commonly used to discover S3 buckets in your account.",
                "resource_type": "AccessKey",
                "details": {
                    "service": "s3.amazonaws.com",
                    "additionalInfo": {
                        "recentApiCalls": [
                            {"api": "ListBuckets", "count": 4},
                            {"api": "GetBucketLocation", "count": 3},
                            {"api": "GetBucketAcl", "count": 2}
                        ]
                    }
                }
            },
            {
                "type": "Persistence:IAMUser/NetworkPermissions",
                "severity_range": (6.0, 8.5),
                "description_template": "An IAM entity invoked an API commonly used to change the network access permissions for security groups, routes and ACLs.",
                "resource_type": "AccessKey",
                "details": {
                    "service": "ec2.amazonaws.com",
                    "additionalInfo": {
                        "recentApiCalls": [
                            {"api": "AuthorizeSecurityGroupIngress", "count": 2},
                            {"api": "ModifyVpcEndpoint", "count": 1},
                            {"api": "CreateNetworkAcl", "count": 1}
                        ]
                    }
                }
            },
            {
                "type": "Execution:EC2/SuspiciousFile",
                "severity_range": (7.0, 9.0),
                "description_template": "A suspicious file was detected on EC2 instance i-0123456789abcdef0.",
                "resource_type": "Instance",
                "details": {
                    "filepath": "/tmp/suspicious_file.elf",
                    "fileHash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    "processPaths": ["/bin/bash", "/usr/bin/curl"]
                }
            }
        ]
        
        # Select a finding type based on the scenario description
        if "credential" in scenario_description.lower() or "password" in scenario_description.lower():
            finding_type = next((f for f in finding_types if "Credential" in f["type"]), finding_types[1])
        elif "bucket" in scenario_description.lower() or "s3" in scenario_description.lower():
            finding_type = next((f for f in finding_types if "S3" in f["type"]), finding_types[2])
        elif "network" in scenario_description.lower() or "firewall" in scenario_description.lower():
            finding_type = next((f for f in finding_types if "Network" in f["type"]), finding_types[3])
        elif "malware" in scenario_description.lower() or "file" in scenario_description.lower():
            finding_type = next((f for f in finding_types if "SuspiciousFile" in f["type"]), finding_types[4])
        elif "login" in scenario_description.lower() or "console" in scenario_description.lower():
            finding_type = next((f for f in finding_types if "ConsoleLogin" in f["type"]), finding_types[0])
        else:
            # Random selection for generic descriptions
            import random
            finding_type = random.choice(finding_types)
        
        # Generate a realistic severity within the range for this finding type
        import random
        min_severity, max_severity = finding_type["severity_range"]
        severity = round(random.uniform(min_severity, max_severity), 1)
        
        # Generate a finding ID
        finding_id = str(uuid.uuid4())
        
        # Generate the account ID
        account_id = "123456789012"  # Use a constant for demo purposes
        
        # Generate a resource ID appropriate for the resource type
        if finding_type["resource_type"] == "AccessKey":
            resource_id = f"AKIA{finding_id.replace('-', '').upper()[:16]}"
        elif finding_type["resource_type"] == "Instance":
            resource_id = f"i-{finding_id.replace('-', '')[:17]}"
        else:
            resource_id = finding_id.replace('-', '')[:20]
        
        # Use the scenario description to customize the finding description
        description = finding_type["description_template"]
        if len(scenario_description) > 10:  # If a meaningful scenario was provided
            description = f"{description} {scenario_description}"
        
        # Generate the finding
        finding = {
            "id": finding_id,
            "type": finding_type["type"],
            "severity": severity,
            "region": "us-east-1",
            "resourceType": finding_type["resource_type"],
            "createdAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "description": description,
            "accountId": account_id,
            "resourceId": resource_id,
            "details": {
                "ipAddressV4": "203.0.113.1",  # Example IP from TEST-NET-3 block
                **finding_type["details"]
            }
        }
        
        logger.info(f"Generated mock finding: {finding['id']} of type {finding['type']}")
        return finding
    
    def generate_advanced_finding(self, scenario_description: str) -> Dict[str, Any]:
        """
        Generate a more complex finding using Claude 3.7's capabilities via Bedrock.
        
        This version includes advanced security details like tactics, risk scores,
        and more detailed context.
        """
        logger.info(f"Generating advanced GuardDuty finding for scenario: {scenario_description}")
        
        # If Bedrock client initialization failed, fall back to mock implementation
        if self.bedrock_runtime is None:
            logger.warning("Using mock implementation for generate_advanced_finding")
            return self._mock_generate_advanced_finding(scenario_description)
        
        try:
            # Create the prompt for Claude
            prompt = f"""Create a sophisticated AWS GuardDuty finding JSON for this security scenario: {scenario_description}

The JSON should have these standard fields:
- id: a UUID
- type: a realistic GuardDuty finding type (e.g., "UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B")
- severity: a float between 1.0 and 8.9
- region: an AWS region
- resourceType: the type of resource involved (e.g., "AccessKey", "Instance")
- createdAt: current ISO timestamp
- description: detailed description of the finding (at least 1-2 sentences)
- accountId: "123456789012"
- resourceId: appropriate ID for the resource type

And these advanced fields in the details object:
- tactics: array of MITRE ATT&CK tactics that apply to this finding
- service: the AWS service involved
- ipAddressV4: source IP address (use a realistic but fictional address)
- riskScore: numeric risk score from 0-100
- additionalInfo: object with context-specific details like:
  - affectedResources: list of other resources affected
  - recentApiCalls: array of API calls related to the attack
  - any other relevant context like dataVolume, destinations, etc.

Note: Only respond with the JSON object. No markdown formatting, no explanations, just the raw JSON.
"""
            # Call Bedrock with correct Claude 3.7 parameters format
            body_params = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.2,  # Lower temperature for more deterministic JSON
                "system": "You are an advanced AWS GuardDuty finding generator with expertise in cloud security. Create realistic, detailed AWS GuardDuty findings in JSON format with advanced security context like MITRE ATT&CK tactics and specific attack details.",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            logger.info(f"Calling Bedrock with parameters: {json.dumps(body_params)}")
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body_params)
            )
            
            # Parse the response
            response_bytes = response['body'].read()
            response_body = json.loads(response_bytes)
            
            # Debug the response structure
            logger.info(f"Advanced response keys: {list(response_body.keys())}")
            
            # Extract content based on the response structure
            if 'content' in response_body and len(response_body['content']) > 0:
                llm_response = response_body['content'][0]['text']
                logger.info(f"Using content[0].text for advanced response")
            elif 'completion' in response_body:
                llm_response = response_body['completion']
                logger.info(f"Using completion for advanced response")
            else:
                logger.error(f"Unexpected advanced response format: {response_body}")
                raise ValueError(f"Unexpected response format from Bedrock")
            
            # Extract JSON from response
            try:
                # Try to parse the response as JSON
                finding = json.loads(llm_response)
                
                # Ensure all required fields are present
                required_fields = ['id', 'type', 'severity', 'region', 'resourceType', 
                                 'createdAt', 'description', 'accountId', 'resourceId']
                
                for field in required_fields:
                    if field not in finding:
                        raise ValueError(f"Missing required field: {field}")
                
                # Ensure details is an object
                if 'details' not in finding or not isinstance(finding['details'], dict):
                    finding['details'] = {
                        "ipAddressV4": "203.0.113.1",
                        "additionalInfo": {},
                        "tactics": ["Discovery", "Collection"],
                        "riskScore": round(finding['severity'] * 10)
                    }
                
                # Ensure details has tactics and riskScore
                if 'tactics' not in finding['details']:
                    finding['details']['tactics'] = ["Discovery", "Collection"]
                
                if 'riskScore' not in finding['details']:
                    finding['details']['riskScore'] = round(finding['severity'] * 10)
                
                logger.info(f"Successfully generated advanced finding with Bedrock: {finding['id']} of type {finding['type']}")
                return finding
                
            except json.JSONDecodeError:
                logger.error("Failed to parse Bedrock advanced response as JSON")
                logger.debug(f"Raw advanced response: {llm_response}")
                # Fall back to mock implementation
                return self._mock_generate_advanced_finding(scenario_description)
                
        except Exception as e:
            logger.error(f"Error calling Bedrock for advanced finding: {e}")
            # Fall back to mock implementation
            return self._mock_generate_advanced_finding(scenario_description)
    
    def _mock_generate_advanced_finding(self, scenario_description: str) -> Dict[str, Any]:
        """
        Mock implementation for generating an advanced GuardDuty finding when Bedrock is unavailable.
        """
        logger.info(f"Using mock implementation to generate advanced finding for: {scenario_description}")
        
        # Generate a basic finding first
        base_finding = self._mock_generate_finding(scenario_description)
        
        # Enhance the finding with additional fields
        resources_affected = ["S3Bucket", "EC2Instance", "IAMRole", "Lambda"]
        import random
        
        # Add more realistic details based on the prompt
        if "lateral movement" in scenario_description.lower():
            base_finding["details"]["tactics"] = ["LateralMovement", "PrivilegeEscalation"]
            base_finding["details"]["additionalInfo"]["affectedResources"] = [
                random.choice(resources_affected) for _ in range(2)
            ]
        elif "data exfiltration" in scenario_description.lower():
            base_finding["details"]["tactics"] = ["Exfiltration", "Impact"]
            base_finding["details"]["additionalInfo"]["dataVolume"] = f"{random.randint(1, 999)} MB"
            base_finding["details"]["additionalInfo"]["destination"] = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
        else:
            # Generic enhancements
            base_finding["details"]["tactics"] = ["Discovery", "Collection"]
            
        # Add a service name if not present
        if "service" not in base_finding["details"]:
            base_finding["details"]["service"] = random.choice(["ec2.amazonaws.com", "iam.amazonaws.com", "s3.amazonaws.com", "lambda.amazonaws.com"])
        
        # Add a risk score
        base_finding["details"]["riskScore"] = round(base_finding["severity"] * 10)
        
        return base_finding