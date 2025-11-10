"""Tests for the foodbank URLs edit form."""
import pytest
from unittest.mock import patch, Mock
from django.urls import reverse
from django.test import RequestFactory

from givefood.forms import FoodbankUrlsForm
from givefood.models import Foodbank, CrawlItem


@pytest.mark.django_db
class TestFoodbankUrlsForm:
    """Test the foodbank URLs edit functionality."""

    def test_foodbank_urls_form_url_resolves(self):
        """Test that the URL pattern resolves correctly."""
        url = reverse('admin:foodbank_urls_edit', kwargs={'slug': 'test-foodbank'})
        assert url == '/admin/foodbank/test-foodbank/edit/urls/'

    def test_foodbank_urls_form_has_correct_fields(self):
        """Test that the form has only the URL fields."""
        form = FoodbankUrlsForm()
        expected_fields = ['url', 'shopping_list_url', 'rss_url', 'donation_points_url', 'locations_url', 'contacts_url']
        assert list(form.fields.keys()) == expected_fields

    def test_foodbank_urls_form_inherits_from_model_form(self):
        """Test that FoodbankUrlsForm uses the Foodbank model."""
        form = FoodbankUrlsForm()
        from givefood.models import Foodbank
        assert form._meta.model == Foodbank
    
    @patch('gfadmin.views.render')
    @patch('gfadmin.views.requests.get')
    @patch('gfadmin.views.gemini')
    def test_crawlitem_created_when_fetching_urls(self, mock_gemini, mock_requests_get, mock_render):
        """Test that a CrawlItem with crawl_type='urls' is created when fetching URLs."""
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
        
        # Mock the HTTP request
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><a href="/shopping-list">Shopping List</a></body></html>'
        mock_requests_get.return_value = mock_response
        
        # Mock gemini response
        mock_gemini.return_value = {
            'shopping_list_url': '',
            'rss_url': '',
            'donation_points_url': '',
            'locations_url': '',
            'contacts_url': ''
        }
        
        # Mock render to prevent template rendering
        mock_render.return_value = Mock(status_code=200)
        
        # Make a GET request to the view
        from gfadmin.views import foodbank_urls_form
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/edit/urls/')
        
        # Call the view
        response = foodbank_urls_form(request, slug=foodbank.slug)
        
        # Verify a CrawlItem was created
        crawl_items = CrawlItem.objects.filter(foodbank=foodbank, crawl_type='urls')
        assert crawl_items.count() == 1
        
        crawl_item = crawl_items.first()
        assert crawl_item.crawl_type == 'urls'
        assert crawl_item.url == foodbank.url
        assert crawl_item.foodbank == foodbank
