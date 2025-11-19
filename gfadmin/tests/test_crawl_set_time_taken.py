"""Tests for CrawlSet time_taken method to ensure it rounds to nearest second."""
import pytest
from datetime import datetime, timedelta
from givefood.models import CrawlSet


@pytest.mark.django_db
class TestCrawlSetTimeTaken:
    """Test that CrawlSet.time_taken() rounds to the nearest second."""

    def test_time_taken_rounds_to_nearest_second(self):
        """Test that time_taken rounds microseconds to nearest second."""
        # Create a crawl set
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        
        # Set start and finish times with microseconds
        # 5.6 seconds should round to 6 seconds
        start_time = datetime(2024, 1, 1, 12, 0, 0, 0)
        finish_time = datetime(2024, 1, 1, 12, 0, 5, 600000)  # 5.6 seconds later
        
        crawl_set.start = start_time
        crawl_set.finish = finish_time
        crawl_set.save()
        
        time_taken = crawl_set.time_taken()
        
        # Should be rounded to 6 seconds
        assert time_taken == timedelta(seconds=6)
        # Should not have microseconds
        assert time_taken.microseconds == 0

    def test_time_taken_rounds_down_when_appropriate(self):
        """Test that time_taken rounds down when < 0.5 seconds."""
        # Create a crawl set
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        
        # 5.4 seconds should round to 5 seconds
        start_time = datetime(2024, 1, 1, 12, 0, 0, 0)
        finish_time = datetime(2024, 1, 1, 12, 0, 5, 400000)  # 5.4 seconds later
        
        crawl_set.start = start_time
        crawl_set.finish = finish_time
        crawl_set.save()
        
        time_taken = crawl_set.time_taken()
        
        # Should be rounded to 5 seconds
        assert time_taken == timedelta(seconds=5)
        # Should not have microseconds
        assert time_taken.microseconds == 0

    def test_time_taken_handles_exact_seconds(self):
        """Test that time_taken works correctly with exact seconds."""
        # Create a crawl set
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        
        # Exactly 10 seconds
        start_time = datetime(2024, 1, 1, 12, 0, 0, 0)
        finish_time = datetime(2024, 1, 1, 12, 0, 10, 0)
        
        crawl_set.start = start_time
        crawl_set.finish = finish_time
        crawl_set.save()
        
        time_taken = crawl_set.time_taken()
        
        # Should be exactly 10 seconds
        assert time_taken == timedelta(seconds=10)
        # Should not have microseconds
        assert time_taken.microseconds == 0

    def test_time_taken_returns_none_when_unfinished(self):
        """Test that time_taken returns None when finish is not set."""
        # Create a crawl set without a finish time
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        
        assert crawl_set.time_taken() is None

    def test_time_taken_with_longer_duration(self):
        """Test that time_taken works correctly with longer durations."""
        # Create a crawl set
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        
        # 1 hour, 23 minutes, 45.7 seconds should round to 1:23:46
        start_time = datetime(2024, 1, 1, 12, 0, 0, 0)
        finish_time = datetime(2024, 1, 1, 13, 23, 45, 700000)
        
        crawl_set.start = start_time
        crawl_set.finish = finish_time
        crawl_set.save()
        
        time_taken = crawl_set.time_taken()
        
        # Should be rounded to 1:23:46 (5026 seconds)
        assert time_taken == timedelta(seconds=5026)
        # Should not have microseconds
        assert time_taken.microseconds == 0
