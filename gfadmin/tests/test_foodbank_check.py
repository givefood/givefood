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
        
        # Verify CrawlItems were created
        crawl_items = CrawlItem.objects.filter(foodbank=foodbank, crawl_type='check')
        
        # Should have 3 crawl items: homepage, donation_points HTML (GET), and donation_points POST
        assert crawl_items.count() == 3


@pytest.mark.django_db
class TestFoodbankCheckPrompt:
    """Tests for the foodbank check prompt debug URL."""

    @patch('gfadmin.views.requests.get')
    def test_returns_plain_text(self, mock_get):
        """Test that the prompt endpoint returns plain text."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
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
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_check_prompt
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/prompt/')
        
        # Call the view
        response = foodbank_check_prompt(request, slug=foodbank.slug)
        
        # Verify response content type is plain text
        assert response['Content-Type'] == 'text/plain; charset=utf-8'
        assert response.status_code == 200
        
        # Verify the content contains expected foodbank details
        content = response.content.decode('utf-8')
        assert 'Test Foodbank' in content
        assert 'AB12 3CD' in content

    @patch('gfadmin.views.requests.get')
    def test_prompt_contains_foodbank_json(self, mock_get):
        """Test that the prompt contains the foodbank JSON data."""
        # Create a test foodbank with locations
        foodbank = Foodbank(
            name='Foodbank With Locations',
            url='https://example.com',
            address='456 Main St',
            postcode='CD34 5EF',
            country='Wales',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            phone_number='01234 567890',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Content</body></html>'
        mock_get.return_value = mock_response
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_check_prompt
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/prompt/')
        
        # Call the view
        response = foodbank_check_prompt(request, slug=foodbank.slug)
        
        content = response.content.decode('utf-8')
        # Check that the content includes foodbank details
        # (Note: JSON may be HTML-escaped in the template output)
        assert 'Foodbank With Locations' in content
        assert 'CD34 5EF' in content
        assert 'Wales' in content


@pytest.mark.django_db
class TestFoodbankCheckResult:
    """Tests for the foodbank check result debug URL."""

    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_returns_json(self, mock_get, mock_gemini):
        """Test that the result endpoint returns JSON."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='JSON Test Foodbank',
            url='https://example.com',
            address='789 Json St',
            postcode='EF56 7GH',
            country='Scotland',
            lat_lng='55.9533,-3.1883',
            contact_email='json@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response
        
        # Mock gemini response
        mock_gemini.return_value = {
            'details': {
                'name': 'JSON Test Foodbank',
                'address': '789 Json St',
                'postcode': 'EF56 7GH',
                'country': 'Scotland',
                'phone_number': '',
                'contact_email': 'json@example.com',
                'network': '',
            },
            'locations': [
                {'name': 'Branch A', 'address': '10 Branch A St', 'postcode': 'BR1 1AA'}
            ],
            'donation_points': []
        }
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_check_result
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/result/')
        
        # Call the view
        response = foodbank_check_result(request, slug=foodbank.slug)
        
        # Verify response content type is JSON
        assert response['Content-Type'] == 'application/json'
        assert response.status_code == 200
        
        # Verify the content is valid JSON
        import json
        result = json.loads(response.content.decode('utf-8'))
        assert result['details']['name'] == 'JSON Test Foodbank'
        assert result['details']['postcode'] == 'EF56 7GH'
        assert len(result['locations']) == 1
        assert result['locations'][0]['name'] == 'Branch A'

    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_calls_gemini_with_correct_schema(self, mock_get, mock_gemini):
        """Test that gemini is called with the correct response schema."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='Schema Test Foodbank',
            url='https://example.com',
            address='100 Schema St',
            postcode='GH78 9IJ',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='schema@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response
        
        # Mock gemini response
        mock_gemini.return_value = {
            'details': {
                'name': 'Schema Test Foodbank',
                'address': '100 Schema St',
                'postcode': 'GH78 9IJ',
                'country': 'England',
                'phone_number': '',
                'contact_email': 'schema@example.com',
                'network': '',
            },
            'locations': [],
            'donation_points': []
        }
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_check_result
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/result/')
        
        # Call the view
        response = foodbank_check_result(request, slug=foodbank.slug)
        
        # Verify gemini was called
        assert mock_gemini.called
        
        # Verify the schema includes required fields
        call_kwargs = mock_gemini.call_args[1]
        schema = call_kwargs['response_schema']
        assert 'details' in schema['properties']
        assert 'locations' in schema['properties']
        assert 'donation_points' in schema['properties']


@pytest.mark.django_db
class TestFoodbankCheckDetailChanges:
    """Tests for the detail_changes highlighting feature."""

    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_detail_changes_detects_differences(self, mock_get, mock_gemini, mock_render):
        """Test that detail_changes is populated when fields differ."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            phone_number='01234567890',
            contact_email='test@example.com',
            charity_number='12345',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        # Mock gemini response with DIFFERENT values
        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '456 Different St',  # Different
                'postcode': 'XY99 9ZZ',  # Different
                'country': 'England',
                'phone_number': '09876 543210',  # Different
                'contact_email': 'different@example.com',  # Different
                'network': '',
                'charity_number': '67890',  # Different
            },
            'locations': [],
            'donation_points': []
        }

        # Mock render
        mock_render.return_value = Mock(status_code=200)

        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)

        # Verify render was called with detail_changes
        render_call_args = mock_render.call_args
        context = render_call_args[0][2]  # Third argument is the context dict

        assert 'detail_changes' in context
        detail_changes = context['detail_changes']

        # All fields should be marked as changed
        assert detail_changes['address'] is True
        assert detail_changes['phone_number'] is True
        assert detail_changes['contact_email'] is True
        assert detail_changes['charity_number'] is True

    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_detail_changes_no_differences(self, mock_get, mock_gemini, mock_render):
        """Test that detail_changes is empty when fields match."""
        # Create a test foodbank
        # Note: phone_number gets spaces stripped on save, so use no spaces
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            phone_number='01234567890',  # No spaces - matches saved format
            contact_email='test@example.com',
            charity_number='12345',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        # Mock gemini response with SAME values
        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': '01234567890',  # Must match saved format
                'contact_email': 'test@example.com',
                'network': '',
                'charity_number': '12345',
            },
            'locations': [],
            'donation_points': []
        }

        # Mock render
        mock_render.return_value = Mock(status_code=200)

        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)

        # Verify render was called with detail_changes
        render_call_args = mock_render.call_args
        context = render_call_args[0][2]  # Third argument is the context dict

        assert 'detail_changes' in context
        detail_changes = context['detail_changes']

        # No fields should be marked as changed
        assert detail_changes['address'] is False
        assert detail_changes['phone_number'] is False
        assert detail_changes['contact_email'] is False
        assert detail_changes['charity_number'] is False

    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_phone_number_comparison_ignores_spaces(self, mock_get, mock_gemini, mock_render):
        """Test that phone number comparison ignores spaces."""
        # Create a test foodbank with phone number without spaces
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            phone_number='01234567890',  # No spaces
            contact_email='test@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        # Mock gemini response with phone number WITH spaces (should match)
        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': '01234 567890',  # Same number but with space
                'contact_email': 'test@example.com',
                'network': '',
            },
            'locations': [],
            'donation_points': []
        }

        # Mock render
        mock_render.return_value = Mock(status_code=200)

        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)

        # Verify render was called with detail_changes
        render_call_args = mock_render.call_args
        context = render_call_args[0][2]  # Third argument is the context dict

        assert 'detail_changes' in context
        detail_changes = context['detail_changes']

        # Phone number should NOT be marked as changed (spaces are ignored)
        assert detail_changes['phone_number'] is False

    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_detail_changes_handles_empty_values(self, mock_get, mock_gemini, mock_render):
        """Test that detail_changes handles None and empty string values correctly."""
        # Create a test foodbank with empty fields
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            phone_number='',  # Empty
            contact_email='test@example.com',
            charity_number=None,  # None
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        # Mock gemini response with empty values (matching)
        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': '',  # Empty matches empty
                'contact_email': 'test@example.com',
                'network': '',
                'charity_number': '',  # Empty matches None
            },
            'locations': [],
            'donation_points': []
        }

        # Mock render
        mock_render.return_value = Mock(status_code=200)

        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)

        # Verify render was called with detail_changes
        render_call_args = mock_render.call_args
        context = render_call_args[0][2]  # Third argument is the context dict

        assert 'detail_changes' in context
        detail_changes = context['detail_changes']

        # Empty values should match empty values (no changes)
        assert detail_changes['address'] is False
        assert detail_changes['phone_number'] is False
        assert detail_changes['contact_email'] is False
        assert detail_changes['charity_number'] is False

    @patch('givefood.models.geocode')
    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_location_discrepancy_not_shown_for_delivery_address_postcode(self, mock_get, mock_gemini, mock_render, mock_geocode):
        """Test that locations matching delivery address postcode are not shown as discrepancies."""
        # Mock geocode to prevent API call
        mock_geocode.return_value = '51.5074,-0.1278'
        
        # Create a test foodbank with a delivery address
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            delivery_address='Delivery Warehouse\n456 Delivery Road\nXY99 9ZZ',  # Delivery postcode XY99 9ZZ
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        # Mock gemini response with a location matching delivery address postcode
        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': '',
                'contact_email': 'test@example.com',
                'network': '',
                'charity_number': '',
            },
            'locations': [
                {'name': 'Delivery Warehouse', 'address': '456 Delivery Road', 'postcode': 'XY99 9ZZ'}
            ],
            'donation_points': []
        }

        # Mock render
        mock_render.return_value = Mock(status_code=200)

        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)

        # Verify render was called
        render_call_args = mock_render.call_args
        context = render_call_args[0][2]

        # The location should NOT have discrepancy set because it matches delivery address postcode
        locations = context['check_result']['locations']
        assert len(locations) == 1
        assert 'discrepancy' not in locations[0] or locations[0].get('discrepancy') is not True


    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_detail_changes_detects_new_field_differences(self, mock_get, mock_gemini, mock_render):
        """Test that detail_changes is populated when new fields (facebook, twitter, urls) differ."""
        # Create a test foodbank with all the new fields populated
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            facebook_page='oldfacebook',
            twitter_handle='oldtwitter',
            bankuet_slug='oldbankuet',
            rss_url='https://example.com/old.rss',
            news_url='https://example.com/old-news',
            donation_points_url='https://example.com/old-donate',
            locations_url='https://example.com/old-locations',
            contacts_url='https://example.com/old-contacts',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        # Mock gemini response with DIFFERENT values for new fields
        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': '',
                'contact_email': 'test@example.com',
                'network': '',
                'charity_number': '',
                'facebook_page': 'newfacebook',
                'twitter_handle': 'newtwitter',
                'bankuet_slug': 'newbankuet',
                'rss_url': 'https://example.com/new.rss',
                'news_url': 'https://example.com/new-news',
                'donation_points_url': 'https://example.com/new-donate',
                'locations_url': 'https://example.com/new-locations',
                'contacts_url': 'https://example.com/new-contacts',
            },
            'locations': [],
            'donation_points': []
        }

        # Mock render
        mock_render.return_value = Mock(status_code=200)

        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)

        # Verify render was called with detail_changes
        render_call_args = mock_render.call_args
        context = render_call_args[0][2]

        assert 'detail_changes' in context
        detail_changes = context['detail_changes']

        # All new fields should be marked as changed
        assert detail_changes['facebook_page'] is True
        assert detail_changes['twitter_handle'] is True
        assert detail_changes['bankuet_slug'] is True
        assert detail_changes['rss_url'] is True
        assert detail_changes['news_url'] is True
        assert detail_changes['donation_points_url'] is True
        assert detail_changes['locations_url'] is True
        assert detail_changes['contacts_url'] is True


    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_detail_changes_no_differences_for_new_fields(self, mock_get, mock_gemini, mock_render):
        """Test that detail_changes shows no changes when new fields match."""
        # Create a test foodbank with new fields populated
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            facebook_page='samefacebook',
            twitter_handle='sametwitter',
            bankuet_slug='samebankuet',
            rss_url='https://example.com/same.rss',
            news_url='https://example.com/same-news',
            donation_points_url='https://example.com/same-donate',
            locations_url='https://example.com/same-locations',
            contacts_url='https://example.com/same-contacts',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test</body></html>'
        mock_get.return_value = mock_response

        # Mock gemini response with SAME values
        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': '',
                'contact_email': 'test@example.com',
                'network': '',
                'charity_number': '',
                'facebook_page': 'samefacebook',
                'twitter_handle': 'sametwitter',
                'bankuet_slug': 'samebankuet',
                'rss_url': 'https://example.com/same.rss',
                'news_url': 'https://example.com/same-news',
                'donation_points_url': 'https://example.com/same-donate',
                'locations_url': 'https://example.com/same-locations',
                'contacts_url': 'https://example.com/same-contacts',
            },
            'locations': [],
            'donation_points': []
        }

        # Mock render
        mock_render.return_value = Mock(status_code=200)

        # Make a GET request to the view
        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        # Call the view
        response = foodbank_check(request, slug=foodbank.slug)

        # Verify render was called with detail_changes
        render_call_args = mock_render.call_args
        context = render_call_args[0][2]

        assert 'detail_changes' in context
        detail_changes = context['detail_changes']

        # No new fields should be marked as changed
        assert detail_changes['facebook_page'] is False
        assert detail_changes['twitter_handle'] is False
        assert detail_changes['bankuet_slug'] is False
        assert detail_changes['rss_url'] is False
        assert detail_changes['news_url'] is False
        assert detail_changes['donation_points_url'] is False
        assert detail_changes['locations_url'] is False
        assert detail_changes['contacts_url'] is False


    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_detail_changes_handles_nullish_bankuet(self, mock_get, mock_gemini, mock_render):
        """Bankuet null/None textual values should be treated as empty."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            bankuet_slug='',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        mock_response = Mock(status_code=200, text='<html></html>')
        mock_get.return_value = mock_response

        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': '',
                'contact_email': '',
                'network': '',
                'charity_number': '',
                'facebook_page': '',
                'twitter_handle': '',
                'bankuet_slug': 'None',
                'rss_url': '',
                'news_url': '',
                'donation_points_url': '',
                'locations_url': '',
                'contacts_url': '',
            },
            'locations': [],
            'donation_points': []
        }

        mock_render.return_value = Mock(status_code=200)

        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        response = foodbank_check(request, slug=foodbank.slug)

        context = mock_render.call_args[0][2]
        detail_changes = context['detail_changes']

        # Treated as empty, so no change flagged and rendered value is empty string
        assert detail_changes['bankuet_slug'] is False
        assert context['check_result']['details']['bankuet_slug'] == ''


    @patch('gfadmin.views.render')
    @patch('gfadmin.views.gemini')
    @patch('gfadmin.views.requests.get')
    def test_detail_changes_normalises_all_nullish_fields(self, mock_get, mock_gemini, mock_render):
        """All detail fields should normalise textual nulls to empty strings."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        mock_response = Mock(status_code=200, text='<html></html>')
        mock_get.return_value = mock_response

        mock_gemini.return_value = {
            'details': {
                'name': 'Test Foodbank',
                'address': '123 Test St',
                'postcode': 'AB12 3CD',
                'country': 'England',
                'phone_number': 'none',
                'contact_email': 'Null',
                'network': 'nothing',
                'charity_number': 'null',
                'facebook_page': 'none',
                'twitter_handle': 'none',
                'bankuet_slug': 'NONE',
                'rss_url': 'nothing',
                'news_url': 'none',
                'donation_points_url': 'null',
                'locations_url': 'None',
                'contacts_url': 'null',
            },
            'locations': [],
            'donation_points': []
        }

        mock_render.return_value = Mock(status_code=200)

        from gfadmin.views import foodbank_check
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/check/')

        response = foodbank_check(request, slug=foodbank.slug)

        context = mock_render.call_args[0][2]
        details = context['check_result']['details']
        detail_changes = context['detail_changes']

        # All nullish strings should be empty
        for key in mock_gemini.return_value['details'].keys():
            if key not in ('name', 'address', 'postcode', 'country'):
                assert details[key] == ''
                # Since ours are also empty, no change flagged
                assert detail_changes[key] is False
