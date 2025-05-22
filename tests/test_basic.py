"""
Basic smoke tests for the ArtCafe Agent Framework.
"""
import pytest


def test_framework_imports():
    """Test that core framework modules can be imported."""
    from framework.core import base_agent, enhanced_agent, config
    from framework.messaging import interface, memory_provider
    from framework.tools import decorator, registry
    
    assert base_agent is not None
    assert enhanced_agent is not None
    assert config is not None
    assert interface is not None
    assert memory_provider is not None
    assert decorator is not None
    assert registry is not None


def test_agent_imports():
    """Test that agent modules can be imported."""
    from agents import investigative_agent, triage_agent
    
    assert investigative_agent is not None
    assert triage_agent is not None


def test_version_info():
    """Test that version information is available."""
    import framework
    # Framework should have basic info
    assert hasattr(framework, '__version__') or hasattr(framework, 'VERSION')