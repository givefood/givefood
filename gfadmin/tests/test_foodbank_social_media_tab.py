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

    def test_social_media_tab_not_in_template_without_social_media(self):
        """Test that social media tab is not displayed when foodbank has no social media."""
        # Create a test foodbank without social media
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
        
        # Verify response
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify social media tab is not present
        assert 'socialmedia' not in content
        assert 'Social Media' not in content

    def test_social_media_tab_not_in_template_with_facebook(self):
        """Test that social media tab is not displayed even when foodbank has Facebook page."""
        # Create a test foodbank with Facebook page
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            facebook_page='testfoodbank',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a client and setup authenticated session
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbank', kwargs={'slug': foodbank.slug}))
        
        # Verify response
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify social media tab is not present
        assert 'data-tab="socialmedia"' not in content
        assert 'id="socialmedia-tab"' not in content
        assert 'id="socialmedia-panel"' not in content

    def test_social_media_tab_not_in_template_with_twitter(self):
        """Test that social media tab is not displayed even when foodbank has Twitter handle."""
        # Create a test foodbank with Twitter handle
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            twitter_handle='testfoodbank',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a client and setup authenticated session
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbank', kwargs={'slug': foodbank.slug}))
        
        # Verify response
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify social media tab is not present
        assert 'data-tab="socialmedia"' not in content
        assert 'id="socialmedia-tab"' not in content
        assert 'id="socialmedia-panel"' not in content

    def test_social_media_tab_not_in_template_with_both(self):
        """Test that social media tab is not displayed when foodbank has both Facebook and Twitter."""
        # Create a test foodbank with both Facebook and Twitter
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            facebook_page='testfoodbank',
            twitter_handle='testfoodbank',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a client and setup authenticated session
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbank', kwargs={'slug': foodbank.slug}))
        
        # Verify response
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify social media tab is not present
        assert 'data-tab="socialmedia"' not in content
        assert 'id="socialmedia-tab"' not in content
        assert 'id="socialmedia-panel"' not in content
        
        # Verify social media info is still in the "Info" section
        # (Facebook and Twitter links are displayed in the General tab)
        assert 'facebook.com/testfoodbank' in content
        assert 'twitter.com/testfoodbank' in content
