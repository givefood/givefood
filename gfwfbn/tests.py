"""Tests for gfwfbn views"""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestGeojsonView:
    """Test the geojson endpoint with .only() optimization"""

    def test_geojson_all_items_returns_valid_json(self, client):
        """
        Test that the geojson endpoint for all items returns valid JSON
        with empty database.
        """
        response = client.get(reverse('wfbn:geojson'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        data = response.json()
        assert 'type' in data
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert isinstance(data['features'], list)
