"""Tests for icons in foodbank admin page tabs."""
import pytest
from django.test import Client
from django.urls import reverse

from givefood.models import Foodbank


@pytest.mark.django_db
class TestFoodbankTabIcons:
    """Test that icons are displayed on foodbank admin page tabs."""

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

    def test_general_locations_tab_has_bank_icon(self):
        """Test that General & Locations tab has bank icon."""
        foodbank = self._create_foodbank()
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify bank icon is present in General & Locations tab
        assert 'mdi mdi-bank' in content
        assert '<span class="icon"><i class="mdi mdi-bank"></i></span>' in content

    def test_needs_orders_tab_has_shopping_icon(self):
        """Test that Needs & Orders tab has shopping icon."""
        foodbank = self._create_foodbank()
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify shopping icon is present in Needs & Orders tab
        assert 'mdi mdi-shopping' in content
        assert '<span class="icon"><i class="mdi mdi-shopping"></i></span>' in content

    def test_donation_points_tab_has_store_icon(self):
        """Test that Donation Points tab has store icon."""
        foodbank = self._create_foodbank()
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify store icon is present in Donation Points tab
        assert 'mdi mdi-store' in content
        assert '<span class="icon"><i class="mdi mdi-store"></i></span>' in content

    def test_subscribers_tab_has_bell_icon(self):
        """Test that Subscribers tab has bell icon."""
        foodbank = self._create_foodbank()
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify bell icon is present in Subscribers tab
        assert 'mdi mdi-bell' in content
        assert '<span class="icon"><i class="mdi mdi-bell"></i></span>' in content

    def test_crawls_tab_has_robot_icon(self):
        """Test that Crawls tab has robot icon."""
        foodbank = self._create_foodbank()
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify robot icon is present in Crawls tab
        assert 'mdi mdi-robot' in content
        assert '<span class="icon"><i class="mdi mdi-robot"></i></span>' in content

    def test_all_six_icons_present(self):
        """Test that all six icons are present in the tabs."""
        foodbank = self._create_foodbank()
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify all icons are present
        expected_icons = [
            'mdi-bank',
            'mdi-shopping',
            'mdi-store',
            'mdi-bell',
            'mdi-robot',
        ]
        
        for icon in expected_icons:
            assert icon in content, f"Icon {icon} not found in page content"
