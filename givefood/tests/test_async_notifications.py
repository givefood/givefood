import pytest
from unittest.mock import patch, MagicMock
from givefood.func import (
    send_firebase_notification_async,
    send_webpush_notification_async,
    send_whatsapp_notification_async,
    foodbank_article_crawl_async,
    decache_async,
)


class TestAsyncTaskPriorities:
    """Test that async task wrappers have correct priorities."""

    def test_decache_async_priority(self):
        assert decache_async.priority == 20

    def test_foodbank_article_crawl_async_priority(self):
        assert foodbank_article_crawl_async.priority == 30

    def test_send_firebase_notification_async_priority(self):
        assert send_firebase_notification_async.priority == 10

    def test_send_webpush_notification_async_priority(self):
        assert send_webpush_notification_async.priority == 10

    def test_send_whatsapp_notification_async_priority(self):
        assert send_whatsapp_notification_async.priority == 10

    def test_article_crawl_higher_priority_than_decache(self):
        assert foodbank_article_crawl_async.priority > decache_async.priority

    def test_decache_higher_priority_than_notifications(self):
        assert decache_async.priority > send_firebase_notification_async.priority
        assert decache_async.priority > send_webpush_notification_async.priority
        assert decache_async.priority > send_whatsapp_notification_async.priority


@pytest.mark.django_db
class TestAsyncTaskCallsDelegates:
    """Test that async task wrappers correctly delegate to their sync counterparts."""

    def _create_foodbank(self):
        from givefood.models import Foodbank
        foodbank = Foodbank(
            name="Test Bank",
            slug="test-bank",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
            contact_email="test@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        return foodbank

    def _create_need(self, foodbank):
        from givefood.models import FoodbankChange
        need = FoodbankChange(foodbank=foodbank, change_text="Pasta\nRice")
        need.save(do_foodbank_save=False, do_translate=False)
        return need

    @patch('givefood.func.send_firebase_notification')
    def test_send_firebase_notification_async_calls_sync(self, mock_send):
        foodbank = self._create_foodbank()
        need = self._create_need(foodbank)

        send_firebase_notification_async.call(need.need_id_str)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0].need_id_str == need.need_id_str

    @patch('givefood.func.send_webpush_notification')
    def test_send_webpush_notification_async_calls_sync(self, mock_send):
        foodbank = self._create_foodbank()
        need = self._create_need(foodbank)

        send_webpush_notification_async.call(need.need_id_str)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0].need_id_str == need.need_id_str

    @patch('givefood.func.send_whatsapp_notification')
    def test_send_whatsapp_notification_async_calls_sync(self, mock_send):
        foodbank = self._create_foodbank()
        need = self._create_need(foodbank)

        send_whatsapp_notification_async.call(need.need_id_str)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0].need_id_str == need.need_id_str

    @patch('givefood.func.foodbank_article_crawl')
    def test_foodbank_article_crawl_async_calls_sync(self, mock_crawl):
        foodbank = self._create_foodbank()

        foodbank_article_crawl_async.call(foodbank.slug)
        mock_crawl.assert_called_once()
        assert mock_crawl.call_args[0][0].slug == "test-bank"
