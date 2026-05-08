"""
Pytest configuration and fixtures for AI Batch Inference tests
Patches Redis before any modules that use it are imported
"""

import sys
from unittest.mock import MagicMock, patch


# Patch redis.Redis BEFORE any module imports it
def pytest_configure(config):
    """pytest hook - runs before collecting tests"""
    import os
    os.environ.setdefault("METRICS_ALLOWED_HOSTS", "127.0.0.1,testclient")
    
    # Create a mock Redis client
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.lpush.return_value = 1
    mock_redis.lpop.return_value = None
    mock_redis.llen.return_value = 0
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = 1
    
    # Patch redis.Redis before tests import modules
    import redis
    original_redis = redis.Redis
    redis.Redis = MagicMock(return_value=mock_redis)
    
    # Store original for cleanup if needed
    config._original_redis = original_redis


import pytest


@pytest.fixture(autouse=True)
def ensure_mocks():
    """Ensure mocks remain in place during tests"""
    # Just a safety check that mocking is active
    import redis
    assert isinstance(redis.Redis(), MagicMock) or isinstance(redis.Redis(), type(MagicMock()))
    yield




