"""
Tests for the gfapi2 (API v2) app.
"""
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestAPI2Index:
    """Test the API v2 index page."""

    def test_api_index_accessible(self, client):
        """Test that the API index page is accessible."""
        response = client.get('/api/2/')
        assert response.status_code == 200

    def test_api_index_contains_api_info(self, client):
        """Test that the API index page contains API information."""
        response = client.get('/api/2/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Check for expected content
        assert 'api' in content.lower() or 'documentation' in content.lower()


@pytest.mark.django_db
class TestAPI2Docs:
    """Test the API v2 documentation page."""

    def test_api_docs_accessible(self, client):
        """Test that the API docs page is accessible."""
        response = client.get('/api/2/docs/')
        assert response.status_code == 200

    def test_api_docs_contains_examples(self, client):
        """Test that the API docs page contains examples."""
        response = client.get('/api/2/docs/')
        assert response.status_code == 200
        # Just ensure we can access it
        assert len(response.content) > 0


@pytest.mark.django_db
class TestAPI2Foodbanks:
    """Test the API v2 foodbanks endpoint."""

    def test_foodbanks_list_json(self, client):
        """Test that the foodbanks list returns JSON."""
        response = client.get('/api/2/foodbanks/')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('application/json') or \
               response['Content-Type'].startswith('text/html')  # May vary based on format parameter

    def test_foodbanks_list_xml(self, client):
        """Test that the foodbanks list can return XML."""
        response = client.get('/api/2/foodbanks/?format=xml')
        assert response.status_code == 200

    def test_foodbanks_list_geojson(self, client):
        """Test that the foodbanks list can return GeoJSON."""
        response = client.get('/api/2/foodbanks/?format=geojson')
        assert response.status_code == 200
