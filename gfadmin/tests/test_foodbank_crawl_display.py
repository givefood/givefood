"""Tests for the foodbank crawl display on the admin page."""
import pytest
from unittest.mock import patch

from givefood.models import Foodbank, CrawlItem, CrawlSet


@pytest.mark.django_db
class TestFoodbankCrawlDisplay:
    """Test the crawl display on the foodbank admin page."""

    @patch('gfadmin.views.render')
    def test_crawl_items_passed_to_template(self, mock_render):
        """Test that crawl items are properly passed to the template."""
        from gfadmin.views import foodbank as foodbank_view
        from django.test import RequestFactory
        
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
        
        # Create a crawl set
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        
        # Create a crawl item with a crawl_set
        crawl_item = CrawlItem.objects.create(
            foodbank=foodbank,
            crawl_type='need',
            crawl_set=crawl_set,
            url='https://example.com/shopping'
        )
        
        # Create an orphaned crawl item (no crawl_set)
        orphan_crawl_item = CrawlItem.objects.create(
            foodbank=foodbank,
            crawl_type='check',
            crawl_set=None,
            url='https://example.com/check'
        )
        
        # Mock render to prevent template rendering
        mock_render.return_value = None
        
        # Make a request to the view
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank.slug}/')
        
        # Call the view
        foodbank_view(request, slug=foodbank.slug)
        
        # Verify render was called
        assert mock_render.called
        
        # Get the template context
        render_args = mock_render.call_args
        template_vars = render_args[0][2]  # Third argument is the context
        
        # Verify foodbank is in context
        assert 'foodbank' in template_vars
        assert template_vars['foodbank'] == foodbank
        
        # Verify crawl items can be accessed from the foodbank
        crawl_items = template_vars['foodbank'].crawl_items()
        assert len(crawl_items) == 2

    def test_crawl_item_icon_method_consistency(self):
        """Test that CrawlItem.crawl_type_icon() returns same icons as CrawlSet.crawl_type_icon()."""
        # Create test instances
        crawl_set_need = CrawlSet(crawl_type='need')
        crawl_item_need = CrawlItem(crawl_type='need')
        
        crawl_set_article = CrawlSet(crawl_type='article')
        crawl_item_article = CrawlItem(crawl_type='article')
        
        crawl_set_charity = CrawlSet(crawl_type='charity')
        crawl_item_charity = CrawlItem(crawl_type='charity')
        
        crawl_set_discrepancy = CrawlSet(crawl_type='discrepancy')
        crawl_item_discrepancy = CrawlItem(crawl_type='discrepancy')
        
        crawl_set_check = CrawlSet(crawl_type='check')
        crawl_item_check = CrawlItem(crawl_type='check')
        
        crawl_set_urls = CrawlSet(crawl_type='urls')
        crawl_item_urls = CrawlItem(crawl_type='urls')
        
        # Verify icons match
        assert crawl_set_need.crawl_type_icon() == crawl_item_need.crawl_type_icon()
        assert crawl_set_article.crawl_type_icon() == crawl_item_article.crawl_type_icon()
        assert crawl_set_charity.crawl_type_icon() == crawl_item_charity.crawl_type_icon()
        assert crawl_set_discrepancy.crawl_type_icon() == crawl_item_discrepancy.crawl_type_icon()
        assert crawl_set_check.crawl_type_icon() == crawl_item_check.crawl_type_icon()
        assert crawl_set_urls.crawl_type_icon() == crawl_item_urls.crawl_type_icon()
