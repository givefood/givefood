"""Tests for the foodbank touch functionality."""
import pytest
from datetime import datetime, timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from givefood.models import Foodbank


@pytest.mark.django_db
class TestFoodbankTouch:
    """Test the foodbank touch functionality."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def test_touch_button_appears_on_foodbank_page(self):
        """Test that the touch button appears on the foodbank admin page."""
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
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a client and setup authenticated session
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbank', kwargs={'slug': foodbank.slug}))
        
        # Check response is successful
        assert response.status_code == 200
        
        # Check that the touch button form is in the response
        content = response.content.decode()
        # The template uses {% url 'admin:foodbank_touch' foodbank.slug %} which resolves to /admin/foodbank/SLUG/touch/
        assert f'/admin/foodbank/{foodbank.slug}/touch/' in content
        assert 'value="Touch"' in content
        # Also check that the Edit button appears
        assert 'Edit Food Bank' in content

    def test_touch_updates_edited_timestamp(self):
        """Test that touching a foodbank updates its edited timestamp."""
        # Create a test foodbank with an old edited timestamp
        old_time = timezone.now() - timedelta(days=30)
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Manually set the edited timestamp to an old time
        Foodbank.objects.filter(slug=foodbank.slug).update(edited=old_time)
        
        # Refresh the foodbank from database
        foodbank.refresh_from_db()
        assert foodbank.edited == old_time
        
        # Create a client with authenticated session and touch the foodbank
        client = Client()
        self._setup_authenticated_session(client)
        response = client.post(reverse('admin:foodbank_touch', kwargs={'slug': foodbank.slug}))
        
        # Check that we're redirected to the foodbanks list
        assert response.status_code == 302
        assert response.url == reverse('admin:foodbanks')
        
        # Refresh the foodbank from database
        foodbank.refresh_from_db()
        
        # Check that the edited timestamp has been updated (within the last minute)
        time_diff = timezone.now() - foodbank.edited
        assert time_diff.total_seconds() < 60

    def test_touch_requires_post(self):
        """Test that touch requires a POST request."""
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
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Try to GET the touch URL with authenticated session (should fail)
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbank_touch', kwargs={'slug': foodbank.slug}))
        
        # Should return 405 Method Not Allowed
        assert response.status_code == 405
