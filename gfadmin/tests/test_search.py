"""Tests for the admin search functionality."""
import pytest
from django.test import Client
from django.urls import reverse

from givefood.models import Foodbank, FoodbankChange


@pytest.mark.django_db
class TestSearchResults:
    """Test the search_results view."""

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
        """Helper method to create a foodbank with minimal required fields."""
        defaults = {
            'name': 'Test Food Bank',
            'address': '123 Test St',
            'postcode': 'TE1 1ST',
            'lat_lng': '51.5074,-0.1278',
            'country': 'England',
            'url': 'https://example.com',
            'shopping_list_url': 'https://example.com/list',
            'contact_email': 'test@example.com',
        }
        defaults.update(kwargs)
        foodbank = Foodbank(**defaults)
        foodbank.latitude = 51.5074
        foodbank.longitude = -0.1278
        foodbank.save(do_geoupdate=False)
        return foodbank

    def test_search_finds_foodbank_by_name(self):
        """Test that search finds food banks by name."""
        self._create_foodbank(name='Manchester Food Bank')
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'Manchester'})
        
        assert response.status_code == 200
        assert 'Manchester Food Bank' in response.content.decode()

    def test_search_finds_foodbank_by_main_url(self):
        """Test that search finds food banks by main URL."""
        self._create_foodbank(name='Test FB', url='https://testfoodbank.org')
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'testfoodbank.org'})
        
        assert response.status_code == 200
        assert 'Test FB' in response.content.decode()

    def test_search_finds_foodbank_by_shopping_list_url(self):
        """Test that search finds food banks by shopping list URL."""
        self._create_foodbank(
            name='Shopping URL FB',
            shopping_list_url='https://unique-shopping-site.com/needs'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'unique-shopping-site.com'})
        
        assert response.status_code == 200
        assert 'Shopping URL FB' in response.content.decode()

    def test_search_finds_foodbank_by_donation_points_url(self):
        """Test that search finds food banks by donation points URL."""
        self._create_foodbank(
            name='Donation Points FB',
            donation_points_url='https://donation-points-unique.org/drop-off'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'donation-points-unique.org'})
        
        assert response.status_code == 200
        assert 'Donation Points FB' in response.content.decode()

    def test_search_finds_foodbank_by_locations_url(self):
        """Test that search finds food banks by locations URL."""
        self._create_foodbank(
            name='Locations URL FB',
            locations_url='https://locations-unique-domain.org/find-us'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'locations-unique-domain.org'})
        
        assert response.status_code == 200
        assert 'Locations URL FB' in response.content.decode()

    def test_search_finds_foodbank_by_contacts_url(self):
        """Test that search finds food banks by contacts URL."""
        self._create_foodbank(
            name='Contacts URL FB',
            contacts_url='https://contacts-unique-domain.org/contact'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'contacts-unique-domain.org'})
        
        assert response.status_code == 200
        assert 'Contacts URL FB' in response.content.decode()

    def test_search_finds_foodbank_by_rss_url(self):
        """Test that search finds food banks by RSS URL."""
        self._create_foodbank(
            name='RSS URL FB',
            rss_url='https://rss-unique-domain.org/feed.xml'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'rss-unique-domain.org'})
        
        assert response.status_code == 200
        assert 'RSS URL FB' in response.content.decode()

    def test_search_need_id_displays_truncated(self):
        """Test that need IDs in search results display only first 7 characters."""
        foodbank = self._create_foodbank(name='Need Search FB')
        
        # Create a need for the foodbank
        need = FoodbankChange(
            foodbank=foodbank,
            change_text='unique-search-term-for-need-test',
            published=True
        )
        need.save(do_translate=False, do_foodbank_save=False)
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'unique-search-term-for-need-test'})
        
        content = response.content.decode()
        assert response.status_code == 200
        
        # The full need_id should be in the URL (href)
        full_need_id = str(need.need_id)
        assert full_need_id in content
        
        # The displayed link text should be only the first 7 characters
        truncated_id = full_need_id[:7]
        # Check that the truncated ID appears (as link text)
        assert truncated_id in content
        
        # The 8th character should NOT appear immediately after the 7th character
        # as the link text (except in the href URL)
        # We can verify this by checking the HTML structure
        assert f'>{truncated_id}</a>' in content
