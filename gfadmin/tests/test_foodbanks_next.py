"""Tests for the foodbanks next functionality."""
import pytest
from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from givefood.models import Foodbank


@pytest.mark.django_db
class TestFoodbanksNext:
    """Test the foodbanks next functionality."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def test_next_redirects_to_oldest_edited_foodbank(self):
        """Test that the next endpoint redirects to the foodbank with the oldest edited date."""
        # Create multiple foodbanks with different edited timestamps
        now = timezone.now()
        
        foodbank1 = Foodbank(
            name='Newest Foodbank',
            url='https://newest.com',
            shopping_list_url='https://newest.com/shopping',
            address='123 New St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='newest@example.com',
        )
        foodbank1.save(do_geoupdate=False, do_decache=False)
        Foodbank.objects.filter(slug=foodbank1.slug).update(edited=now - timedelta(days=1))
        
        foodbank2 = Foodbank(
            name='Oldest Foodbank',
            url='https://oldest.com',
            shopping_list_url='https://oldest.com/shopping',
            address='456 Old St',
            postcode='CD34 5EF',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='oldest@example.com',
        )
        foodbank2.save(do_geoupdate=False, do_decache=False)
        Foodbank.objects.filter(slug=foodbank2.slug).update(edited=now - timedelta(days=30))
        
        foodbank3 = Foodbank(
            name='Middle Foodbank',
            url='https://middle.com',
            shopping_list_url='https://middle.com/shopping',
            address='789 Mid St',
            postcode='EF56 7GH',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='middle@example.com',
        )
        foodbank3.save(do_geoupdate=False, do_decache=False)
        Foodbank.objects.filter(slug=foodbank3.slug).update(edited=now - timedelta(days=15))
        
        # Create a client with authenticated session and call the next endpoint
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbanks_next'))
        
        # Check that we're redirected to the oldest foodbank
        assert response.status_code == 302
        assert response.url == reverse('admin:foodbank', kwargs={'slug': foodbank2.slug})

    def test_next_excludes_closed_foodbanks(self):
        """Test that the next endpoint excludes closed foodbanks."""
        now = timezone.now()
        
        # Create an older foodbank that is closed
        closed_foodbank = Foodbank(
            name='Closed Foodbank',
            url='https://closed.com',
            shopping_list_url='https://closed.com/shopping',
            address='123 Closed St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='closed@example.com',
            is_closed=True,
        )
        closed_foodbank.save(do_geoupdate=False, do_decache=False)
        Foodbank.objects.filter(slug=closed_foodbank.slug).update(edited=now - timedelta(days=60))
        
        # Create a newer foodbank that is open
        open_foodbank = Foodbank(
            name='Open Foodbank',
            url='https://open.com',
            shopping_list_url='https://open.com/shopping',
            address='456 Open St',
            postcode='CD34 5EF',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='open@example.com',
            is_closed=False,
        )
        open_foodbank.save(do_geoupdate=False, do_decache=False)
        Foodbank.objects.filter(slug=open_foodbank.slug).update(edited=now - timedelta(days=30))
        
        # Create a client with authenticated session and call the next endpoint
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbanks_next'))
        
        # Check that we're redirected to the open foodbank, not the older closed one
        assert response.status_code == 302
        assert response.url == reverse('admin:foodbank', kwargs={'slug': open_foodbank.slug})

    def test_next_button_appears_on_check_page(self):
        """Test that the Next button appears on the check page below the Touch button."""
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
        
        # Mock the check view to avoid making HTTP requests
        from unittest.mock import patch, Mock
        
        with patch('gfadmin.views.render') as mock_render, \
             patch('gfadmin.views.gemini') as mock_gemini, \
             patch('gfadmin.views.requests.get') as mock_get:
            
            # Setup mocks
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '<html><body>Test content</body></html>'
            mock_get.return_value = mock_response
            
            mock_gemini.return_value = {
                'details': {
                    'name': 'Test Foodbank',
                    'address': '123 Test St',
                    'postcode': 'AB12 3CD',
                    'country': 'England',
                    'phone_number': '',
                    'contact_email': 'test@example.com',
                    'network': '',
                },
                'locations': [],
                'donation_points': []
            }
            
            # Create the actual response
            from django.shortcuts import render as django_render
            def render_side_effect(request, template, context):
                return django_render(request, template, context)
            
            mock_render.side_effect = render_side_effect
            
            # Create a client with authenticated session
            client = Client()
            self._setup_authenticated_session(client)
            response = client.get(reverse('admin:foodbank_check', kwargs={'slug': foodbank.slug}))
            
            # Check response is successful
            assert response.status_code == 200
            
            # Check that the Next button is in the response
            content = response.content.decode()
            assert 'Next</a>' in content
            assert f'/admin/foodbanks/next/' in content
            
            # Check that the Touch button also appears (Next should be below it)
            assert 'Touch</button>' in content
            
            # Verify the Next button appears after the Touch button in the HTML
            touch_pos = content.find('Touch</button>')
            next_pos = content.find('Next</a>')
            assert touch_pos > 0
            assert next_pos > 0
            assert next_pos > touch_pos

    def test_next_redirects_to_foodbanks_if_no_foodbanks_exist(self):
        """Test that the next endpoint redirects to foodbanks list if no open foodbanks exist."""
        # Make sure there are no foodbanks in the database
        Foodbank.objects.all().delete()
        
        # Create a client with authenticated session and call the next endpoint
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbanks_next'))
        
        # Check that we're redirected to the foodbanks list
        assert response.status_code == 302
        assert response.url == reverse('admin:foodbanks')
