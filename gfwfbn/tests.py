import pytest
from unittest.mock import patch, Mock
from django.test import Client
from django.urls import reverse
from givefood.models import Foodbank, FoodbankDonationPoint, FoodbankChange, FoodbankLocation


@pytest.fixture
def create_test_foodbank():
    """Factory fixture for creating test foodbanks with default values."""
    def _create_foodbank(name="Test Food Bank", slug="test-food-bank", **kwargs):
        defaults = {
            "address": "Test Address",
            "postcode": "SW1A 1AA",
            "country": "England",
            "lat_lng": "51.5014,-0.1419",
            "latitude": 51.5014,
            "longitude": -0.1419,
            "network": "Independent",
            "url": "https://test.example.com",
            "shopping_list_url": "https://test.example.com/shopping",
        }
        defaults.update(kwargs)
        foodbank = Foodbank(name=name, slug=slug, **defaults)
        foodbank.save(do_geoupdate=False, do_decache=False)
        return foodbank
    return _create_foodbank


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
        mock_response.status_code = 200
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
        url = reverse('wfbn:foodbank_location_map', kwargs={
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
        called_params = mock_requests_get.call_args[1]['params']
        assert called_url == "https://maps.googleapis.com/maps/api/staticmap"
        # Convert params list to dict for easier checking
        params_dict = dict(called_params)
        assert params_dict['center'] == "51.5014,-0.1419"
        assert params_dict['zoom'] == 15
        assert params_dict['language'] == "en"  # Check language parameter
        assert 'path' not in params_dict  # No boundary path

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_with_boundary(self, mock_get_cred, mock_requests_get, client):
        """Test that location map includes boundary_geojson as a path."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
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
        url = reverse('wfbn:foodbank_location_map', kwargs={
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
        called_params = mock_requests_get.call_args[1]['params']
        assert called_url == "https://maps.googleapis.com/maps/api/staticmap"
        # Convert params list to dict for easier checking
        params_dict = dict(called_params)
        assert params_dict['center'] == "51.5014,-0.1419"
        assert params_dict['zoom'] == 12  # Zoom 12 when boundary exists
        assert params_dict['language'] == "en"  # Check language parameter
        assert 'path' in params_dict
        path_param = params_dict['path']
        assert "fillcolor:0xf7a72333" in path_param  # Orange fill with transparency
        assert "color:0xf7a723ff" in path_param  # Orange border
        assert "weight:1" in path_param
        # Verify coordinates are in lat,lng format with reduced precision (4 decimal places)
        # The coordinates should be rounded to 4 decimal places
        assert "51.5014,-0.1419" in path_param or "51.5014,-0.1420" in path_param

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_with_large_boundary_downsamples(self, mock_get_cred, mock_requests_get, client):
        """Test that location map downsamples large boundary polygons to avoid URL length issues."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response
        
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
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a location with a large boundary_geojson (150 points)
        # Generate a polygon with many points to trigger downsampling
        coords = []
        for i in range(150):
            angle = (i / 150.0) * 2 * 3.14159
            lng = -0.1419 + 0.01 * (0.5 + 0.5 * (angle / 6.28))
            lat = 51.5014 + 0.01 * (0.5 + 0.5 * ((angle + 1.57) / 6.28))
            coords.append([lng, lat])
        coords.append(coords[0])  # Close the polygon
        
        boundary_geojson = '{"type":"Feature","geometry":{"type":"Polygon","coordinates":[' + str(coords).replace("'", '"') + ']},"properties":{}}'
        location = FoodbankLocation(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            foodbank_phone_number="",
            foodbank_email="test@example.com",
            name="Test Location 3",
            slug="test-location-3",
            address="789 Test Blvd",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
            boundary_geojson=boundary_geojson,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Make request to location map
        url = reverse('wfbn:foodbank_location_map', kwargs={
            'slug': foodbank.slug,
            'locslug': location.slug
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with downsampled boundary
        assert mock_requests_get.called
        called_url = mock_requests_get.call_args[0][0]
        called_params = mock_requests_get.call_args[1]['params']
        assert called_url == "https://maps.googleapis.com/maps/api/staticmap"
        # Convert params list to dict for easier checking
        params_dict = dict(called_params)
        assert params_dict['language'] == "en"  # Check language parameter
        
        # Count the number of pipe-separated coordinate pairs in the path
        if 'path' in params_dict:
            path_param = params_dict['path']
            # Count pipes after the style parameters
            coords_section = path_param.split("weight:1|", 1)[1] if "weight:1|" in path_param else ""
            num_coords = len(coords_section.split("|"))
            # Should be downsampled to ~100 points (original was 151)
            assert num_coords <= 105, f"Expected ~100 coords, got {num_coords}"
            assert num_coords >= 50, f"Too few coords: {num_coords}"


@pytest.mark.django_db
class TestFoodbankMapSizes:
    """Test the foodbank_map endpoint with different sizes"""

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_foodbank_map_size_300(self, mock_get_cred, mock_requests_get, client):
        """Test that foodbank map with size 300 returns 150x150 at scale 2."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
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
        
        # Make request with size 300
        url = reverse('wfbn:foodbank_map_size', kwargs={
            'slug': foodbank.slug,
            'size': 300
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with correct size and scale
        assert mock_requests_get.called
        called_params = mock_requests_get.call_args[1]['params']
        params_dict = dict(called_params)
        assert params_dict['size'] == "150x150"
        assert params_dict['scale'] == 2

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_foodbank_map_size_600(self, mock_get_cred, mock_requests_get, client):
        """Test that foodbank map with size 600 returns 600x400 at scale 1."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
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
        
        # Make request with size 600
        url = reverse('wfbn:foodbank_map_size', kwargs={
            'slug': foodbank.slug,
            'size': 600
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with correct size and scale
        assert mock_requests_get.called
        called_params = mock_requests_get.call_args[1]['params']
        params_dict = dict(called_params)
        assert params_dict['size'] == "600x400"
        assert params_dict['scale'] == 1

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_foodbank_map_size_1080(self, mock_get_cred, mock_requests_get, client):
        """Test that foodbank map with size 1080 returns 540x360 at scale 2."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response
        
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
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Make request with size 1080
        url = reverse('wfbn:foodbank_map_size', kwargs={
            'slug': foodbank.slug,
            'size': 1080
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with correct size and scale
        assert mock_requests_get.called
        called_params = mock_requests_get.call_args[1]['params']
        params_dict = dict(called_params)
        assert params_dict['size'] == "540x360"
        assert params_dict['scale'] == 2

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_foodbank_map_default_size(self, mock_get_cred, mock_requests_get, client):
        """Test that foodbank map.png (default) returns 600x400 at scale 1."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response
        
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
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Make request with default size (map.png)
        url = reverse('wfbn:foodbank_map', kwargs={
            'slug': foodbank.slug,
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with correct size and scale
        assert mock_requests_get.called
        called_params = mock_requests_get.call_args[1]['params']
        params_dict = dict(called_params)
        assert params_dict['size'] == "600x400"
        assert params_dict['scale'] == 1

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_foodbank_map_invalid_size(self, mock_get_cred, mock_requests_get, client):
        """Test that foodbank map with invalid size returns 400."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 5",
            slug="test-food-bank-5",
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
        
        # Make request with invalid size
        url = reverse('wfbn:foodbank_map_size', kwargs={
            'slug': foodbank.slug,
            'size': 999
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 400


@pytest.mark.django_db
class TestFoodbankLocationMapSizes:
    """Test the foodbank_location_map endpoint with different sizes"""

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_size_300(self, mock_get_cred, mock_requests_get, client):
        """Test that location map with size 300 returns 150x150 at scale 2."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
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
        
        # Create a location
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
        
        # Make request with size 300
        url = reverse('wfbn:foodbank_location_map_size', kwargs={
            'slug': foodbank.slug,
            'locslug': location.slug,
            'size': 300
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with correct size and scale
        assert mock_requests_get.called
        called_params = mock_requests_get.call_args[1]['params']
        params_dict = dict(called_params)
        assert params_dict['size'] == "150x150"
        assert params_dict['scale'] == 2

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_size_600(self, mock_get_cred, mock_requests_get, client):
        """Test that location map with size 600 returns 600x400 at scale 1."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
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
        
        # Create a location
        location = FoodbankLocation(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            foodbank_phone_number="",
            foodbank_email="test@example.com",
            name="Test Location 2",
            slug="test-location-2",
            address="123 Test St",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
            boundary_geojson=None,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Make request with size 600
        url = reverse('wfbn:foodbank_location_map_size', kwargs={
            'slug': foodbank.slug,
            'locslug': location.slug,
            'size': 600
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with correct size and scale
        assert mock_requests_get.called
        called_params = mock_requests_get.call_args[1]['params']
        params_dict = dict(called_params)
        assert params_dict['size'] == "600x400"
        assert params_dict['scale'] == 1

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_size_1080(self, mock_get_cred, mock_requests_get, client):
        """Test that location map with size 1080 returns 540x360 at scale 2."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response
        
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
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a location
        location = FoodbankLocation(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            foodbank_phone_number="",
            foodbank_email="test@example.com",
            name="Test Location 3",
            slug="test-location-3",
            address="123 Test St",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
            boundary_geojson=None,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Make request with size 1080
        url = reverse('wfbn:foodbank_location_map_size', kwargs={
            'slug': foodbank.slug,
            'locslug': location.slug,
            'size': 1080
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with correct size and scale
        assert mock_requests_get.called
        called_params = mock_requests_get.call_args[1]['params']
        params_dict = dict(called_params)
        assert params_dict['size'] == "540x360"
        assert params_dict['scale'] == 2

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_default_size(self, mock_get_cred, mock_requests_get, client):
        """Test that location map.png (default) returns 600x400 at scale 1."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response
        
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
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create a location
        location = FoodbankLocation(
            foodbank=foodbank,
            foodbank_name=foodbank.name,
            foodbank_slug=foodbank.slug,
            foodbank_network=foodbank.network,
            foodbank_phone_number="",
            foodbank_email="test@example.com",
            name="Test Location 4",
            slug="test-location-4",
            address="123 Test St",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
            boundary_geojson=None,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Make request with default size (map.png)
        url = reverse('wfbn:foodbank_location_map', kwargs={
            'slug': foodbank.slug,
            'locslug': location.slug
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'
        
        # Verify the Google Maps API was called with correct size and scale
        assert mock_requests_get.called
        called_params = mock_requests_get.call_args[1]['params']
        params_dict = dict(called_params)
        assert params_dict['size'] == "600x400"
        assert params_dict['scale'] == 1

    @patch('gfwfbn.views.requests.get')
    @patch('gfwfbn.views.get_cred')
    def test_location_map_invalid_size(self, mock_get_cred, mock_requests_get, client):
        """Test that location map with invalid size returns 400."""
        # Setup mocks
        mock_get_cred.return_value = "test_api_key"
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 5",
            slug="test-food-bank-5",
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
            foodbank_network=foodbank.network,
            foodbank_phone_number="",
            foodbank_email="test@example.com",
            name="Test Location 5",
            slug="test-location-5",
            address="123 Test St",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            country="England",
            boundary_geojson=None,
        )
        location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Make request with invalid size
        url = reverse('wfbn:foodbank_location_map_size', kwargs={
            'slug': foodbank.slug,
            'locslug': location.slug,
            'size': 999
        })
        response = client.get(url)
        
        # Verify response
        assert response.status_code == 400


@pytest.mark.django_db
class TestRSSFeeds:
    """Test the combined RSS feed functionality"""

    def test_site_wide_rss_returns_xml(self, client):
        """Test that the site-wide RSS feed returns valid XML."""
        response = client.get(reverse('wfbn:rss'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/xml'
        # Check for basic RSS structure
        content = response.content.decode('utf-8')
        assert '<?xml version="1.0"' in content
        assert '<rss version="2.0">' in content
        assert '<channel>' in content
        assert '<title>Give Food</title>' in content

    def test_foodbank_specific_rss_returns_xml(self, client):
        """Test that a food bank-specific RSS feed returns valid XML."""
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

        response = client.get(reverse('wfbn:foodbank_rss', kwargs={'slug': 'test-food-bank'}))
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/xml'
        # Check for basic RSS structure
        content = response.content.decode('utf-8')
        assert '<?xml version="1.0"' in content
        assert '<rss version="2.0">' in content
        assert '<channel>' in content
        # Should include foodbank name
        assert 'Test Food Bank' in content

    def test_foodbank_rss_with_needs(self, client):
        """Test that a food bank RSS feed includes needs when present."""
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

        # Create a need for the food bank
        need = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Tinned Tomatoes, Pasta, Rice",
            published=True,
        )

        response = client.get(reverse('wfbn:foodbank_rss', kwargs={'slug': 'test-food-bank-2'}))
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Should include items from the need
        assert '<item>' in content
        assert 'items requested at' in content

    def test_foodbank_rss_invalid_slug_returns_404(self, client):
        """Test that requesting RSS for non-existent food bank returns 404."""
        response = client.get(reverse('wfbn:foodbank_rss', kwargs={'slug': 'non-existent-foodbank'}))
        assert response.status_code == 404


@pytest.mark.django_db
class TestTurnstileFailureHandling:
    """Test the turnstile failure redirect and error handling"""

    def test_foodbank_with_turnstilefail_shows_error(self, client, create_test_foodbank):
        """Test that foodbank page with turnstilefail parameter shows error message."""
        # Create a food bank
        foodbank = create_test_foodbank()

        # Create a need for the food bank so subscribe form is shown
        need = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Tinned Tomatoes, Pasta, Rice",
            published=True,
        )
        
        # Update the foodbank to reference the latest need
        foodbank.latest_need = need
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Make request with turnstilefail parameter
        url = reverse('wfbn:foodbank', kwargs={'slug': 'test-food-bank'})
        response = client.get(url + '?turnstilefail=true&email=test@example.com')
        
        # Check that response is successful
        assert response.status_code == 200
        
        # Check that error message is present
        content = response.content.decode('utf-8')
        assert 'Sorry, the security check failed' in content
        
        # Check that email is pre-filled
        assert 'test@example.com' in content
        
    def test_foodbank_without_turnstilefail_no_error(self, client, create_test_foodbank):
        """Test that foodbank page without turnstilefail doesn't show error."""
        # Create a food bank
        foodbank = create_test_foodbank(name="Test Food Bank 2", slug="test-food-bank-2")

        # Create a need for the food bank
        need = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Tinned Tomatoes, Pasta, Rice",
            published=True,
        )
        
        # Update the foodbank to reference the latest need
        foodbank.latest_need = need
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Make request without turnstilefail parameter
        url = reverse('wfbn:foodbank', kwargs={'slug': 'test-food-bank-2'})
        response = client.get(url)
        
        # Check that response is successful
        assert response.status_code == 200
        
        # Check that error message is NOT present
        content = response.content.decode('utf-8')
        assert 'Sorry, the security check failed' not in content

    @patch('gfwfbn.views.validate_turnstile')
    def test_updates_subscribe_redirects_to_foodbank_on_turnstile_fail(self, mock_validate_turnstile, client, create_test_foodbank):
        """Test that updates view redirects to foodbank page when turnstile fails."""
        # Setup mock to return False (turnstile validation failed)
        mock_validate_turnstile.return_value = False
        
        # Create a food bank
        foodbank = create_test_foodbank(name="Test Food Bank 3", slug="test-food-bank-3")

        # Post to updates view with subscribe action
        url = reverse('wfbn:updates', kwargs={'slug': 'test-food-bank-3', 'action': 'subscribe'})
        response = client.post(url, {
            'email': 'test@example.com',
            'cf-turnstile-response': 'fake-token'
        })
        
        # Should redirect
        assert response.status_code == 302
        
        # Should redirect to foodbank page with turnstilefail parameter
        from urllib.parse import unquote
        expected_url = reverse('wfbn:foodbank', kwargs={'slug': 'test-food-bank-3'})
        assert response.url.startswith(expected_url)
        assert 'turnstilefail=true' in response.url
        assert 'email=test@example.com' in unquote(response.url)

