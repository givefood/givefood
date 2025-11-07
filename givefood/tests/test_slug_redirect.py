#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from django.test import Client
from django.core.cache import cache
from django.db import IntegrityError

from givefood.models import SlugRedirect


@pytest.fixture
def populate_slug_redirects():
    """Fixture to populate slug redirects for testing."""
    # Data from OLD_FOODBANK_SLUGS - subset for testing
    redirects_data = {
        "angus": "dundee-angus",
        "dundee": "dundee-angus",
        "lifeshare": "lifeshare-manchester",
        "bath": "bath-keynsham-somer-valley",
    }
    
    redirects = [
        SlugRedirect(old_slug=old_slug, new_slug=new_slug)
        for old_slug, new_slug in redirects_data.items()
    ]
    SlugRedirect.objects.bulk_create(redirects)
    cache.clear()
    return redirects_data


@pytest.mark.django_db
class TestSlugRedirectModel:
    """Test the SlugRedirect model."""

    def test_slug_redirect_creation(self):
        """Test creating a slug redirect."""
        redirect = SlugRedirect.objects.create(
            old_slug="test-old",
            new_slug="test-new"
        )
        assert redirect.old_slug == "test-old"
        assert redirect.new_slug == "test-new"
        assert str(redirect) == "test-old -> test-new"

    def test_slug_redirect_unique_old_slug(self):
        """Test that old_slug must be unique."""
        SlugRedirect.objects.create(old_slug="test", new_slug="new1")
        
        with pytest.raises(IntegrityError):
            SlugRedirect.objects.create(old_slug="test", new_slug="new2")

    def test_slug_redirects_can_be_queried(self, populate_slug_redirects):
        """Test that slug redirects can be queried."""
        # Check that some known redirects exist
        assert SlugRedirect.objects.filter(old_slug="angus", new_slug="dundee-angus").exists()
        assert SlugRedirect.objects.filter(old_slug="dundee", new_slug="dundee-angus").exists()
        assert SlugRedirect.objects.filter(old_slug="lifeshare", new_slug="lifeshare-manchester").exists()

    def test_slug_redirect_lookup(self, populate_slug_redirects):
        """Test looking up a slug redirect."""
        redirect = SlugRedirect.objects.get(old_slug="angus")
        assert redirect.new_slug == "dundee-angus"


@pytest.mark.django_db
class TestSlugRedirectCaching:
    """Test that slug redirect caching works."""

    def test_slug_redirects_are_cached(self, populate_slug_redirects):
        """Test that slug redirects are cached after first access."""
        from givefood.func import get_slug_redirects
        
        cache.clear()
        
        # First call should hit the database
        redirects1 = get_slug_redirects()
        assert isinstance(redirects1, dict)
        assert len(redirects1) > 0
        assert "angus" in redirects1
        assert redirects1["angus"] == "dundee-angus"
        
        # Second call should use cache
        redirects2 = get_slug_redirects()
        assert redirects1 == redirects2
        
        # Verify it's actually from cache
        cache_key = 'slug_redirects_dict'
        cached_redirects = cache.get(cache_key)
        assert cached_redirects is not None
        assert cached_redirects == redirects1

    def test_cache_can_be_invalidated(self, populate_slug_redirects):
        """Test that cache can be cleared and reloaded."""
        from givefood.func import get_slug_redirects
        
        cache.clear()
        
        # Get redirects to populate cache
        redirects1 = get_slug_redirects()
        
        # Add a new redirect
        SlugRedirect.objects.create(old_slug="cache-test-old", new_slug="cache-test-new")
        
        # Cache still has old data
        cached_redirects = get_slug_redirects()
        assert "cache-test-old" not in cached_redirects
        
        # Clear cache
        cache.clear()
        
        # Now we should get the updated data
        fresh_redirects = get_slug_redirects()
        assert "cache-test-old" in fresh_redirects
        assert fresh_redirects["cache-test-old"] == "cache-test-new"

    def test_get_slug_redirects_returns_dict(self, populate_slug_redirects):
        """Test that get_slug_redirects returns a dictionary."""
        from givefood.func import get_slug_redirects
        
        cache.clear()
        redirects = get_slug_redirects()
        
        assert isinstance(redirects, dict)
        assert len(redirects) == 4  # We populated 4 redirects
        assert "angus" in redirects
        assert "dundee" in redirects
        assert "lifeshare" in redirects
        assert "bath" in redirects


@pytest.mark.django_db
class TestSlugRedirectURLs:
    """Test that slug redirect URLs work for all languages."""

    def test_slug_redirect_works_for_english(self, populate_slug_redirects):
        """Test that slug redirects work for English (default language)."""
        client = Client()
        
        # Test main foodbank page redirect
        response = client.get('/needs/at/angus/', follow=False)
        assert response.status_code == 302
        assert response.url == '/needs/at/dundee-angus/'
        
        # Test subpage redirect
        response = client.get('/needs/at/angus/news/', follow=False)
        assert response.status_code == 302
        assert response.url == '/needs/at/dundee-angus/news/'

    def test_slug_redirect_works_for_polish(self, populate_slug_redirects):
        """Test that slug redirects work for Polish language."""
        client = Client()
        
        # Test main foodbank page redirect with Polish prefix
        response = client.get('/pl/needs/at/angus/', follow=False)
        assert response.status_code == 302
        assert response.url == '/needs/at/dundee-angus/'
        
        # Test subpage redirect
        response = client.get('/pl/needs/at/angus/news/', follow=False)
        assert response.status_code == 302
        assert response.url == '/needs/at/dundee-angus/news/'

    def test_slug_redirect_works_for_spanish(self, populate_slug_redirects):
        """Test that slug redirects work for Spanish language."""
        client = Client()
        
        # Test main foodbank page redirect with Spanish prefix
        response = client.get('/es/needs/at/lifeshare/', follow=False)
        assert response.status_code == 302
        assert response.url == '/needs/at/lifeshare-manchester/'
        
        # Test subpage redirect
        response = client.get('/es/needs/at/lifeshare/locations/', follow=False)
        assert response.status_code == 302
        assert response.url == '/needs/at/lifeshare-manchester/locations/'

    def test_slug_redirect_works_for_welsh(self, populate_slug_redirects):
        """Test that slug redirects work for Welsh language."""
        client = Client()
        
        # Test main foodbank page redirect with Welsh prefix
        response = client.get('/cy/needs/at/bath/', follow=False)
        assert response.status_code == 302
        assert response.url == '/needs/at/bath-keynsham-somer-valley/'

    def test_slug_redirect_works_for_all_subpages(self, populate_slug_redirects):
        """Test that slug redirects work for all defined subpages."""
        from givefood.const.general import FOODBANK_SUBPAGES
        client = Client()
        
        # Test all subpages for English
        for subpage in FOODBANK_SUBPAGES:
            response = client.get(f'/needs/at/dundee/{subpage}/', follow=False)
            assert response.status_code == 302
            assert response.url == f'/needs/at/dundee-angus/{subpage}/'
        
        # Test a few subpages with language prefix
        for subpage in ['news', 'charity', 'nearby']:
            response = client.get(f'/pl/needs/at/dundee/{subpage}/', follow=False)
            assert response.status_code == 302
            assert response.url == f'/needs/at/dundee-angus/{subpage}/'


