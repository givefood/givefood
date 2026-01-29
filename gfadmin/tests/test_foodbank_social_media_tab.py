"""Tests for the removal of social media tab from foodbank admin page."""
import pytest
from django.test import Client
from django.urls import reverse

from givefood.models import Foodbank


@pytest.mark.django_db
class TestFoodbankSocialMediaTabRemoval:
    """Test that social media tab is not displayed on foodbank admin page."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def _create_foodbank(self, **kwargs):
        """Helper to create a foodbank with common defaults."""
        defaults = {
            'name': 'Test Foodbank',
            'url': 'https://example.com',
            'shopping_list_url': 'https://example.com/shopping',
            'address': '123 Test St',
            'postcode': 'AB12 3CD',
            'country': 'England',
            'lat_lng': '51.5074,-0.1278',
            'contact_email': 'test@example.com',
        }
        defaults.update(kwargs)
        foodbank = Foodbank(**defaults)
        foodbank.save(do_geoupdate=False, do_decache=False)
        return foodbank

    def _get_foodbank_page(self, foodbank):
        """Helper to get the foodbank admin page with authentication."""
        client = Client()
        self._setup_authenticated_session(client)
        return client.get(reverse('admin:foodbank', kwargs={'slug': foodbank.slug}))

    def test_social_media_tab_not_in_template_without_social_media(self):
        """Test that social media tab is not displayed when foodbank has no social media."""
        foodbank = self._create_foodbank()
        response = self._get_foodbank_page(foodbank)
        
        # Verify response
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify social media tab is not present
        assert 'socialmedia' not in content
        assert 'Social Media' not in content

    def test_social_media_tab_not_in_template_with_facebook(self):
        """Test that social media tab is not displayed even when foodbank has Facebook page."""
        foodbank = self._create_foodbank(facebook_page='testfoodbank')
        response = self._get_foodbank_page(foodbank)
        
        # Verify response
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify social media tab is not present
        assert 'data-tab="socialmedia"' not in content
        assert 'id="socialmedia-tab"' not in content
        assert 'id="socialmedia-panel"' not in content
        
        # Verify Facebook info is still in the "Info" section (General tab)
        assert 'facebook.com/testfoodbank' in content

    def test_social_media_tab_not_in_template_with_both(self):
        """Test that social media tab is not displayed when foodbank has Facebook."""
        foodbank = self._create_foodbank(
            facebook_page='testfoodbank'
        )
        response = self._get_foodbank_page(foodbank)
        
        # Verify response
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify social media tab is not present
        assert 'data-tab="socialmedia"' not in content
        assert 'id="socialmedia-tab"' not in content
        assert 'id="socialmedia-panel"' not in content
        
        # Verify social media info is still in the "Info" section
        # (Facebook link is displayed in the General tab)
        assert 'facebook.com/testfoodbank' in content
