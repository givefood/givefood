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


@pytest.mark.django_db
class TestSignOut:
    """Test the sign out functionality."""

    def test_sign_out_without_session_data(self, client):
        """Test that sign out works even when user_data is not in session."""
        response = client.get('/auth/sign-out/')
        # Should redirect to sign in page without raising KeyError
        assert response.status_code == 302
        assert response.url == '/auth/'

    def test_sign_out_with_session_data(self, client):
        """Test that sign out clears user_data from session."""
        # Set up a session with user_data
        session = client.session
        session['user_data'] = {'email': 'test@example.com'}
        session.save()

        response = client.get('/auth/sign-out/')
        # Should redirect to sign in page
        assert response.status_code == 302
        assert response.url == '/auth/'

        # Verify user_data is removed from session
        assert 'user_data' not in client.session
