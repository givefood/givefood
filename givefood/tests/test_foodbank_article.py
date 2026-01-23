"""Tests for FoodbankArticle model methods."""
import pytest
from django.utils import timezone

from givefood.models import Foodbank, FoodbankArticle


@pytest.mark.django_db
class TestFoodbankArticleTitleCapitalised:
    """Test the title_captialised() method."""

    @pytest.fixture
    def foodbank(self):
        """Create a test foodbank."""
        foodbank = Foodbank(
            name='Test Food Bank',
            slug='test-food-bank',
            address='123 Test St',
            postcode='TE1 1ST',
            lat_lng='51.5074,-0.1278',
            country='England',
            url='https://example.com',
            shopping_list_url='https://example.com/needs',
            contact_email='test@example.com',
            edited=timezone.now(),
            is_closed=False
        )
        foodbank.latitude = 51.5074
        foodbank.longitude = -0.1278
        foodbank.save(do_geoupdate=False)
        return foodbank

    @pytest.fixture
    def article(self, foodbank):
        """Create a test article."""
        return FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='test article title',
            url='https://example.com/article1',
            published_date=timezone.now(),
            featured=False
        )

    def test_basic_capitalisation(self, foodbank):
        """Test that basic capitalisation works."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='test article title',
            url='https://example.com/basic-cap',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'Test Article Title'

    def test_uk_not_capitalised(self, foodbank):
        """Test that UK stays as UK, not Uk."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='food bank in uk opens',
            url='https://example.com/uk-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'Food Bank In UK Opens'

    def test_agm_not_capitalised(self, foodbank):
        """Test that AGM stays as AGM, not Agm."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='food bank agm announced',
            url='https://example.com/agm-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'Food Bank AGM Announced'

    def test_ceo_not_capitalised(self, foodbank):
        """Test that CEO stays as CEO, not Ceo."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='new ceo joins food bank',
            url='https://example.com/ceo-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'New CEO Joins Food Bank'

    def test_ni_not_capitalised(self, foodbank):
        """Test that NI (Northern Ireland) stays as NI, not Ni."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='food banks in ni need help',
            url='https://example.com/ni-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'Food Banks In NI Need Help'

    def test_gck_not_capitalised(self, foodbank):
        """Test that GCK stays as GCK, not Gck."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='gck donates to food bank',
            url='https://example.com/gck-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'GCK Donates To Food Bank'

    def test_bbc_not_capitalised(self, foodbank):
        """Test that BBC stays as BBC, not Bbc."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='bbc covers food bank story',
            url='https://example.com/bbc-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'BBC Covers Food Bank Story'

    def test_trailing_period_removed(self, foodbank):
        """Test that trailing period is removed."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='food bank opens today.',
            url='https://example.com/period-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'Food Bank Opens Today'

    def test_trailing_multiple_periods_removed(self, foodbank):
        """Test that trailing multiple periods are removed."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='food bank opens today...',
            url='https://example.com/periods-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'Food Bank Opens Today'

    def test_double_spaces_replaced(self, foodbank):
        """Test that double spaces are replaced with a single space."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='food bank  opens today',
            url='https://example.com/double-space-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'Food Bank Opens Today'

    def test_multiple_consecutive_spaces_replaced(self, foodbank):
        """Test that multiple consecutive spaces (more than two) are replaced with a single space."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='food bank   opens    today',
            url='https://example.com/multi-space-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'Food Bank Opens Today'

    def test_combined_improvements(self, foodbank):
        """Test multiple improvements combined: UK, trailing period, double spaces."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='bbc covers uk  food bank story.',
            url='https://example.com/combined-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'BBC Covers UK Food Bank Story'

    def test_multiple_acronyms(self, foodbank):
        """Test multiple acronyms in one title."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='bbc and uk ceo meet at agm',
            url='https://example.com/multi-acronym-test',
            published_date=timezone.now(),
        )
        assert article.title_captialised() == 'BBC And UK CEO Meet At AGM'

    def test_mid_sentence_period_not_removed(self, foodbank):
        """Test that periods in the middle of the title are not removed."""
        article = FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='dr. smith opens food bank',
            url='https://example.com/mid-period-test',
            published_date=timezone.now(),
        )
        # Only trailing period should be removed
        assert article.title_captialised() == 'Dr. Smith Opens Food Bank'
