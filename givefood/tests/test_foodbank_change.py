import pytest
from unittest.mock import patch, call
from givefood.models import Foodbank, FoodbankChange


@pytest.mark.django_db
class TestFoodbankChangeTranslation:
    """Test that FoodbankChange triggers translation when published."""

    @patch('givefood.models.translate_need_async')
    def test_save_with_published_true_triggers_translation(self, mock_translate):
        """Test that saving a need with published=True triggers translation."""
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank",
            slug="test-food-bank",
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

        # Create a need with published=True
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice",
            published=True,
        )
        need.save()

        # Verify that translate_need_async.enqueue was called for non-English languages
        # The LANGUAGES setting should have multiple languages, we expect calls for each non-en language
        assert mock_translate.enqueue.called
        # Check that it was called with the need_id_str
        calls = mock_translate.enqueue.call_args_list
        # Should be called for each non-English language
        assert len(calls) > 0
        # Verify the need_id_str is passed in each call
        for call_args in calls:
            assert call_args[0][1] == str(need.need_id)

    @patch('givefood.models.translate_need_async')
    def test_save_with_published_false_does_not_trigger_translation(self, mock_translate):
        """Test that saving a need with published=False does not trigger translation."""
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 2",
            slug="test-food-bank-2",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test2.example.com",
            shopping_list_url="https://test2.example.com/shopping",
            contact_email="test2@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need with published=False
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice",
            published=False,
        )
        need.save()

        # Verify that translate_need_async.enqueue was NOT called
        assert not mock_translate.enqueue.called

    @patch('givefood.models.translate_need_async')
    def test_update_to_published_true_triggers_translation(self, mock_translate):
        """Test that updating a need to published=True triggers translation."""
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 3",
            slug="test-food-bank-3",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test3.example.com",
            shopping_list_url="https://test3.example.com/shopping",
            contact_email="test3@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need with published=False
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice",
            published=False,
        )
        need.save()

        # Reset mock to clear previous calls
        mock_translate.enqueue.reset_mock()

        # Update the need to published=True
        need.published = True
        need.save()

        # Verify that translate_need_async.enqueue was called
        assert mock_translate.enqueue.called
        calls = mock_translate.enqueue.call_args_list
        assert len(calls) > 0
        for call_args in calls:
            assert call_args[0][1] == str(need.need_id)

    @patch('givefood.models.translate_need_async')
    def test_save_with_do_translate_false_does_not_trigger_translation(self, mock_translate):
        """Test that saving with do_translate=False prevents translation even when published=True."""
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 4",
            slug="test-food-bank-4",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test4.example.com",
            shopping_list_url="https://test4.example.com/shopping",
            contact_email="test4@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need with published=True but explicitly pass do_translate=False
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice",
            published=True,
        )
        need.save(do_translate=False)

        # Verify that translate_need_async.enqueue was NOT called
        assert not mock_translate.enqueue.called

    @patch('givefood.models.translate_need_async')
    def test_save_without_foodbank_does_not_crash(self, mock_translate):
        """Test that saving a need without a foodbank doesn't crash."""
        # Create a need without a foodbank
        need = FoodbankChange(
            change_text="Tinned Tomatoes\nPasta\nRice",
            published=True,
        )
        need.save()

        # Should not crash, and translation might or might not be called
        # (depending on implementation - it's valid either way)
