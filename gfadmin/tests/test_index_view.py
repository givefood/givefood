"""Tests for the admin index view."""
import pytest
from django.utils import timezone
from datetime import timedelta

from givefood.models import CrawlSet


@pytest.mark.django_db
class TestLatestNeedCrawlset:
    """Test the latest need crawlset logic."""

    def test_latest_need_crawlset_returns_none_when_empty(self):
        """Test that the query returns None when no crawlsets exist."""
        # Ensure no need crawlsets exist
        CrawlSet.objects.filter(crawl_type='need').delete()
        
        # Simulate the view logic
        try:
            latest = CrawlSet.objects.filter(crawl_type="need").order_by("-start")[:1][0]
        except IndexError:
            latest = None
        
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
        try:
            latest = CrawlSet.objects.filter(crawl_type="need").order_by("-start")[:1][0]
        except IndexError:
            latest = None
        
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
        
        # Get the latest one directly (simulating the view logic)
        try:
            latest = CrawlSet.objects.filter(crawl_type="need").order_by("-start")[:1][0]
        except IndexError:
            latest = None
        
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
        try:
            latest = CrawlSet.objects.filter(crawl_type="need").order_by("-start")[:1][0]
        except IndexError:
            latest = None
        
        # Should return the need crawlset, not the article one
        assert latest is not None
        assert latest.id == need_crawlset.id
        assert latest.crawl_type == 'need'
