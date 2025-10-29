import pytest
from unittest.mock import patch, Mock
from django.test import Client
from django.urls import reverse
from givefood.models import Foodbank, FoodbankDonationPoint, FoodbankChange, FoodbankLocation


@pytest.mark.django_db
class TestGeojsonView:
    """Test the geojson endpoint with .only() optimization"""

    def test_geojson_all_items_returns_valid_json(self, client):
        """
        Test that the geojson endpoint for all items returns valid JSON
        with empty database.
        """
        response = client.get(reverse('wfbn:geojson'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        data = response.json()
        assert 'type' in data
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert isinstance(data['features'], list)

        
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


    def test_donation_point_with_empty_opening_hours_no_preload_header(self, client):
        """Test that donation point with empty opening hours doesn't include Link preload header."""
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
        
        # Create a donation point with empty opening hours string
        donationpoint = FoodbankDonationPoint(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            name="Test Donation Point 3",
            slug="test-donation-point-3",
            address="789 Test Blvd",
            postcode="SW1A 1AA",
            opening_hours="   ",  # Empty/whitespace only opening hours
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


@pytest.mark.django_db
class TestFoodbankLocationMap:
    """Test the foodbank_location_map endpoint with boundary_geojson support"""

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_without_boundary(self, mock_get_cred, mock_requests_get, client):
        """Test that location map works without boundary_geojson."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_requests_get.return_value = mock_response
        
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
        
        # Create a location without boundary_geojson
        location = FoodbankLocation(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            foodbank_phone_number="",
            foodbank_email="test@example.com",
            name="Test Location",
            slug="test-location",
            address="123 Test St",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
            boundary_geojson=None,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Make request to location map
        url = reverse('wfbn-generic:foodbank_location_map', kwargs={
            'slug': foodbank.slug,
            'locslug': location.slug
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called
        assert mock_requests_get.called
        called_url = mock_requests_get.call_args[0][0]
        assert "center=51.5014,-0.1419" in called_url
        assert "zoom=15" in called_url
        assert "path=" not in called_url  # No boundary path

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_with_boundary(self, mock_get_cred, mock_requests_get, client):
        """Test that location map includes boundary_geojson as a path."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_requests_get.return_value = mock_response
        
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
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a location with boundary_geojson
        boundary_geojson = '{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-0.1419,51.5014],[-0.1420,51.5015],[-0.1418,51.5016],[-0.1419,51.5014]]]},"properties":{}}'
        location = FoodbankLocation(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            foodbank_phone_number="",
            foodbank_email="test@example.com",
            name="Test Location 2",
            slug="test-location-2",
            address="456 Test Ave",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
            boundary_geojson=boundary_geojson,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Make request to location map
        url = reverse('wfbn-generic:foodbank_location_map', kwargs={
            'slug': foodbank.slug,
            'locslug': location.slug
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with boundary path
        assert mock_requests_get.called
        called_url = mock_requests_get.call_args[0][0]
        assert "center=51.5014,-0.1419" in called_url
        assert "zoom=15" in called_url
        assert "path=" in called_url
        assert "fillcolor:0xf7a72333" in called_url  # Orange fill with transparency
        assert "color:0xf7a723ff" in called_url  # Orange border
        assert "weight:1" in called_url
        # Verify coordinates are in lat,lng format (reversed from GeoJSON lng,lat)
        assert "51.5014,-0.1419" in called_url
