"""Tests for the foodbank location area form functionality."""
import json
import pytest
from unittest.mock import Mock, patch
from django.test import Client
from django.urls import reverse

from givefood.models import Foodbank, FoodbankLocation


@pytest.mark.django_db
class TestFoodbankLocationAreaForm:
    """Test the foodbank location area form functionality."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def test_fblocation_area_form_get(self):
        """Test that the area form loads correctly."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='Independent',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a client and setup authenticated session
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:fblocation_area_new', kwargs={'slug': foodbank.slug}))
        
        # Check response is successful
        assert response.status_code == 200
        
        # Check that the form fields are in the response
        content = response.content.decode()
        assert 'name' in content.lower()
        assert 'mapit' in content.lower()

    @patch('gfadmin.views.requests.get')
    @patch('gfadmin.views.get_cred')
    def test_fblocation_area_form_post_success(self, mock_get_cred, mock_requests_get):
        """Test that posting valid data creates a location."""
        # Setup mock for get_cred
        mock_get_cred.return_value = 'test_api_key'
        
        # Setup mock responses for MapIt API calls
        geometry_response = Mock()
        geometry_response.status_code = 200
        geometry_response.json.return_value = {
            'centre_lat': 51.5074,
            'centre_lon': -0.1278,
        }
        
        geojson_response = Mock()
        geojson_response.status_code = 200
        geojson_response.json.return_value = {
            'type': 'Polygon',
            'coordinates': [[[-0.1, 51.5], [-0.2, 51.5], [-0.2, 51.6], [-0.1, 51.6], [-0.1, 51.5]]]
        }
        
        # Configure mock to return different responses for different URLs
        def side_effect(*args, **kwargs):
            if 'geometry' in args[0]:
                return geometry_response
            else:
                return geojson_response
        
        mock_requests_get.side_effect = side_effect
        
        # Create a test foodbank
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='Independent',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a client and setup authenticated session
        client = Client()
        self._setup_authenticated_session(client)
        
        # Post form data
        response = client.post(
            reverse('admin:fblocation_area_new', kwargs={'slug': foodbank.slug}),
            {
                'name': 'Test Area Location',
                'mapit_id': 2247,
            }
        )
        
        # Check that we're redirected to the foodbank page
        assert response.status_code == 302
        assert response.url == reverse('admin:foodbank', kwargs={'slug': foodbank.slug})
        
        # Check that a location was created
        locations = FoodbankLocation.objects.filter(foodbank=foodbank, name='Test Area Location')
        assert locations.count() == 1
        
        location = locations.first()
        assert location.lat_lng == '51.5074,-0.1278'
        assert location.boundary_geojson is not None
        
        # Check that boundary_geojson is properly formatted
        boundary_data = json.loads(location.boundary_geojson)
        assert boundary_data['type'] == 'Feature'
        assert 'geometry' in boundary_data
        assert boundary_data['geometry']['type'] == 'Polygon'

    @patch('gfadmin.views.requests.get')
    @patch('gfadmin.views.get_cred')
    def test_fblocation_area_form_post_api_error(self, mock_get_cred, mock_requests_get):
        """Test that API errors are handled gracefully."""
        # Setup mock for get_cred
        mock_get_cred.return_value = 'test_api_key'
        
        # Setup mock to return error response
        geometry_response = Mock()
        geometry_response.status_code = 404
        mock_requests_get.return_value = geometry_response
        
        # Create a test foodbank
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='Independent',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a client and setup authenticated session
        client = Client()
        self._setup_authenticated_session(client)
        
        # Post form data
        response = client.post(
            reverse('admin:fblocation_area_new', kwargs={'slug': foodbank.slug}),
            {
                'name': 'Test Area Location',
                'mapit_id': 9999,
            }
        )
        
        # Check that we're NOT redirected (form has errors)
        assert response.status_code == 200
        
        # Check that no location was created
        locations = FoodbankLocation.objects.filter(foodbank=foodbank, name='Test Area Location')
        assert locations.count() == 0
        
        # Check for error message in response
        content = response.content.decode()
        assert 'Failed to fetch' in content or 'error' in content.lower()
