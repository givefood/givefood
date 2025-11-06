"""Tests for the SlugRedirect admin interface."""
import pytest
from django.urls import reverse

from givefood.models import SlugRedirect


@pytest.mark.django_db
class TestSlugRedirectModel:
    """Test the SlugRedirect model in admin context."""

    def test_slug_redirect_can_be_created(self):
        """Test that a SlugRedirect can be created."""
        redirect = SlugRedirect.objects.create(
            old_slug="test-old",
            new_slug="test-new"
        )
        assert redirect.old_slug == "test-old"
        assert redirect.new_slug == "test-new"
        assert redirect.id is not None

    def test_slug_redirect_can_be_updated(self):
        """Test that a SlugRedirect can be updated."""
        redirect = SlugRedirect.objects.create(
            old_slug="test-old",
            new_slug="test-new"
        )
        redirect.old_slug = "updated-old"
        redirect.new_slug = "updated-new"
        redirect.save()
        
        redirect.refresh_from_db()
        assert redirect.old_slug == "updated-old"
        assert redirect.new_slug == "updated-new"

    def test_slug_redirect_list_query(self):
        """Test querying SlugRedirect objects for list view."""
        # Create some test redirects
        SlugRedirect.objects.create(old_slug="old1", new_slug="new1")
        SlugRedirect.objects.create(old_slug="old2", new_slug="new2")
        SlugRedirect.objects.create(old_slug="old3", new_slug="new3")
        
        # Query as the view would
        slug_redirects = SlugRedirect.objects.all().order_by("-created")
        
        assert slug_redirects.count() == 3
        # Most recent should be first
        assert slug_redirects[0].old_slug == "old3"

    def test_slug_redirect_get_by_id(self):
        """Test getting a specific SlugRedirect by id."""
        redirect = SlugRedirect.objects.create(
            old_slug="test-old",
            new_slug="test-new"
        )
        
        # Query as the view would
        fetched = SlugRedirect.objects.get(id=redirect.id)
        
        assert fetched.id == redirect.id
        assert fetched.old_slug == "test-old"
        assert fetched.new_slug == "test-new"


@pytest.mark.django_db
class TestSlugRedirectUrls:
    """Test that URL patterns are correctly configured."""

    def test_slug_redirects_list_url_exists(self):
        """Test that the slug_redirects list URL pattern is configured."""
        url = reverse('admin:slug_redirects')
        assert url == '/admin/slug-redirects/'

    def test_slug_redirect_new_url_exists(self):
        """Test that the new slug redirect URL pattern is configured."""
        url = reverse('admin:slug_redirect_new')
        assert url == '/admin/slug-redirect/new/'

    def test_slug_redirect_edit_url_exists(self):
        """Test that the edit slug redirect URL pattern is configured."""
        url = reverse('admin:slug_redirect_form', args=[123])
        assert url == '/admin/slug-redirect/123/edit/'

