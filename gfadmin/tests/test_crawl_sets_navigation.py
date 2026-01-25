"""Tests for Crawl Sets navigation in admin."""
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestCrawlSetsNavigation:
    """Test that Crawl Sets is in the admin navigation."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def _get_authenticated_client(self):
        """Helper to get an authenticated client for testing admin views."""
        client = Client()
        self._setup_authenticated_session(client)
        return client

    def test_crawl_sets_page_has_crawl_sets_section(self):
        """Test that the crawl sets page has section set to 'crawl_sets'."""
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_sets'))
        assert response.status_code == 200
        assert response.context['section'] == 'crawl_sets'

    def test_crawl_set_detail_page_has_crawl_sets_section(self):
        """Test that the crawl set detail page has section set to 'crawl_sets'."""
        from givefood.models import CrawlSet
        from django.utils import timezone
        
        # Create a crawl set
        crawl_set = CrawlSet.objects.create(
            crawl_type='need',
            start=timezone.now()
        )
        
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_set', kwargs={'crawl_set_id': crawl_set.id}))
        assert response.status_code == 200
        assert response.context['section'] == 'crawl_sets'

    def test_crawl_sets_link_in_navigation(self):
        """Test that Crawl Sets link is present in the navigation."""
        client = self._get_authenticated_client()
        response = client.get(reverse('gfadmin:crawl_sets'))
        assert response.status_code == 200
        
        # Check that the page contains the Crawl Sets link in navigation
        content = response.content.decode('utf-8')
        assert 'href="/admin/crawl-sets/"' in content or 'href="{% url \'admin:crawl_sets\' %}"' in content
        assert '>Crawl Sets</a>' in content
