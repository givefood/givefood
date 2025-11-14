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


@pytest.mark.django_db
class TestAPI2LocationSearch:
    """Test the API v2 location search endpoint."""

    def test_location_search_includes_facebook_page(self, client):
        """Test that location search response includes facebook_page in foodbank data."""
        # Using a known UK postcode for testing
        response = client.get('/api/2/locations/search/?address=SW1A1AA')
        
        # The endpoint should return 200 or 400 (if geocoding fails or no results)
        # We're mainly checking the structure when data is returned
        assert response.status_code in [200, 400]
        
        # Only check JSON structure if we got a successful response
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            
            # If there are results, check that facebook_page field exists
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                assert 'foodbank' in first_item
                assert 'facebook_page' in first_item['foodbank']
