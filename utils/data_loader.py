import json
import os
from typing import Dict, List, Any

def load_json_file(file_path: str) -> Any:
    """Load data from a JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def load_guardduty_findings() -> List[Dict[str, Any]]:
    """Load mock GuardDuty findings data"""
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                            'data', 'mock_guardduty_findings.json')
    return load_json_file(file_path)

def load_customer_data() -> Dict[str, Any]:
    """Load mock customer data"""
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                            'data', 'mock_customer_data.json')
    return load_json_file(file_path)

def get_customer_resource_details(account_id: str, resource_type: str, resource_id: str) -> Dict[str, Any]:
    """Get specific customer resource details"""
    customer_data = load_customer_data()
    
    if account_id not in customer_data['customers']:
        return {}
    
    customer = customer_data['customers'][account_id]
    
    if resource_type not in customer['resources']:
        return {}
    
    resources = customer['resources'][resource_type]
    
    if resource_id not in resources:
        return {}
    
    return resources[resource_id]