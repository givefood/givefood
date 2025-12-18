import pytest
from unittest.mock import patch, call
from django.utils.translation import activate
from givefood.models import Foodbank, FoodbankChange, FoodbankChangeTranslation


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


@pytest.mark.django_db
class TestFoodbankChangeGetText:
    """Test that FoodbankChange.get_text() handles missing translations."""

    @patch('givefood.models.translate_need_async')
    def test_get_text_fallback_to_english_when_translation_missing(self, mock_translate):
        """Test that get_text falls back to English when translation doesn't exist."""
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank Fallback",
            slug="test-food-bank-fallback",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://testfallback.example.com",
            shopping_list_url="https://testfallback.example.com/shopping",
            contact_email="testfallback@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need with English text only (no translation)
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice",
            excess_change_text="Bread\nMilk",
            published=True,
        )
        need.save(do_translate=False)

        # Activate a non-English language (e.g., Spanish)
        activate('es')

        # Should fall back to English text without raising UnboundLocalError
        change_text = need.get_change_text()
        assert change_text == "Tinned Tomatoes\nPasta\nRice"

        excess_text = need.get_excess_text()
        assert excess_text == "Bread\nMilk"

        # Reset to English
        activate('en')

    @patch('givefood.models.translate_need_async')
    def test_get_text_uses_translation_when_available(self, mock_translate):
        """Test that get_text uses translation when it exists."""
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank Translation",
            slug="test-food-bank-translation",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://testtranslation.example.com",
            shopping_list_url="https://testtranslation.example.com/shopping",
            contact_email="testtranslation@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice",
            excess_change_text="Bread\nMilk",
            published=True,
        )
        need.save(do_translate=False)

        # Create a translation for Spanish
        translation = FoodbankChangeTranslation(
            need=need,
            language="es",
            change_text="Tomates enlatados\nPasta\nArroz",
            excess_change_text="Pan\nLeche",
        )
        translation.save()

        # Activate Spanish
        activate('es')

        # Should use Spanish translation
        change_text = need.get_change_text()
        assert change_text == "Tomates enlatados\nPasta\nArroz"

        excess_text = need.get_excess_text()
        assert excess_text == "Pan\nLeche"

        # Reset to English
        activate('en')

    @patch('givefood.models.translate_need_async')
    def test_get_text_returns_english_when_language_is_english(self, mock_translate):
        """Test that get_text returns English text when language is English."""
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank English",
            slug="test-food-bank-english",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://testenglish.example.com",
            shopping_list_url="https://testenglish.example.com/shopping",
            contact_email="testenglish@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice",
            excess_change_text="Bread\nMilk",
            published=True,
        )
        need.save(do_translate=False)

        # Activate English
        activate('en')

        # Should return English text
        change_text = need.get_change_text()
        assert change_text == "Tinned Tomatoes\nPasta\nRice"

        excess_text = need.get_excess_text()
        assert excess_text == "Bread\nMilk"

    @patch('givefood.models.translate_need_async')
    def test_get_text_uses_prefetched_translations(self, mock_translate):
        """Test that get_text uses prefetched translations when available to avoid N+1 queries."""
        from django.db.models import Prefetch

        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank Prefetch",
            slug="test-food-bank-prefetch",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://testprefetch.example.com",
            shopping_list_url="https://testprefetch.example.com/shopping",
            contact_email="testprefetch@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta\nRice",
            excess_change_text="Bread\nMilk",
            published=True,
        )
        need.save(do_translate=False)

        # Create a translation for Spanish
        translation = FoodbankChangeTranslation(
            need=need,
            language="es",
            change_text="Tomates enlatados\nPasta\nArroz",
            excess_change_text="Pan\nLeche",
        )
        translation.save()

        # Activate Spanish
        activate('es')

        # Fetch the need with prefetched translations
        need_with_prefetch = FoodbankChange.objects.prefetch_related(
            Prefetch("foodbankchangetranslation_set", queryset=FoodbankChangeTranslation.objects.all())
        ).get(pk=need.pk)

        # Should use the prefetched Spanish translation without making an additional query
        change_text = need_with_prefetch.get_change_text()
        assert change_text == "Tomates enlatados\nPasta\nArroz"

        excess_text = need_with_prefetch.get_excess_text()
        assert excess_text == "Pan\nLeche"

        # Reset to English
        activate('en')
