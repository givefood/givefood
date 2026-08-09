"""Tests for the on demand food bank admin tabs."""
from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse

from givefood.models import (
    CrawlItem, Foodbank, FoodbankArticle, FoodbankChange, FoodbankDonationPoint,
    FoodbankLocation, FoodbankSubscriber, Order,
)


def create_foodbank(**kwargs):
    """A food bank with the fields the admin page needs."""
    defaults = {
        'name': 'Test Foodbank',
        'url': 'https://example.com',
        'shopping_list_url': 'https://example.com/shopping',
        'address': '123 Test St',
        'postcode': 'AB12 3CD',
        'country': 'England',
        'lat_lng': '51.5074,-0.1278',
        'contact_email': 'test@example.com',
        'network': 'Independent',
    }
    defaults.update(kwargs)
    foodbank = Foodbank(**defaults)
    foodbank.save(do_geoupdate=False, do_decache=False)
    return foodbank


def populate(foodbank):
    """Give a food bank a row in each of the on demand tabs."""

    FoodbankLocation(
        foodbank=foodbank,
        name='Test Location',
        address='1 Location Street',
        postcode='AB12 3CD',
        lat_lng='51.5074,-0.1278',
    ).save(do_geoupdate=False, do_foodbank_resave=False)

    FoodbankDonationPoint(
        foodbank=foodbank,
        name='Test Donation Point',
        address='2 Donation Street',
        postcode='AB12 3CD',
        lat_lng='51.5074,-0.1278',
    ).save(do_geoupdate=False, do_foodbank_resave=False)

    FoodbankChange.objects.create(
        foodbank=foodbank,
        change_text='Beans, Soup',
        published=False,
    )

    # gemini() parses the order text into lines, which tests have no business calling
    with patch('givefood.models.orders.gemini', return_value=[]):
        Order(
            foodbank=foodbank,
            items_text='Beans',
            delivery_date=date(2026, 1, 1),
            delivery_hour=9,
        ).save(do_foodbank_save=False)

    FoodbankArticle.objects.create(
        foodbank=foodbank,
        title='Test Article',
        url='https://example.com/article',
        published_date=date(2026, 1, 1),
    )

    FoodbankSubscriber.objects.create(
        foodbank=foodbank,
        email='subscriber@example.com',
        confirmed=True,
    )

    CrawlItem.objects.create(
        foodbank=foodbank,
        crawl_type='need',
        url='https://example.com/shopping',
    )


@pytest.mark.django_db
class TestFoodbankLazyTabs:

    def test_panels_are_placeholders_on_the_page(self, admin_client):
        """The page ships empty panels with htmx triggers, not their contents."""
        foodbank = create_foodbank()
        populate(foodbank)

        response = admin_client.get(reverse('admin:foodbank', kwargs={'slug': foodbank.slug}))
        content = response.content.decode('utf-8')

        assert response.status_code == 200
        for tab in ['needsorders', 'donationpoints', 'articles', 'subscribers', 'crawls']:
            assert 'id="%s-panel"' % tab in content
            assert reverse('admin:foodbank_tab', kwargs={'slug': foodbank.slug, 'tab': tab}) in content
        assert 'hx-trigger="showtab once"' in content

        # None of the deferred rows are in the initial page
        assert 'Beans, Soup' not in content
        assert 'Test Donation Point' not in content
        assert 'Test Article' not in content
        assert 'subscriber@example.com' not in content
        assert 'https://example.com/shopping</a>' not in content

        # But the General & Locations tab still is
        assert 'Test Location' in content

    def test_counts_are_still_on_the_tabs(self, admin_client):
        """Tab counts survive the content moving out of the page."""
        foodbank = create_foodbank()
        populate(foodbank)

        response = admin_client.get(reverse('admin:foodbank', kwargs={'slug': foodbank.slug}))
        counts = response.context['counts']

        assert counts == {
            'locations': 1,
            'needs': 1,
            'orders': 1,
            'donation_points': 1,
            'articles': 1,
            'subscribers': 1,
            'crawls': 1,
            'photos': 0,
        }

    @pytest.mark.parametrize('tab,expected', [
        ('needsorders', 'Beans, Soup'),
        ('donationpoints', 'Test Donation Point'),
        ('articles', 'Test Article'),
        ('subscribers', 'subscriber@example.com'),
        ('crawls', 'https://example.com/shopping'),
    ])
    def test_tab_returns_its_own_panel(self, admin_client, tab, expected):
        """Each tab endpoint returns just that panel's markup."""
        foodbank = create_foodbank()
        populate(foodbank)

        response = admin_client.get(reverse('admin:foodbank_tab', kwargs={'slug': foodbank.slug, 'tab': tab}))
        content = response.content.decode('utf-8')

        assert response.status_code == 200
        assert expected in content
        # A fragment, not a whole page
        assert '<!DOCTYPE html>' not in content

    def test_unknown_tab_is_a_404(self, admin_client):
        foodbank = create_foodbank()

        response = admin_client.get(reverse('admin:foodbank_tab', kwargs={'slug': foodbank.slug, 'tab': 'nonsense'}))

        assert response.status_code == 404

    def test_unknown_foodbank_is_a_404(self, admin_client):
        response = admin_client.get(reverse('admin:foodbank_tab', kwargs={'slug': 'no-such-foodbank', 'tab': 'crawls'}))

        assert response.status_code == 404

    def test_page_query_count_does_not_grow_with_content(self, admin_client, django_assert_max_num_queries):
        """
        The point of the exercise -- the page costs the same number of queries
        whether or not the food bank has needs, orders, crawls and the rest.
        """
        empty = create_foodbank(name='Empty Foodbank')
        full = create_foodbank(name='Full Foodbank')
        populate(full)

        with django_assert_max_num_queries(10) as empty_queries:
            admin_client.get(reverse('admin:foodbank', kwargs={'slug': empty.slug}))

        with django_assert_max_num_queries(10) as full_queries:
            admin_client.get(reverse('admin:foodbank', kwargs={'slug': full.slug}))

        assert len(empty_queries) == len(full_queries)
