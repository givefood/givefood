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
