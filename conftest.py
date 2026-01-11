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


@pytest.fixture
def admin_client():
    """
    Django test client with authenticated session for admin requests.
    Bypasses the LoginRequiredAccess middleware by setting proper session data.
    """
    client = Client()
    # Set up a session that will pass the LoginRequiredAccess middleware
    session = client.session
    session['user_data'] = {
        'email': 'test@givefood.org.uk',
        'email_verified': True,
        'hd': 'givefood.org.uk'
    }
    session.save()
    return client
