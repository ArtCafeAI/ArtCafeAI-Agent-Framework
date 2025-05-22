"""
Pytest configuration and shared fixtures for ArtCafe Agent Framework tests.
"""
import pytest
import sys
import os

# Add the project root to Python path so we can import modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return {
        "agent_id": "test-agent",
        "messaging": {
            "provider": "memory",
            "heartbeat_interval": 30
        },
        "llm": {
            "provider": "anthropic",
            "model": "claude-3-opus-20240229",
            "api_key": "test-key"
        },
        "logging": {
            "level": "INFO"
        }
    }