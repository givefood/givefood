"""Tests for the foodbank URLs edit form."""
import pytest
from django.urls import reverse

from givefood.forms import FoodbankUrlsForm


@pytest.mark.django_db
class TestFoodbankUrlsForm:
    """Test the foodbank URLs edit functionality."""

    def test_foodbank_urls_form_url_resolves(self):
        """Test that the URL pattern resolves correctly."""
        url = reverse('admin:foodbank_urls_edit', kwargs={'slug': 'test-foodbank'})
        assert url == '/admin/foodbank/test-foodbank/edit/urls/'

    def test_foodbank_urls_form_has_correct_fields(self):
        """Test that the form has only the URL fields."""
        form = FoodbankUrlsForm()
        expected_fields = ['url', 'shopping_list_url', 'rss_url', 'donation_points_url', 'locations_url', 'contacts_url']
        assert list(form.fields.keys()) == expected_fields

    def test_foodbank_urls_form_inherits_from_model_form(self):
        """Test that FoodbankUrlsForm uses the Foodbank model."""
        form = FoodbankUrlsForm()
        from givefood.models import Foodbank
        assert form._meta.model == Foodbank
