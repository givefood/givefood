"""
Tests for the gfapi3 (API v3) app.
"""
import uuid
import pytest
from django.test import Client
from django.urls import reverse
from givefood.models import Foodbank


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


@pytest.mark.django_db
class TestAPI3SlugFromId:
    """Test the API v3 slugfromid endpoint."""

    def test_slugfromid_returns_slug_as_plain_text(self, client):
        """Test that a valid UUID returns the foodbank slug as plain text."""
        foodbank = Foodbank(
            name="Test Food Bank",
            slug="test-food-bank",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        response = client.get(f'/api/3/slugfromid/{foodbank.uuid}/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/plain; charset=utf-8'
        assert response.content.decode('utf-8') == 'test-food-bank'

    def test_slugfromid_not_found(self, client):
        """Test that an unknown UUID returns 404."""
        unknown_uuid = uuid.uuid4()
        response = client.get(f'/api/3/slugfromid/{unknown_uuid}/')
        assert response.status_code == 404
