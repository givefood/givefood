"""Tests for the crawl_sets view."""
import pytest
from django.urls import reverse
from django.utils import timezone

from givefood.models import CrawlSet, CrawlItem, Foodbank


@pytest.mark.django_db
class TestCrawlSetsView:
    """Test the crawl_sets view with filters."""

    def setup_method(self):
        """Set up test data."""
        # Create a test foodbank
        self.foodbank = Foodbank.objects.create(
            name='Test Food Bank',
            slug='test-food-bank',
            address='123 Test St',
            postcode='TE1 1ST',
            lat_lng='51.5074,-0.1278',
            country='England',
            latitude=51.5074,
            longitude=-0.1278,
        )

    def test_crawl_sets_page_accessible(self, client):
        """Test that the crawl sets page is accessible."""
        response = client.get(reverse('gfadmin:crawl_sets'))
        assert response.status_code == 200

    def test_adhoc_type_filter_parameter(self, client):
        """Test that adhoc_type filter parameter works."""
        # Create orphaned crawl items with different types
        CrawlItem.objects.create(
            crawl_type='need',
            foodbank=self.foodbank,
            crawl_set=None
        )
        CrawlItem.objects.create(
            crawl_type='article',
            foodbank=self.foodbank,
            crawl_set=None
        )
        
        # Test with adhoc_type filter for 'need'
        response = client.get(reverse('gfadmin:crawl_sets') + '?adhoc_type=need')
        assert response.status_code == 200
        assert 'adhoc_type_filter' in response.context
        assert response.context['adhoc_type_filter'] == 'need'

    def test_adhoc_filter_filters_orphaned_items(self, client):
        """Test that adhoc filter correctly filters orphaned crawl items."""
        # Create orphaned crawl items with different types
        need_item = CrawlItem.objects.create(
            crawl_type='need',
            foodbank=self.foodbank,
            crawl_set=None
        )
        article_item = CrawlItem.objects.create(
            crawl_type='article',
            foodbank=self.foodbank,
            crawl_set=None
        )
        
        # Test filtering by 'need'
        response = client.get(reverse('gfadmin:crawl_sets') + '?adhoc_type=need')
        orphaned_items = list(response.context['orphaned_crawl_items'])
        assert len(orphaned_items) == 1
        assert orphaned_items[0].crawl_type == 'need'
        
        # Test filtering by 'article'
        response = client.get(reverse('gfadmin:crawl_sets') + '?adhoc_type=article')
        orphaned_items = list(response.context['orphaned_crawl_items'])
        assert len(orphaned_items) == 1
        assert orphaned_items[0].crawl_type == 'article'

    def test_adhoc_filter_independent_from_crawlset_filter(self, client):
        """Test that adhoc filter is independent from crawlset filter."""
        # Create a crawl set
        crawl_set = CrawlSet.objects.create(
            crawl_type='need'
        )
        
        # Create orphaned crawl items with different types
        CrawlItem.objects.create(
            crawl_type='need',
            foodbank=self.foodbank,
            crawl_set=None
        )
        CrawlItem.objects.create(
            crawl_type='article',
            foodbank=self.foodbank,
            crawl_set=None
        )
        
        # Test with both filters
        response = client.get(
            reverse('gfadmin:crawl_sets') + 
            '?type=need&adhoc_type=article'
        )
        assert response.status_code == 200
        assert response.context['crawl_type_filter'] == 'need'
        assert response.context['adhoc_type_filter'] == 'article'
        
        # Check that orphaned items are filtered by adhoc_type
        orphaned_items = list(response.context['orphaned_crawl_items'])
        assert len(orphaned_items) == 1
        assert orphaned_items[0].crawl_type == 'article'

    def test_invalid_adhoc_type_returns_forbidden(self, client):
        """Test that invalid adhoc_type returns forbidden response."""
        response = client.get(
            reverse('gfadmin:crawl_sets') + '?adhoc_type=invalid_type'
        )
        assert response.status_code == 403

    def test_empty_adhoc_filter_shows_all_orphaned_items(self, client):
        """Test that empty adhoc filter shows all orphaned items."""
        # Create orphaned crawl items with different types
        CrawlItem.objects.create(
            crawl_type='need',
            foodbank=self.foodbank,
            crawl_set=None
        )
        CrawlItem.objects.create(
            crawl_type='article',
            foodbank=self.foodbank,
            crawl_set=None
        )
        
        # Test without adhoc_type filter
        response = client.get(reverse('gfadmin:crawl_sets'))
        orphaned_items = list(response.context['orphaned_crawl_items'])
        assert len(orphaned_items) == 2
