import pytest
from givefood.models import Foodbank, FoodbankSubscriber, WhatsappSubscriber, MobileSubscriber, WebPushSubscription


@pytest.mark.django_db
class TestSubscriptionsData:
    """Test the subscriptions data retrieval and filtering logic"""

    @pytest.fixture
    def foodbank(self):
        """Create a test foodbank"""
        foodbank = Foodbank(
            name="Test Foodbank",
            slug="test-foodbank",
            address="123 Test St",
            postcode="SW1A 1AA",
            lat_lng="51.5074,-0.1278",
            country="England",
            url="https://example.com",
            shopping_list_url="https://example.com/needs",
            contact_email="test@example.com"
        )
        foodbank.latitude = 51.5074
        foodbank.longitude = -0.1278
        foodbank.save(do_geoupdate=False)
        return foodbank

    @pytest.fixture
    def email_subscription(self, foodbank):
        """Create an email subscription"""
        return FoodbankSubscriber.objects.create(
            foodbank=foodbank,
            email="subscriber@example.com",
            confirmed=True
        )

    @pytest.fixture
    def whatsapp_subscription(self, foodbank):
        """Create a WhatsApp subscription"""
        return WhatsappSubscriber.objects.create(
            foodbank=foodbank,
            phone_number="+447700900000"
        )

    @pytest.fixture
    def mobile_subscription(self, foodbank):
        """Create a mobile subscription"""
        return MobileSubscriber.objects.create(
            foodbank=foodbank,
            device_id="test-device-123",
            platform="iOS",
            timezone="Europe/London",
            locale="en-GB",
            app_version="1.0.0",
            os_version="17.0",
            device_model="iPhone 15",
            sub_type="foodbank"
        )

    @pytest.fixture
    def webpush_subscription(self, foodbank):
        """Create a WebPush subscription"""
        return WebPushSubscription.objects.create(
            foodbank=foodbank,
            endpoint="https://push.example.com/subscription/123",
            p256dh="test-key",
            auth="test-auth",
            browser="Chrome"
        )

    def test_all_subscription_types_exist(self, email_subscription, whatsapp_subscription, mobile_subscription, webpush_subscription):
        """Test that all subscription types can be created and retrieved"""
        # Check email subscriptions
        email_subs = FoodbankSubscriber.objects.all()
        assert email_subs.count() == 1
        assert email_subs.first().email == "subscriber@example.com"
        
        # Check WhatsApp subscriptions
        whatsapp_subs = WhatsappSubscriber.objects.all()
        assert whatsapp_subs.count() == 1
        assert whatsapp_subs.first().phone_number == "+447700900000"
        
        # Check mobile subscriptions
        mobile_subs = MobileSubscriber.objects.all()
        assert mobile_subs.count() == 1
        assert mobile_subs.first().platform == "iOS"
        
        # Check WebPush subscriptions
        webpush_subs = WebPushSubscription.objects.all()
        assert webpush_subs.count() == 1
        assert webpush_subs.first().browser == "Chrome"

    def test_filter_email_subscriptions(self, email_subscription, whatsapp_subscription):
        """Test filtering only email subscriptions"""
        email_subs = FoodbankSubscriber.objects.all()
        assert email_subs.count() == 1
        assert email_subs.first().email == "subscriber@example.com"
        
        # Ensure WhatsApp subscriptions are separate
        whatsapp_subs = WhatsappSubscriber.objects.all()
        assert whatsapp_subs.count() == 1

    def test_filter_whatsapp_subscriptions(self, email_subscription, whatsapp_subscription):
        """Test filtering only WhatsApp subscriptions"""
        whatsapp_subs = WhatsappSubscriber.objects.all()
        assert whatsapp_subs.count() == 1
        assert whatsapp_subs.first().phone_number == "+447700900000"

    def test_filter_mobile_subscriptions(self, mobile_subscription):
        """Test filtering only mobile subscriptions"""
        mobile_subs = MobileSubscriber.objects.all()
        assert mobile_subs.count() == 1
        assert mobile_subs.first().device_id == "test-device-123"

    def test_filter_webpush_subscriptions(self, webpush_subscription):
        """Test filtering only WebPush subscriptions"""
        webpush_subs = WebPushSubscription.objects.all()
        assert webpush_subs.count() == 1
        assert webpush_subs.first().endpoint == "https://push.example.com/subscription/123"

    def test_delete_email_subscription(self, email_subscription):
        """Test deleting an email subscription"""
        assert FoodbankSubscriber.objects.filter(email='subscriber@example.com').count() == 1
        
        email_subscription.delete()
        
        assert FoodbankSubscriber.objects.filter(email='subscriber@example.com').count() == 0

    def test_delete_whatsapp_subscription(self, whatsapp_subscription):
        """Test deleting a WhatsApp subscription"""
        sub_id = whatsapp_subscription.id
        assert WhatsappSubscriber.objects.filter(id=sub_id).count() == 1
        
        whatsapp_subscription.delete()
        
        assert WhatsappSubscriber.objects.filter(id=sub_id).count() == 0

    def test_delete_mobile_subscription(self, mobile_subscription):
        """Test deleting a mobile subscription"""
        sub_id = mobile_subscription.id
        assert MobileSubscriber.objects.filter(id=sub_id).count() == 1
        
        mobile_subscription.delete()
        
        assert MobileSubscriber.objects.filter(id=sub_id).count() == 0

    def test_delete_webpush_subscription(self, webpush_subscription):
        """Test deleting a WebPush subscription"""
        sub_id = webpush_subscription.id
        assert WebPushSubscription.objects.filter(id=sub_id).count() == 1
        
        webpush_subscription.delete()
        
        assert WebPushSubscription.objects.filter(id=sub_id).count() == 0

    def test_subscriptions_have_timestamps(self, email_subscription, whatsapp_subscription, mobile_subscription, webpush_subscription):
        """Test that all subscriptions have created timestamps"""
        assert email_subscription.created is not None
        assert whatsapp_subscription.created is not None
        assert mobile_subscription.created is not None
        assert webpush_subscription.created is not None

    def test_subscriptions_linked_to_foodbank(self, foodbank, email_subscription, whatsapp_subscription, mobile_subscription, webpush_subscription):
        """Test that all subscriptions are properly linked to a foodbank"""
        assert email_subscription.foodbank == foodbank
        assert whatsapp_subscription.foodbank == foodbank
        assert mobile_subscription.foodbank == foodbank
        assert webpush_subscription.foodbank == foodbank

    def test_device_id_truncation_safe(self, foodbank):
        """Test that short device IDs don't cause errors"""
        # Create a mobile subscription with a very short device_id
        short_device = MobileSubscriber.objects.create(
            foodbank=foodbank,
            device_id="abc",  # Only 3 characters
            platform="iOS",
            timezone="Europe/London",
            locale="en-GB",
            app_version="1.0.0",
            os_version="17.0",
            device_model="iPhone",
            sub_type="foodbank"
        )
        assert short_device.device_id == "abc"
        
        # Create one with exactly 20 characters
        exact_device = MobileSubscriber.objects.create(
            foodbank=foodbank,
            device_id="12345678901234567890",  # Exactly 20
            platform="Android",
            timezone="Europe/London",
            locale="en-GB",
            app_version="1.0.0",
            os_version="17.0",
            device_model="Pixel",
            sub_type="foodbank"
        )
        assert exact_device.device_id == "12345678901234567890"

    def test_endpoint_truncation_safe(self, foodbank):
        """Test that short endpoints don't cause errors"""
        # Create a WebPush subscription with a very short endpoint
        short_endpoint = WebPushSubscription.objects.create(
            foodbank=foodbank,
            endpoint="https://short.url",  # Short URL
            p256dh="test-key",
            auth="test-auth",
            browser="Firefox"
        )
        assert short_endpoint.endpoint == "https://short.url"

