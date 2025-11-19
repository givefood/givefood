"""
Tests for gfadmin2 views

These tests verify that:
1. Views are accessible
2. htmx requests work correctly
3. Templates render without errors
"""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAdmin2Index:
    """Test the admin2 index/dashboard view."""
    
    def test_index_accessible(self, client):
        """Test that the admin2 index is accessible."""
        url = reverse('gfadmin2:index')
        response = client.get(url)
        assert response.status_code == 200
        
    def test_index_contains_htmx(self, client):
        """Test that htmx is loaded."""
        url = reverse('gfadmin2:index')
        response = client.get(url)
        assert b'htmx.org' in response.content


@pytest.mark.django_db
class TestAdmin2Foodbanks:
    """Test the foodbanks list view."""
    
    def test_foodbanks_list_accessible(self, client):
        """Test that the foodbanks list is accessible."""
        url = reverse('gfadmin2:foodbanks_list')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_foodbanks_list_htmx_request(self, client):
        """Test that htmx requests return fragments."""
        url = reverse('gfadmin2:foodbanks_list')
        response = client.get(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        # htmx response should not include full page structure
        assert b'<!DOCTYPE html>' not in response.content


@pytest.mark.django_db
class TestAdmin2Needs:
    """Test the needs views."""
    
    def test_needs_list_accessible(self, client):
        """Test that the needs list is accessible."""
        url = reverse('gfadmin2:needs_list')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_needs_list_with_filter(self, client):
        """Test that needs list accepts filter parameter."""
        url = reverse('gfadmin2:needs_list')
        response = client.get(url, {'filter': 'published'})
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdmin2Search:
    """Test the search functionality."""
    
    def test_search_accessible(self, client):
        """Test that search is accessible."""
        url = reverse('gfadmin2:search')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_search_with_query(self, client):
        """Test search with query parameter."""
        url = reverse('gfadmin2:search')
        response = client.get(url, {'q': 'test'})
        assert response.status_code == 200
    
    def test_search_htmx_request(self, client):
        """Test that search htmx requests work."""
        url = reverse('gfadmin2:search')
        response = client.get(url, {'q': 'test'}, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
