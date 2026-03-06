"""Tests for the admin map view."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAdminMapView:
    """Test the admin map view."""

    def test_map_page_returns_200(self, admin_client):
        """Test that the map page returns a 200 status code."""
        url = reverse('admin:map')
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_map_page_contains_map_div(self, admin_client):
        """Test that the map page contains the map div element."""
        url = reverse('admin:map')
        response = admin_client.get(url)
        content = response.content.decode('utf-8')
        assert 'id="map"' in content

    def test_map_page_contains_map_config(self, admin_client):
        """Test that the map page includes the map configuration."""
        url = reverse('admin:map')
        response = admin_client.get(url)
        content = response.content.decode('utf-8')
        assert 'window.gfMapConfig' in content

    def test_map_page_contains_maplibre(self, admin_client):
        """Test that the map page includes MapLibre GL JS."""
        url = reverse('admin:map')
        response = admin_client.get(url)
        content = response.content.decode('utf-8')
        assert 'maplibre-gl.js' in content

    def test_map_page_contains_wfbn_js(self, admin_client):
        """Test that the map page includes wfbn.js for map initialization."""
        url = reverse('admin:map')
        response = admin_client.get(url)
        content = response.content.decode('utf-8')
        assert 'wfbn.js' in content
