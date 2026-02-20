"""Tests for the crawl_set_json view."""
import json
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from givefood.models import CrawlSet, CrawlItem, Foodbank


@pytest.mark.django_db
class TestCrawlSetJsonView:
    """Test the crawl_set_json view."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def setup_method(self):
        """Set up test data."""
        self.foodbank = Foodbank(
            name='Test Food Bank',
            slug='test-food-bank',
            address='123 Test St',
            postcode='TE1 1ST',
            lat_lng='51.5074,-0.1278',
            country='England',
            latitude=51.5074,
            longitude=-0.1278,
        )
        self.foodbank.save(do_geoupdate=False, do_decache=False)

    def _get_authenticated_client(self):
        """Helper to get an authenticated client for testing admin views."""
        client = Client()
        self._setup_authenticated_session(client)
        return client

    def test_crawl_set_json_returns_json(self):
        """Test that the JSON endpoint returns valid JSON."""
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_set_json', args=[crawl_set.id]))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        data = json.loads(response.content)
        assert data['crawl_type'] == 'need'

    def test_crawl_set_json_contains_expected_fields(self):
        """Test that the JSON response contains expected fields."""
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_set_json', args=[crawl_set.id]))
        data = json.loads(response.content)
        assert 'crawl_type' in data
        assert 'start' in data
        assert 'finish' in data
        assert 'item_count' in data
        assert 'object_count' in data
        assert 'items' in data

    def test_crawl_set_json_unfinished(self):
        """Test that unfinished crawl sets have null finish."""
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_set_json', args=[crawl_set.id]))
        data = json.loads(response.content)
        assert data['finish'] is None
        assert data['time_taken'] is None

    def test_crawl_set_json_finished(self):
        """Test that finished crawl sets have finish time."""
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        crawl_set.finish = timezone.now()
        crawl_set.save()
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_set_json', args=[crawl_set.id]))
        data = json.loads(response.content)
        assert data['finish'] is not None
        assert data['time_taken'] is not None

    def test_crawl_set_json_with_items(self):
        """Test that crawl items are included."""
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        CrawlItem.objects.create(
            crawl_set=crawl_set,
            crawl_type='need',
            foodbank=self.foodbank,
            url='https://example.com',
        )
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_set_json', args=[crawl_set.id]))
        data = json.loads(response.content)
        assert data['item_count'] == 1
        assert len(data['items']) == 1
        assert data['items'][0]['foodbank_name'] == 'Test Food Bank'
        assert data['items'][0]['foodbank_slug'] == 'test-food-bank'
        assert data['items'][0]['url'] == 'https://example.com'

    def test_crawl_set_json_404_for_nonexistent(self):
        """Test that a 404 is returned for non-existent crawl set."""
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_set_json', args=[99999]))
        assert response.status_code == 404
