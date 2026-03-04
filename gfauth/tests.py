"""
Tests for the gfauth (authentication) app.
"""
import pytest
from django.test import Client
from django.urls import reverse
from unittest.mock import patch


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


@pytest.mark.django_db
class TestAuthReceiverRedirect:
    """Test that auth_receiver redirects to the stored next_url after login."""

    @patch('gfauth.views.id_token.verify_oauth2_token')
    def test_redirects_to_next_url_after_login(self, mock_verify, client):
        """Test redirect to stored next_url after successful authentication."""
        mock_verify.return_value = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }

        # Store a next_url in session (as middleware would)
        session = client.session
        session['next_url'] = '/admin/foodbanks/'
        session.save()

        response = client.post('/auth/receiver/', {'credential': 'fake-token'})
        assert response.status_code == 302
        assert response.url == '/admin/foodbanks/'
        # next_url should be consumed
        assert 'next_url' not in client.session

    @patch('gfauth.views.id_token.verify_oauth2_token')
    def test_redirects_to_sign_in_without_next_url(self, mock_verify, client):
        """Test redirect to sign_in when no next_url is stored."""
        mock_verify.return_value = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }

        response = client.post('/auth/receiver/', {'credential': 'fake-token'})
        assert response.status_code == 302
        assert response.url == '/auth/'

    @patch('gfauth.views.id_token.verify_oauth2_token')
    def test_ignores_non_relative_next_url(self, mock_verify, client):
        """Test that external URLs in next_url are ignored for safety."""
        mock_verify.return_value = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }

        session = client.session
        session['next_url'] = 'https://evil.com/steal'
        session.save()

        response = client.post('/auth/receiver/', {'credential': 'fake-token'})
        assert response.status_code == 302
        assert response.url == '/auth/'

    @patch('gfauth.views.id_token.verify_oauth2_token')
    def test_ignores_protocol_relative_next_url(self, mock_verify, client):
        """Test that protocol-relative URLs in next_url are ignored."""
        mock_verify.return_value = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }

        session = client.session
        session['next_url'] = '//evil.com/steal'
        session.save()

        response = client.post('/auth/receiver/', {'credential': 'fake-token'})
        assert response.status_code == 302
        assert response.url == '/auth/'
