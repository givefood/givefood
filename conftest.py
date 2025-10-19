"""
Shared pytest fixtures and configuration for Give Food tests.
"""
import pytest
from django.test import Client


@pytest.fixture
def client():
    """
    Django test client for making HTTP requests.
    """
    return Client()


@pytest.fixture
def api_client():
    """
    Django test client specifically for API requests.
    """
    return Client()
