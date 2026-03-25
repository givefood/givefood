"""Tests for the /admin/foodbanks/ list view."""
import pytest
from datetime import date
from django.test import Client
from django.urls import reverse
from django.core.cache import cache

from givefood.models import Foodbank, FoodbankHit


@pytest.mark.django_db
class TestFoodbanksListView:
    """Test the foodbanks admin list view."""

    def setup_method(self):
        cache.clear()

    def _setup_authenticated_session(self, client):
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def _make_foodbank(self, name, **kwargs):
        fb = Foodbank(
            name=name,
            url=f'https://{name.lower().replace(" ", "")}.com',
            shopping_list_url=f'https://{name.lower().replace(" ", "")}.com/shop',
            address='1 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email=f'{name.lower().replace(" ", "")}@example.com',
            **kwargs,
        )
        fb.save(do_geoupdate=False, do_decache=False)
        return fb

    def test_foodbanks_list_returns_200(self):
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbanks'))
        assert response.status_code == 200

    def test_foodbanks_list_caches_result(self):
        """Subsequent requests are served from cache, making one fewer DB query."""
        self._make_foodbank('Alpha Bank')
        client = Client()
        self._setup_authenticated_session(client)

        # Prime the cache
        client.get(reverse('admin:foodbanks'))

        # The cache key for the default sort ('edited') should now be populated
        cached = cache.get('admin_foodbanks_edited')
        assert cached is not None
        assert any(fb.name == 'Alpha Bank' for fb in cached)

    def test_foodbanks_list_cache_keyed_by_sort(self):
        """Each sort option is cached independently."""
        client = Client()
        self._setup_authenticated_session(client)

        client.get(reverse('admin:foodbanks') + '?sort=name')
        client.get(reverse('admin:foodbanks') + '?sort=-name')

        assert cache.get('admin_foodbanks_name') is not None
        assert cache.get('admin_foodbanks_-name') is not None

    def test_foodbanks_list_excludes_closed(self):
        """Closed foodbanks should not appear in the list."""
        self._make_foodbank('Open Bank', is_closed=False)
        self._make_foodbank('Closed Bank', is_closed=True)

        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbanks'))

        content = response.content.decode()
        assert 'Open Bank' in content
        assert 'Closed Bank' not in content

    def test_foodbanks_list_includes_hits(self):
        """28-day hit counts should appear in the rendered page."""
        fb = self._make_foodbank('Hit Bank')
        FoodbankHit.objects.create(foodbank=fb, day=date.today(), hits=42)

        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:foodbanks'))

        assert response.status_code == 200
        assert b'42' in response.content
