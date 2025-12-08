"""Tests for the admin index view."""
import pytest
from django.utils import timezone
from datetime import datetime, timedelta

from givefood.models import CrawlSet, Foodbank


@pytest.mark.django_db
class TestLatestNeedCrawlset:
    """Test the latest need crawlset logic."""

    def _get_latest_need_crawlset_view_logic(self):
        """Helper method that mimics the view's query logic for consistency."""
        try:
            return CrawlSet.objects.filter(crawl_type="need").order_by("-start")[:1][0]
        except IndexError:
            return None

    def test_latest_need_crawlset_returns_none_when_empty(self):
        """Test that the query returns None when no crawlsets exist."""
        # Ensure no need crawlsets exist
        CrawlSet.objects.filter(crawl_type='need').delete()
        
        # Simulate the view logic
        latest = self._get_latest_need_crawlset_view_logic()
        
        # Should return None
        assert latest is None

    def test_latest_need_crawlset_returns_crawlset_when_exists(self):
        """Test that the query returns a crawlset when one exists."""
        now = timezone.now()
        crawlset = CrawlSet.objects.create(
            crawl_type='need',
            start=now,
            finish=now
        )
        
        # Simulate the view logic
        latest = self._get_latest_need_crawlset_view_logic()
        
        # Should return the crawlset
        assert latest is not None
        assert latest.id == crawlset.id

    def test_latest_need_crawlset_returns_most_recent(self):
        """Test that the most recent need crawlset is returned."""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Create older crawlset
        CrawlSet.objects.create(
            crawl_type='need',
            start=yesterday,
            finish=yesterday
        )
        
        # Create newer crawlset
        newer_crawlset = CrawlSet.objects.create(
            crawl_type='need',
            start=now,
            finish=now
        )
        
        # Get the latest one (simulating the view logic)
        latest = self._get_latest_need_crawlset_view_logic()
        
        # Should return the newer one
        assert latest is not None
        assert latest.id == newer_crawlset.id
        # Check the start time is close (within 1 second)
        assert abs((latest.start - now).total_seconds()) < 1

    def test_latest_need_crawlset_ignores_other_types(self):
        """Test that only 'need' type crawlsets are considered."""
        now = timezone.now()
        
        # Create article crawlset (should be ignored)
        CrawlSet.objects.create(
            crawl_type='article',
            start=now,
            finish=now
        )
        
        # Create need crawlset (should be returned)
        need_crawlset = CrawlSet.objects.create(
            crawl_type='need',
            start=now - timedelta(hours=1),  # slightly older but still a need type
            finish=now - timedelta(hours=1)
        )
        
        # Get the latest need crawlset
        latest = self._get_latest_need_crawlset_view_logic()
        
        # Should return the need crawlset, not the article one
        assert latest is not None
        assert latest.id == need_crawlset.id
        assert latest.crawl_type == 'need'


@pytest.mark.django_db
class TestOldestEditDays:
    """Test the oldest edit days calculation."""

    def test_oldest_edit_days_calculation(self):
        """Test that oldest_edit_days is correctly calculated."""
        # Create a food bank with an edit date 100 days ago
        old_date = datetime.now() - timedelta(days=100)
        
        # Create the foodbank without triggering geo updates
        foodbank = Foodbank(
            name='Test Food Bank',
            slug='test-food-bank',
            address='123 Test St',
            postcode='TE1 1ST',
            lat_lng='51.5074,-0.1278',  # London coordinates
            country='England',
            edited=old_date,
            is_closed=False
        )
        # Set required fields manually to avoid external API calls
        foodbank.latitude = 51.5074
        foodbank.longitude = -0.1278
        foodbank.save(do_geoupdate=False)
        
        # The days calculation should be approximately 100
        # (we allow a small margin since datetime.now() might be slightly different)
        days_since = (datetime.now() - foodbank.edited).days
        assert days_since >= 99
        assert days_since <= 101

