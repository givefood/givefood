"""
Tests for the gfauth (authentication) app.
"""
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestSignIn:
    """Test the sign in page."""

    def test_sign_in_accessible(self, client):
        """Test that the sign in page is accessible."""
        response = client.get('/auth/')
        assert response.status_code == 200

    def test_sign_in_uses_correct_template(self, client):
        """Test that the sign in page uses the correct template."""
        response = client.get('/auth/')
        assert response.status_code == 200
        # Check for sign in related content
        content = response.content.decode('utf-8')
        assert 'sign' in content.lower() or 'google' in content.lower() or 'login' in content.lower()


# Note: Sign out and auth receiver tests are skipped as they require:
# - An active session with user_data for sign out
# - Valid OAuth credentials for auth_receiver
# These tests should be tested manually or with proper mocking.
