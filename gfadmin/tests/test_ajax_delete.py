"""Tests for AJAX deletion of locations and donation points."""
import pytest
import json
from django.test import Client
from givefood.models import Foodbank, FoodbankLocation, FoodbankDonationPoint


@pytest.fixture
def authenticated_client():
    """Create an authenticated test client."""
    client = Client()
    # Set up session with authentication data
    session = client.session
    session['user_data'] = {
        'email': 'test@givefood.org.uk',
        'email_verified': True,
        'hd': 'givefood.org.uk'
    }
    session.save()
    return client


@pytest.mark.django_db
class TestAjaxLocationDelete:
    """Test AJAX deletion of food bank locations."""

    def test_location_delete_ajax_returns_json(self, authenticated_client):
        """Test that AJAX request returns JSON response."""
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
            network='',  # Set to empty string to avoid NOT NULL constraint
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a test location
        location = FoodbankLocation(
            foodbank=foodbank,
            name='Test Location',
            address='456 Location St',
            postcode='CD34 5EF',
            lat_lng='51.5074,-0.1278',
        )
        location.save(do_geoupdate=False)
        
        # Make AJAX request to delete
        response = authenticated_client.post(
            f'/admin/foodbank/{foodbank.slug}/location/{location.slug}/delete/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'message' in data
        
        # Verify location was deleted
        assert FoodbankLocation.objects.filter(slug=location.slug).count() == 0

    def test_location_delete_non_ajax_redirects(self, authenticated_client):
        """Test that non-AJAX request redirects to foodbank page."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='Redirect Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='',  # Set to empty string to avoid NOT NULL constraint
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a test location
        location = FoodbankLocation(
            foodbank=foodbank,
            name='Test Location',
            address='456 Location St',
            postcode='CD34 5EF',
            lat_lng='51.5074,-0.1278',
        )
        location.save(do_geoupdate=False)
        
        # Make normal POST request (not AJAX)
        response = authenticated_client.post(
            f'/admin/foodbank/{foodbank.slug}/location/{location.slug}/delete/'
        )
        
        # Verify redirect
        assert response.status_code == 302
        assert response.url == f'/admin/foodbank/{foodbank.slug}/'
        
        # Verify location was deleted
        assert FoodbankLocation.objects.filter(slug=location.slug).count() == 0

    def test_location_delete_nonexistent_returns_404(self, authenticated_client):
        """Test that deleting a non-existent location returns 404."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='404 Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='',  # Set to empty string to avoid NOT NULL constraint
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Try to delete non-existent location
        response = authenticated_client.post(
            f'/admin/foodbank/{foodbank.slug}/location/nonexistent-location/delete/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Verify 404 response
        assert response.status_code == 404


@pytest.mark.django_db
class TestAjaxDonationPointDelete:
    """Test AJAX deletion of donation points."""

    def test_donation_point_delete_ajax_returns_json(self, authenticated_client):
        """Test that AJAX request returns JSON response."""
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
            network='',  # Set to empty string to avoid NOT NULL constraint
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a test donation point
        donation_point = FoodbankDonationPoint(
            foodbank=foodbank,
            name='Test Donation Point',
            address='789 Donation St',
            postcode='EF56 7GH',
            lat_lng='51.5074,-0.1278',
        )
        donation_point.save(do_geoupdate=False)
        
        # Make AJAX request to delete
        response = authenticated_client.post(
            f'/admin/foodbank/{foodbank.slug}/donationpoint/{donation_point.slug}/delete/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'message' in data
        
        # Verify donation point was deleted
        assert FoodbankDonationPoint.objects.filter(slug=donation_point.slug).count() == 0

    def test_donation_point_delete_non_ajax_redirects(self, authenticated_client):
        """Test that non-AJAX request redirects to foodbank page."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='Redirect Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='',  # Set to empty string to avoid NOT NULL constraint
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a test donation point
        donation_point = FoodbankDonationPoint(
            foodbank=foodbank,
            name='Test Donation Point',
            address='789 Donation St',
            postcode='EF56 7GH',
            lat_lng='51.5074,-0.1278',
        )
        donation_point.save(do_geoupdate=False)
        
        # Make normal POST request (not AJAX)
        response = authenticated_client.post(
            f'/admin/foodbank/{foodbank.slug}/donationpoint/{donation_point.slug}/delete/'
        )
        
        # Verify redirect
        assert response.status_code == 302
        assert response.url == f'/admin/foodbank/{foodbank.slug}/'
        
        # Verify donation point was deleted
        assert FoodbankDonationPoint.objects.filter(slug=donation_point.slug).count() == 0

    def test_donation_point_delete_nonexistent_returns_404(self, authenticated_client):
        """Test that deleting a non-existent donation point returns 404."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='404 Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='',  # Set to empty string to avoid NOT NULL constraint
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Try to delete non-existent donation point
        response = authenticated_client.post(
            f'/admin/foodbank/{foodbank.slug}/donationpoint/nonexistent-point/delete/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Verify 404 response
        assert response.status_code == 404


