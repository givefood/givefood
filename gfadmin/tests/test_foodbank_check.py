"""Tests for the foodbank check functionality."""
import pytest
from unittest.mock import patch, Mock, call
from datetime import datetime
from django.test import RequestFactory

from givefood.models import Foodbank, CrawlItem


@pytest.mark.django_db
class TestFoodbankCheck:
    """Test the foodbank check functionality."""

    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    @patch('gfadmin.views.requests.post')
    def test_crawlitems_created_for_each_url(self, mock_post, mock_get, mock_gemini, mock_render):
        """Test that CrawlItems with crawl_type='check' are created for each URL fetched."""
        # Create a test foodbank with all URL fields populated
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            locations_url='https://example.com/locations',
            contacts_url='https://example.com/contacts',
            donation_points_url='https://example.com/donate',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Mock the HTTP responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test content</body></html>'
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        # Mock gemini response
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
        
        # Mock render to prevent template rendering
        mock_render.return_value = Mock(status_code=200)
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')
        
        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)
        
        # Verify CrawlItems were created
        crawl_items = CrawlItem.objects.filter(foodbank=foodbank, crawl_type='check')
        
        # Should have created 5 crawl items (homepage, shopping list, locations, contacts, donation points)
        assert crawl_items.count() == 5
        
        # Verify each crawl item
        urls_checked = list(crawl_items.values_list('url', flat=True))
        assert foodbank.url in urls_checked
        assert foodbank.shopping_list_url in urls_checked
        assert foodbank.locations_url in urls_checked
        assert foodbank.contacts_url in urls_checked
        assert foodbank.donation_points_url in urls_checked
        
        # Verify all have crawl_type='check'
        for item in crawl_items:
            assert item.crawl_type == 'check'
            assert item.foodbank == foodbank
            assert item.finish is not None  # Should have a finish time
            
    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_crawlitems_created_for_minimal_urls(self, mock_get, mock_gemini, mock_render):
        """Test that CrawlItems are created even when only required URLs are present."""
        # Create a test foodbank with only required URL fields
        foodbank = Foodbank(
            name='Minimal Foodbank',
            url='https://minimal.com',
            shopping_list_url='https://minimal.com/needs',
            address='456 Minimal St',
            postcode='CD34 5EF',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='minimal@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Minimal content</body></html>'
        mock_get.return_value = mock_response
        
        # Mock gemini response
        mock_gemini.return_value = {
            'details': {
                'name': 'Minimal Foodbank',
                'address': '456 Minimal St',
                'postcode': 'CD34 5EF',
                'country': 'England',
                'phone_number': '',
                'contact_email': 'minimal@example.com',
                'network': '',
            },
            'locations': [],
            'donation_points': []
        }
        
        # Mock render to prevent template rendering
        mock_render.return_value = Mock(status_code=200)
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')
        
        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)
        
        # Verify CrawlItems were created
        crawl_items = CrawlItem.objects.filter(foodbank=foodbank, crawl_type='check')
        
        # Should have created 2 crawl items (homepage and shopping list)
        assert crawl_items.count() == 2
        
        # Verify each crawl item
        urls_checked = list(crawl_items.values_list('url', flat=True))
        assert foodbank.url in urls_checked
        assert foodbank.shopping_list_url in urls_checked
        
        # Verify all have crawl_type='check' and finish time
        for item in crawl_items:
            assert item.crawl_type == 'check'
            assert item.foodbank == foodbank
            assert item.finish is not None

    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_crawlitem_has_finish_time(self, mock_get, mock_gemini, mock_render):
        """Test that CrawlItems have a finish time set after the request completes."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='Time Test Foodbank',
            url='https://timetest.com',
            shopping_list_url='https://timetest.com/needs',
            address='789 Time St',
            postcode='EF56 7GH',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='time@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Time test</body></html>'
        mock_get.return_value = mock_response
        
        # Mock gemini response
        mock_gemini.return_value = {
            'details': {
                'name': 'Time Test Foodbank',
                'address': '789 Time St',
                'postcode': 'EF56 7GH',
                'country': 'England',
                'phone_number': '',
                'contact_email': 'time@example.com',
                'network': '',
            },
            'locations': [],
            'donation_points': []
        }
        
        # Mock render to prevent template rendering
        mock_render.return_value = Mock(status_code=200)
        
        # Record time before the request
        start_time = datetime.now()
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')
        
        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)
        
        # Record time after the request
        end_time = datetime.now()
        
        # Verify CrawlItems were created with finish times
        crawl_items = CrawlItem.objects.filter(foodbank=foodbank, crawl_type='check')
        
        for item in crawl_items:
            # Verify finish time exists and is between start and end
            assert item.finish is not None
            # The finish time should be after the item was started
            assert item.finish >= item.start
            # The finish time should be within the reasonable time window
            # (comparing without timezone info for simplicity)
            assert item.start.replace(tzinfo=None) >= start_time.replace(tzinfo=None, microsecond=0)
            assert item.finish.replace(tzinfo=None) <= end_time.replace(tzinfo=None) + datetime.resolution
