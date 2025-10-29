import pytest
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

    def test_geojson_foodbank_returns_valid_json(self, client):
        """
        Test that the geojson endpoint for a specific foodbank returns valid JSON.
        """
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
        
        response = client.get(reverse('wfbn:foodbank_geojson', kwargs={'slug': 'test-food-bank'}))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        data = response.json()
        assert 'type' in data
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert isinstance(data['features'], list)
        # Should have the foodbank feature
        assert len(data['features']) >= 1
        
    def test_geojson_location_returns_valid_json(self, client):
        """
        Test that the geojson endpoint for a specific location returns valid JSON
        with only that location's data.
        """
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
        
        # Create a location
        location = FoodbankLocation(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            name="Test Location",
            slug="test-location",
            address="Location Address",
            postcode="SW1A 2AA",
            lat_lng="51.5024,-0.1429",
            latitude=51.5024,
            longitude=-0.1429,
            country="England",
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        response = client.get(reverse('wfbn:foodbank_location_geojson', 
                                     kwargs={'slug': 'test-food-bank', 'locslug': 'test-location'}))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        data = response.json()
        assert 'type' in data
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert isinstance(data['features'], list)
        # Should have only the specific location (not the foodbank)
        assert len(data['features']) == 1
        
        # Verify the location is in the features
        location_features = [f for f in data['features'] if f['properties'].get('type') == 'l']
        assert len(location_features) == 1
        assert location_features[0]['properties']['name'] == 'Test Location'
        
    def test_geojson_location_not_found_returns_404(self, client):
        """
        Test that requesting geo.json for a non-existent location returns 404.
        """
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
        
        # Request geo.json for a non-existent location
        response = client.get(reverse('wfbn:foodbank_location_geojson', 
                                     kwargs={'slug': 'test-food-bank-2', 'locslug': 'non-existent-location'}))
        assert response.status_code == 404

        
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
