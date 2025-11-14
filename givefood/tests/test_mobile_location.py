"""
Tests for is_mobile field on FoodbankLocation model
"""
import pytest
from django.test import Client
from givefood.models import Foodbank, FoodbankLocation


@pytest.mark.django_db
class TestMobileLocation:
    """Test the is_mobile field on FoodbankLocation"""

    def test_is_mobile_field_exists(self):
        """Test that FoodbankLocation has an is_mobile field"""
        # Check the field exists on the model
        assert hasattr(FoodbankLocation, 'is_mobile')
        
    def test_is_mobile_default_false(self):
        """Test that is_mobile defaults to False"""
        # Create a minimal foodbank and location
        foodbank = Foodbank(
            name='Test Foodbank',
            slug='test-foodbank',
            address='Test Address',
            postcode='SW1A 1AA',
            country='England',
            lat_lng='51.5074,-0.1278',
            latitude=51.5074,
            longitude=-0.1278,
            phone_number='01234567890',
            contact_email='test@example.com',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            network='Trussell Trust',
            is_closed=False,
        )
        foodbank.save(do_geoupdate=False)
        
        # Use save with do_geoupdate=False to avoid external API calls
        location = FoodbankLocation(
            foodbank=foodbank,
            name='Test Location',
            slug='test-location',
            lat_lng='51.5074,-0.1278',
            latitude=51.5074,
            longitude=-0.1278,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Check that is_mobile defaults to False
        assert location.is_mobile is False
        
    def test_is_mobile_can_be_set(self):
        """Test that is_mobile can be set to True"""
        # Create a minimal foodbank and location
        foodbank = Foodbank(
            name='Test Foodbank 2',
            slug='test-foodbank-2',
            address='Test Address',
            postcode='SW1A 1AA',
            country='England',
            lat_lng='51.5074,-0.1278',
            latitude=51.5074,
            longitude=-0.1278,
            phone_number='01234567890',
            contact_email='test2@example.com',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            network='Independent',
            is_closed=False,
        )
        foodbank.save(do_geoupdate=False)
        
        # Use save with do_geoupdate=False to avoid external API calls
        location = FoodbankLocation(
            foodbank=foodbank,
            name='Mobile Van',
            slug='mobile-van',
            lat_lng='51.5074,-0.1278',
            latitude=51.5074,
            longitude=-0.1278,
            is_mobile=True,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Check that is_mobile is True
        assert location.is_mobile is True
        
        # Retrieve from DB to ensure it persists
        location_from_db = FoodbankLocation.objects.get(slug='mobile-van')
        assert location_from_db.is_mobile is True
