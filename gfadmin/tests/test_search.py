"""Tests for the admin search functionality."""
import pytest
from django.test import Client
from django.urls import reverse

from givefood.models import Foodbank, FoodbankChange


@pytest.mark.django_db
class TestSearchResults:
    """Test the search_results view."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def _create_foodbank(self, **kwargs):
        """Helper method to create a foodbank with minimal required fields."""
        defaults = {
            'name': 'Test Food Bank',
            'address': '123 Test St',
            'postcode': 'TE1 1ST',
            'lat_lng': '51.5074,-0.1278',
            'country': 'England',
            'url': 'https://example.com',
            'shopping_list_url': 'https://example.com/list',
            'contact_email': 'test@example.com',
        }
        defaults.update(kwargs)
        foodbank = Foodbank(**defaults)
        foodbank.latitude = 51.5074
        foodbank.longitude = -0.1278
        foodbank.save(do_geoupdate=False)
        return foodbank

    def test_search_finds_foodbank_by_name(self):
        """Test that search finds food banks by name."""
        self._create_foodbank(name='Manchester Food Bank')
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'Manchester'})
        
        assert response.status_code == 200
        assert 'Manchester Food Bank' in response.content.decode()

    def test_search_finds_foodbank_by_main_url(self):
        """Test that search finds food banks by main URL."""
        self._create_foodbank(name='Test FB', url='https://testfoodbank.org')
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'testfoodbank.org'})
        
        assert response.status_code == 200
        assert 'Test FB' in response.content.decode()

    def test_search_finds_foodbank_by_shopping_list_url(self):
        """Test that search finds food banks by shopping list URL."""
        self._create_foodbank(
            name='Shopping URL FB',
            shopping_list_url='https://unique-shopping-site.com/needs'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'unique-shopping-site.com'})
        
        assert response.status_code == 200
        assert 'Shopping URL FB' in response.content.decode()

    def test_search_finds_foodbank_by_donation_points_url(self):
        """Test that search finds food banks by donation points URL."""
        self._create_foodbank(
            name='Donation Points FB',
            donation_points_url='https://donation-points-unique.org/drop-off'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'donation-points-unique.org'})
        
        assert response.status_code == 200
        assert 'Donation Points FB' in response.content.decode()

    def test_search_finds_foodbank_by_locations_url(self):
        """Test that search finds food banks by locations URL."""
        self._create_foodbank(
            name='Locations URL FB',
            locations_url='https://locations-unique-domain.org/find-us'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'locations-unique-domain.org'})
        
        assert response.status_code == 200
        assert 'Locations URL FB' in response.content.decode()

    def test_search_finds_foodbank_by_contacts_url(self):
        """Test that search finds food banks by contacts URL."""
        self._create_foodbank(
            name='Contacts URL FB',
            contacts_url='https://contacts-unique-domain.org/contact'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'contacts-unique-domain.org'})
        
        assert response.status_code == 200
        assert 'Contacts URL FB' in response.content.decode()

    def test_search_finds_foodbank_by_rss_url(self):
        """Test that search finds food banks by RSS URL."""
        self._create_foodbank(
            name='RSS URL FB',
            rss_url='https://rss-unique-domain.org/feed.xml'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'rss-unique-domain.org'})
        
        assert response.status_code == 200
        assert 'RSS URL FB' in response.content.decode()

    def test_search_need_id_displays_truncated(self):
        """Test that need IDs in search results display only first 7 characters using need_id_short."""
        foodbank = self._create_foodbank(name='Need Search FB')
        
        # Create a need for the foodbank
        need = FoodbankChange(
            foodbank=foodbank,
            change_text='unique-search-term-for-need-test',
            published=True
        )
        need.save(do_translate=False, do_foodbank_save=False)
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'unique-search-term-for-need-test'})
        
        content = response.content.decode()
        assert response.status_code == 200
        
        # The full need_id should be in the URL (href)
        full_need_id = str(need.need_id)
        assert full_need_id in content
        
        # The displayed link text should be only the first 7 characters (via need_id_short)
        truncated_id = need.need_id_short()
        assert truncated_id == full_need_id[:7]  # Verify need_id_short returns first 7 chars
        # Check that the truncated ID appears (as link text)
        assert truncated_id in content
        
        # The 8th character should NOT appear immediately after the 7th character
        # as the link text (except in the href URL)
        # We can verify this by checking the HTML structure
        assert f'>{truncated_id}</a>' in content

    def test_search_finds_email_subscription(self):
        """Test that search finds email subscriptions."""
        from givefood.models import FoodbankSubscriber
        
        foodbank = self._create_foodbank(name='Test Subscription FB')
        FoodbankSubscriber.objects.create(
            foodbank=foodbank,
            email='test@subscriber.com',
            confirmed=True
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'test@subscriber.com'})
        
        content = response.content.decode()
        assert response.status_code == 200
        assert 'test@subscriber.com' in content
        assert 'Subscriptions' in content
        assert 'Test Subscription FB' in content
        assert '📧' in content  # Email emoji

    def test_search_finds_whatsapp_subscription(self):
        """Test that search finds WhatsApp subscriptions."""
        from givefood.models import WhatsappSubscriber
        
        foodbank = self._create_foodbank(name='WhatsApp Test FB')
        WhatsappSubscriber.objects.create(
            foodbank=foodbank,
            phone_number='+447700123456'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': '+447700123456'})
        
        content = response.content.decode()
        assert response.status_code == 200
        assert '+447700123456' in content
        assert 'Subscriptions' in content
        assert 'WhatsApp Test FB' in content
        assert '💬' in content  # WhatsApp emoji

    def test_search_finds_mobile_subscription(self):
        """Test that search finds mobile subscriptions."""
        from givefood.models import MobileSubscriber
        
        foodbank = self._create_foodbank(name='Mobile Test FB')
        MobileSubscriber.objects.create(
            foodbank=foodbank,
            device_id='unique-device-id-12345',
            platform='iOS',
            timezone='Europe/London',
            locale='en-GB',
            app_version='1.0.0',
            os_version='17.0',
            device_model='iPhone 15',
            sub_type='foodbank'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'unique-device-id-12345'})
        
        content = response.content.decode()
        assert response.status_code == 200
        assert 'unique-device-id-12345' in content
        assert 'Subscriptions' in content
        assert 'Mobile Test FB' in content
        assert 'iOS' in content
        assert '📱' in content  # Mobile emoji

    def test_search_finds_webpush_subscription(self):
        """Test that search finds WebPush subscriptions."""
        from givefood.models import WebPushSubscription
        
        foodbank = self._create_foodbank(name='WebPush Test FB')
        WebPushSubscription.objects.create(
            foodbank=foodbank,
            endpoint='https://push.example-unique-endpoint.com/subscription/abc123',
            p256dh='test-key-data',
            auth='test-auth-data',
            browser='Chrome'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'example-unique-endpoint.com'})
        
        content = response.content.decode()
        assert response.status_code == 200
        assert 'example-unique-endpoint.com' in content
        assert 'Subscriptions' in content
        assert 'WebPush Test FB' in content
        assert '🔔' in content  # WebPush emoji

    def test_search_only_shows_confirmed_email_subscriptions(self):
        """Test that search only shows confirmed email subscriptions."""
        from givefood.models import FoodbankSubscriber
        
        foodbank = self._create_foodbank(name='Status Test FB')
        FoodbankSubscriber.objects.create(
            foodbank=foodbank,
            email='confirmed@test.com',
            confirmed=True
        )
        FoodbankSubscriber.objects.create(
            foodbank=foodbank,
            email='unconfirmed@test.com',
            confirmed=False
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        
        # Search for confirmed subscription - should be found
        response = client.get(reverse('admin:search_results'), {'q': 'confirmed@test.com'})
        content = response.content.decode()
        assert 'confirmed@test.com' in content
        assert 'Subscriptions' in content
        
        # Search for unconfirmed subscription - should NOT be found in results
        response = client.get(reverse('admin:search_results'), {'q': 'unconfirmed@test.com'})
        content = response.content.decode()
        # Subscriptions section should not appear for unconfirmed emails
        assert 'Subscriptions' not in content

    def test_search_truncates_long_device_ids(self):
        """Test that long device IDs are truncated in search results."""
        from givefood.models import MobileSubscriber
        
        foodbank = self._create_foodbank(name='Truncate Test FB')
        long_device_id = 'very-long-device-id-that-should-be-truncated-in-display'
        MobileSubscriber.objects.create(
            foodbank=foodbank,
            device_id=long_device_id,
            platform='Android',
            timezone='Europe/London',
            locale='en-GB',
            app_version='1.0.0',
            os_version='14.0',
            device_model='Pixel',
            sub_type='foodbank'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': long_device_id})
        
        content = response.content.decode()
        assert response.status_code == 200
        # Should show first 20 characters plus ellipsis
        assert long_device_id[:20] in content
        assert '...' in content

    def test_search_truncates_long_endpoints(self):
        """Test that long endpoints are truncated in search results."""
        from givefood.models import WebPushSubscription
        
        foodbank = self._create_foodbank(name='Endpoint Truncate FB')
        long_endpoint = 'https://push.service.example.com/very-long-subscription-endpoint-url-with-many-characters/abc123def456'
        WebPushSubscription.objects.create(
            foodbank=foodbank,
            endpoint=long_endpoint,
            p256dh='test-key',
            auth='test-auth',
            browser='Firefox'
        )
        
        client = Client()
        self._setup_authenticated_session(client)
        response = client.get(reverse('admin:search_results'), {'q': 'very-long-subscription-endpoint'})
        
        content = response.content.decode()
        assert response.status_code == 200
        # Should show first 30 characters plus ellipsis (changed from 50)
        assert long_endpoint[:30] in content
        assert '...' in content

