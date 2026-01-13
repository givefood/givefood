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

    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_duplicate_urls_only_downloaded_once(self, mock_get, mock_gemini, mock_render):
        """Test that when multiple fields point to the same URL, it's only downloaded once."""
        # Create a test foodbank where multiple URL fields point to the same URL
        same_url = 'https://same.com/page'
        foodbank = Foodbank(
            name='Duplicate URL Foodbank',
            url=same_url,
            shopping_list_url=same_url,  # Same as url
            locations_url=same_url,  # Same as url
            contacts_url='https://different.com/contact',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test content</body></html>'
        mock_get.return_value = mock_response
        
        # Mock gemini response
        mock_gemini.return_value = {
            'details': {
                'name': 'Duplicate URL Foodbank',
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
        
        # Should have created only 2 crawl items (one for the same_url, one for contacts_url)
        # even though url, shopping_list_url, and locations_url all point to the same URL
        assert crawl_items.count() == 2
        
        # Verify the URLs
        urls_checked = list(crawl_items.values_list('url', flat=True))
        assert same_url in urls_checked
        assert 'https://different.com/contact' in urls_checked
        
        # Verify requests.get was only called twice (once for same_url, once for contacts_url)
        assert mock_get.call_count == 2
        
        # Verify all have crawl_type='check' and finish time
        for item in crawl_items:
            assert item.crawl_type == 'check'
            assert item.foodbank == foodbank
            assert item.finish is not None

    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    @patch('gfadmin.views.requests.post')
    def test_foodbank_org_uk_donate_food_url_fetches_both_html_and_post(self, mock_post, mock_get, mock_gemini, mock_render):
        """Test that donation points URLs with foodbank.org.uk/support-us/donate-food fetch both regular HTML and POST response."""
        # Create a test foodbank with a foodbank.org.uk donation points URL
        foodbank = Foodbank(
            name='Trussell Trust Foodbank',
            url='https://testfoodbank.foodbank.org.uk',
            donation_points_url='https://testfoodbank.foodbank.org.uk/support-us/donate-food',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network_id='test-network-id-12345678',  # Pre-set network_id to avoid additional lookups
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Mock the HTTP GET response (for homepage and regular donation points HTML)
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = '<html><body><h1>Test Foodbank</h1><p>Donation points listed in HTML: Supermarket A, Supermarket B</p></body></html>'
        mock_get.return_value = mock_get_response
        
        # Mock the HTTP POST response (for donation points API response)
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.text = '{"donation_points": [{"name": "Supermarket C"}]}'
        mock_post.return_value = mock_post_response
        
        # Mock gemini response
        mock_gemini.return_value = {
            'details': {
                'name': 'Trussell Trust Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': '',
                'contact_email': 'test@example.com',
                'network': 'Trussell Trust',
            },
            'locations': [],
            'donation_points': []
        }
        
        # Mock render and capture the context passed to it
        mock_render.return_value = Mock(status_code=200)
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')
        
        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)
        
        # Verify that both GET (for HTML) and POST (for API) were called for donation points
        # GET should be called for: homepage + donation_points_url (regular HTML)
        assert mock_get.call_count == 2
        
        # POST should be called once for the donation points API
        assert mock_post.call_count == 1
        
        # Verify the prompt context was passed with both donation_points and donation_points_html
        render_call_args = mock_render.call_args
        context = render_call_args[0][2]  # Third argument is the context dict
        
        # The prompt is rendered by render_to_string, so we need to check that gemini was called
        # with the prompt that includes both donation_points and donation_points_html
        gemini_call_args = mock_gemini.call_args
        prompt = gemini_call_args[0][0]  # First argument is the prompt
        
        # The prompt should contain both donation_points (POST response) and donation_points_html
        assert 'donation_points' in prompt
        assert 'donation_points_html' in prompt
        
        # Verify the actual POST response content is in the prompt (not just the key name)
        assert 'Supermarket C' in prompt, \
            "POST response content should be included in the prompt"
        
        # Verify the HTML body text content is in the prompt
        assert 'Supermarket A' in prompt, \
            "HTML body text content should be included in the prompt"
        
        # Verify prompt content is NOT HTML-escaped (important for AI parsing)
        assert '&quot;' not in prompt, \
            "Prompt content should not be HTML-escaped"
        
        # Verify CrawlItems were created
        crawl_items = CrawlItem.objects.filter(foodbank=foodbank, crawl_type='check')
        
        # Should have 3 crawl items: homepage, donation_points HTML (GET), and donation_points POST
        assert crawl_items.count() == 3
