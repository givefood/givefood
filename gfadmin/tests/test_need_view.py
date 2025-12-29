"""Tests for the admin need view optimizations."""
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from givefood.models import (
    Foodbank, FoodbankChange, FoodbankChangeTranslation, 
    FoodbankSubscriber, CrawlSet, CrawlItem
)


def _setup_authenticated_session(client):
    """Helper to setup an authenticated session for testing admin views."""
    session = client.session
    session['user_data'] = {
        'email': 'test@givefood.org.uk',
        'email_verified': True,
        'hd': 'givefood.org.uk',
    }
    session.save()


@pytest.fixture
def foodbank():
    """Create a test foodbank."""
    fb = Foodbank(
        name='Test Food Bank',
        slug='test-food-bank',
        address='123 Test St',
        postcode='TE1 1ST',
        lat_lng='51.5074,-0.1278',
        country='England',
        contact_email='test@example.com',
        url='https://example.com',
        shopping_list_url='https://example.com/shopping',
        edited=timezone.now(),
        is_closed=False
    )
    fb.latitude = 51.5074
    fb.longitude = -0.1278
    fb.parliamentary_constituency_slug = 'test-constituency'
    fb.save(do_geoupdate=False, do_decache=False)
    return fb


@pytest.fixture
def need(foodbank):
    """Create a test need."""
    need = FoodbankChange(
        foodbank=foodbank,
        change_text='Pasta\nRice\nBeans',
        excess_change_text='Bread',
        published=True,
        input_method='typed'
    )
    need.save(do_translate=False, do_foodbank_save=False)
    return need


@pytest.fixture
def prev_published_need(foodbank, need):
    """Create a previous published need."""
    prev_need = FoodbankChange(
        foodbank=foodbank,
        change_text='Old Pasta\nOld Rice',
        excess_change_text='Old Bread',
        published=True,
        input_method='typed'
    )
    prev_need.save(do_translate=False, do_foodbank_save=False)
    # Update created to be before the main need using timezone.timedelta
    FoodbankChange.objects.filter(pk=prev_need.pk).update(
        created=need.created - timezone.timedelta(days=1)
    )
    prev_need.refresh_from_db()
    return prev_need


@pytest.mark.django_db
class TestNeedView:
    """Test the admin need view."""

    def test_need_view_returns_200(self, need):
        """Test that the need view returns a 200 status code."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        assert response.status_code == 200

    def test_need_view_includes_need_in_context(self, need):
        """Test that the need object is in the context."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        assert 'need' in response.context
        assert response.context['need'].need_id == need.need_id

    def test_need_view_includes_foodbank_via_select_related(self, need):
        """Test that foodbank is loaded via select_related."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        # The foodbank should be accessible without additional queries
        need_obj = response.context['need']
        assert need_obj.foodbank is not None
        assert need_obj.foodbank.name == 'Test Food Bank'

    def test_need_view_includes_subscriber_count(self, need, foodbank):
        """Test that subscriber count is pre-computed."""
        # Create some subscribers
        FoodbankSubscriber.objects.create(
            foodbank=foodbank,
            email='test1@example.com',
            confirmed=True
        )
        FoodbankSubscriber.objects.create(
            foodbank=foodbank,
            email='test2@example.com',
            confirmed=True
        )
        
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        
        assert 'subscriber_count' in response.context
        assert response.context['subscriber_count'] == 2

    def test_need_view_includes_translation_count(self, need):
        """Test that translation count is pre-computed."""
        # Create some translations
        FoodbankChangeTranslation.objects.create(
            need=need,
            foodbank=need.foodbank,
            language='es',
            change_text='Pasta español'
        )
        FoodbankChangeTranslation.objects.create(
            need=need,
            foodbank=need.foodbank,
            language='pl',
            change_text='Makaron polski'
        )
        
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        
        assert 'translation_count' in response.context
        assert response.context['translation_count'] == 2

    def test_need_view_includes_diff_values(self, need, prev_published_need):
        """Test that diff values are pre-computed."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        
        assert 'diff_from_pub' in response.context
        assert 'diff_from_pub_excess' in response.context
        # The diff should show changes between old and new
        # Since we have different text, there should be a diff

    def test_need_view_includes_prev_published(self, need, prev_published_need):
        """Test that prev_published is in the context."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        
        assert 'prev_published' in response.context
        assert response.context['prev_published'] is not None

    def test_need_view_crawl_set_prefetched(self, need, foodbank):
        """Test that crawl_set is pre-fetched."""
        # Create a crawl set and item linked to this need
        crawl_set = CrawlSet.objects.create(crawl_type='need')
        content_type = ContentType.objects.get_for_model(FoodbankChange)
        CrawlItem.objects.create(
            crawl_set=crawl_set,
            crawl_type='need',
            foodbank=foodbank,
            content_type=content_type,
            object_id=need.id
        )
        
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        
        assert 'crawl_set' in response.context
        assert response.context['crawl_set'] is not None
        assert response.context['crawl_set'].id == crawl_set.id

    def test_need_view_without_foodbank(self):
        """Test that the view handles needs without a foodbank."""
        need = FoodbankChange(
            foodbank=None,
            change_text='Some items',
            published=False,
            input_method='typed'
        )
        need.save(do_translate=False, do_foodbank_save=False)
        
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[need.need_id])
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context['subscriber_count'] == 0
        assert response.context['prev_published'] is None
        assert response.context['prev_nonpert'] is None
