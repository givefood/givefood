"""
Tests for the gfapi3 (API v3) app.
"""
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestAPI3Index:
    """Test the API v3 index page."""

    def test_api3_index_accessible(self, client):
        """Test that the API v3 index page is accessible."""
        response = client.get('/api/3/')
        assert response.status_code == 200

    def test_api3_index_returns_expected_content(self, client):
        """Test that the API v3 index page returns expected content."""
        response = client.get('/api/3/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Give Food API 3' in content


@pytest.mark.django_db
class TestAPI3Company:
    """Test the API v3 company endpoint."""

    def test_company_not_found(self, client):
        """Test that an invalid company slug returns 404."""
        response = client.get('/api/3/donationpoints/company/nonexistent-company/')
        assert response.status_code == 404
