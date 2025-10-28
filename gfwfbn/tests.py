"""
Tests for the gfwfbn (What Food Banks Need) app.
"""
import pytest
from django.test import Client
from django.urls import reverse
from givefood.models import Foodbank, FoodbankDonationPoint, FoodbankChange


@pytest.mark.django_db
class TestDonationPointPreloadHeaders:
    """Test preload headers for donation point pages."""

    def test_donation_point_with_opening_hours_has_preload_header(self, client):
        """Test that donation point with opening hours includes Link preload header."""
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
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a need for the food bank
        need = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Tinned Tomatoes, Pasta, Rice",
            published=True,
        )
        
        # Update the foodbank to reference the latest need
        foodbank.latest_need = need
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a donation point with opening hours
        donationpoint = FoodbankDonationPoint(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            name="Test Donation Point",
            slug="test-donation-point",
            address="123 Test St",
            postcode="SW1A 1AA",
            opening_hours="Mon-Fri 9am-5pm",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
        )
        donationpoint.save(do_geoupdate=False, do_foodbank_resave=False, do_photo_update=False)
        
        # Make request to donation point page
        url = reverse('wfbn:foodbank_donationpoint', kwargs={
            'slug': foodbank.slug,
            'dpslug': donationpoint.slug
        })
        response = client.get(url)
        
        # Check that response is successful
        assert response.status_code == 200
        
        # Check that Link header is present with correct format
        assert 'Link' in response
        
        # Verify the Link header content
        expected_url = reverse('wfbn:foodbank_donationpoint_openinghours', kwargs={
            'slug': foodbank.slug,
            'dpslug': donationpoint.slug
        })
        expected_header = f"<{expected_url}>; rel=preload; as=fetch"
        assert response['Link'] == expected_header

    def test_donation_point_without_opening_hours_no_preload_header(self, client):
        """Test that donation point without opening hours doesn't include Link preload header."""
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
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a need for the food bank
        need = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Tinned Tomatoes, Pasta, Rice",
            published=True,
        )
        
        # Update the foodbank to reference the latest need
        foodbank.latest_need = need
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a donation point without opening hours
        donationpoint = FoodbankDonationPoint(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            name="Test Donation Point 2",
            slug="test-donation-point-2",
            address="456 Test Ave",
            postcode="SW1A 1AA",
            opening_hours=None,  # No opening hours
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
        )
        donationpoint.save(do_geoupdate=False, do_foodbank_resave=False, do_photo_update=False)
        
        # Make request to donation point page
        url = reverse('wfbn:foodbank_donationpoint', kwargs={
            'slug': foodbank.slug,
            'dpslug': donationpoint.slug
        })
        response = client.get(url)
        
        # Check that response is successful
        assert response.status_code == 200
        
        # Check that Link header is NOT present
        assert 'Link' not in response
