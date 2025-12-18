"""Tests for the foodbank partial edit forms (address, phone, email, fsa_id)."""
import pytest
from django.urls import reverse

from givefood.forms import FoodbankAddressForm, FoodbankPhoneForm, FoodbankEmailForm, FoodbankFsaIdForm
from givefood.models import Foodbank


@pytest.mark.django_db
class TestFoodbankAddressForm:
    """Test the foodbank address edit functionality."""

    def test_foodbank_address_form_url_resolves(self):
        """Test that the URL pattern resolves correctly."""
        url = reverse('admin:foodbank_address_edit', kwargs={'slug': 'test-foodbank'})
        assert url == '/admin/foodbank/test-foodbank/edit/address/'

    def test_foodbank_address_form_has_correct_fields(self):
        """Test that the form has only the address fields."""
        form = FoodbankAddressForm()
        expected_fields = ['address', 'postcode', 'lat_lng']
        assert list(form.fields.keys()) == expected_fields

    def test_foodbank_address_form_inherits_from_model_form(self):
        """Test that FoodbankAddressForm uses the Foodbank model."""
        form = FoodbankAddressForm()
        assert form._meta.model == Foodbank


@pytest.mark.django_db
class TestFoodbankPhoneForm:
    """Test the foodbank phone edit functionality."""

    def test_foodbank_phone_form_url_resolves(self):
        """Test that the URL pattern resolves correctly."""
        url = reverse('admin:foodbank_phone_edit', kwargs={'slug': 'test-foodbank'})
        assert url == '/admin/foodbank/test-foodbank/edit/phone/'

    def test_foodbank_phone_form_has_correct_fields(self):
        """Test that the form has only the phone fields."""
        form = FoodbankPhoneForm()
        expected_fields = ['phone_number', 'secondary_phone_number', 'delivery_phone_number']
        assert list(form.fields.keys()) == expected_fields

    def test_foodbank_phone_form_inherits_from_model_form(self):
        """Test that FoodbankPhoneForm uses the Foodbank model."""
        form = FoodbankPhoneForm()
        assert form._meta.model == Foodbank


@pytest.mark.django_db
class TestFoodbankEmailForm:
    """Test the foodbank email edit functionality."""

    def test_foodbank_email_form_url_resolves(self):
        """Test that the URL pattern resolves correctly."""
        url = reverse('admin:foodbank_email_edit', kwargs={'slug': 'test-foodbank'})
        assert url == '/admin/foodbank/test-foodbank/edit/email/'

    def test_foodbank_email_form_has_correct_fields(self):
        """Test that the form has only the email fields."""
        form = FoodbankEmailForm()
        expected_fields = ['contact_email', 'notification_email']
        assert list(form.fields.keys()) == expected_fields

    def test_foodbank_email_form_inherits_from_model_form(self):
        """Test that FoodbankEmailForm uses the Foodbank model."""
        form = FoodbankEmailForm()
        assert form._meta.model == Foodbank


@pytest.mark.django_db
class TestFoodbankFsaIdForm:
    """Test the foodbank FSA ID edit functionality."""

    def test_foodbank_fsa_id_form_url_resolves(self):
        """Test that the URL pattern resolves correctly."""
        url = reverse('admin:foodbank_fsa_id_edit', kwargs={'slug': 'test-foodbank'})
        assert url == '/admin/foodbank/test-foodbank/edit/fsa-id/'

    def test_foodbank_fsa_id_form_has_correct_fields(self):
        """Test that the form has only the fsa_id field."""
        form = FoodbankFsaIdForm()
        expected_fields = ['fsa_id']
        assert list(form.fields.keys()) == expected_fields

    def test_foodbank_fsa_id_form_inherits_from_model_form(self):
        """Test that FoodbankFsaIdForm uses the Foodbank model."""
        form = FoodbankFsaIdForm()
        assert form._meta.model == Foodbank
