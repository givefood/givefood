"""Tests for the foodbank_use_ai_detail functionality."""
import pytest
from django.test import RequestFactory

from givefood.models import Foodbank


@pytest.mark.django_db
class TestFoodbankUseAiDetail:
    """Test the foodbank_use_ai_detail HTMX view."""

    def test_update_phone_number_with_htmx(self):
        """Test updating phone number via HTMX."""
        # Create a test foodbank
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            phone_number='0123456789',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/phone_number/',
            data={'value': '9876543210'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='phone_number')
        
        # Refresh from database
        foodbank.refresh_from_db()
        
        assert foodbank.phone_number == '9876543210'
        assert response.status_code == 200
        assert b'Used' in response.content
        assert b'disabled' in response.content

    def test_update_phone_number_removes_spaces(self):
        """Test that phone number spaces are removed when updating via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            phone_number='0123456789',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/phone_number/',
            data={'value': '01onal 234 567 890'},  # Phone number with spaces
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='phone_number')
        
        foodbank.refresh_from_db()
        
        # Spaces should be removed
        assert foodbank.phone_number == '01onal234567890'
        assert response.status_code == 200

    def test_update_email_with_htmx(self):
        """Test updating email via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='old@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/contact_email/',
            data={'value': 'new@example.com'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='contact_email')
        
        foodbank.refresh_from_db()
        
        assert foodbank.contact_email == 'new@example.com'
        assert b'Used' in response.content

    def test_update_charity_number_with_htmx(self):
        """Test updating charity number via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            charity_number='12345',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/charity_number/',
            data={'value': '67890'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='charity_number')
        
        foodbank.refresh_from_db()
        
        assert foodbank.charity_number == '67890'
        assert b'Used' in response.content

    def test_invalid_field_returns_400(self):
        """Test that invalid field returns 400 error."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/invalid_field/',
            data={'value': 'test'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='invalid_field')
        
        assert response.status_code == 400

    def test_invalid_email_returns_400(self):
        """Test that invalid email format returns 400 error."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/contact_email/',
            data={'value': 'not-a-valid-email'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='contact_email')
        
        assert response.status_code == 400
        assert b'Invalid email format' in response.content

    def test_update_facebook_page_with_htmx(self):
        """Test updating Facebook page via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            facebook_page='oldfacebookpage',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/facebook_page/',
            data={'value': 'newfacebookpage'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='facebook_page')
        
        foodbank.refresh_from_db()
        
        assert foodbank.facebook_page == 'newfacebookpage'
        assert response.status_code == 200
        assert b'Used' in response.content

    def test_update_twitter_handle_with_htmx(self):
        """Test updating Twitter handle via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            twitter_handle='oldhandle',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/twitter_handle/',
            data={'value': 'newhandle'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='twitter_handle')
        
        foodbank.refresh_from_db()
        
        assert foodbank.twitter_handle == 'newhandle'
        assert b'Used' in response.content

    def test_update_bankuet_slug_with_htmx(self):
        """Test updating Bankuet slug via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            bankuet_slug='oldslug',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/bankuet_slug/',
            data={'value': 'newslug'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='bankuet_slug')
        
        foodbank.refresh_from_db()
        
        assert foodbank.bankuet_slug == 'newslug'
        assert b'Used' in response.content

    def test_update_rss_url_with_htmx(self):
        """Test updating RSS URL via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            rss_url='https://example.com/old-feed.rss',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/rss_url/',
            data={'value': 'https://example.com/new-feed.rss'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='rss_url')
        
        foodbank.refresh_from_db()
        
        assert foodbank.rss_url == 'https://example.com/new-feed.rss'
        assert b'Used' in response.content

    def test_update_news_url_with_htmx(self):
        """Test updating News URL via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            news_url='https://example.com/old-news',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/news_url/',
            data={'value': 'https://example.com/new-news'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='news_url')
        
        foodbank.refresh_from_db()
        
        assert foodbank.news_url == 'https://example.com/new-news'
        assert b'Used' in response.content

    def test_update_donation_points_url_with_htmx(self):
        """Test updating Donation Points URL via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            donation_points_url='https://example.com/old-donate',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/donation_points_url/',
            data={'value': 'https://example.com/new-donate'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='donation_points_url')
        
        foodbank.refresh_from_db()
        
        assert foodbank.donation_points_url == 'https://example.com/new-donate'
        assert b'Used' in response.content

    def test_update_locations_url_with_htmx(self):
        """Test updating Locations URL via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            locations_url='https://example.com/old-locations',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/locations_url/',
            data={'value': 'https://example.com/new-locations'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='locations_url')
        
        foodbank.refresh_from_db()
        
        assert foodbank.locations_url == 'https://example.com/new-locations'
        assert b'Used' in response.content

    def test_update_contacts_url_with_htmx(self):
        """Test updating Contacts URL via HTMX."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            contacts_url='https://example.com/old-contacts',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/contacts_url/',
            data={'value': 'https://example.com/new-contacts'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='contacts_url')
        
        foodbank.refresh_from_db()
        
        assert foodbank.contacts_url == 'https://example.com/new-contacts'
        assert b'Used' in response.content

    def test_invalid_url_returns_400(self):
        """Test that invalid URL format returns 400 error."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        from gfadmin.views import foodbank_use_ai_detail
        factory = RequestFactory()
        request = factory.post(
            f'/admin/foodbank/{foodbank.slug}/use-ai/rss_url/',
            data={'value': 'not-a-valid-url'},
            **{'HTTP_HX-Request': 'true'}
        )
        
        response = foodbank_use_ai_detail(request, slug=foodbank.slug, field='rss_url')
        
        assert response.status_code == 400
        assert b'Invalid URL format' in response.content
