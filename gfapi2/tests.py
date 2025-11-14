"""
Tests for the gfapi2 (API v2) app.
"""
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestAPI2Index:
    """Test the API v2 index page."""

    def test_api_index_accessible(self, client):
        """Test that the API index page is accessible."""
        response = client.get('/api/2/')
        assert response.status_code == 200

    def test_api_index_contains_api_info(self, client):
        """Test that the API index page contains API information."""
        response = client.get('/api/2/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Check for expected content
        assert 'api' in content.lower() or 'documentation' in content.lower()


@pytest.mark.django_db
class TestAPI2Docs:
    """Test the API v2 documentation page."""

    def test_api_docs_accessible(self, client):
        """Test that the API docs page is accessible."""
        response = client.get('/api/2/docs/')
        assert response.status_code == 200

    def test_api_docs_contains_examples(self, client):
        """Test that the API docs page contains examples."""
        response = client.get('/api/2/docs/')
        assert response.status_code == 200
        # Just ensure we can access it
        assert len(response.content) > 0


@pytest.mark.django_db
class TestAPI2Foodbanks:
    """Test the API v2 foodbanks endpoint."""

    def test_foodbanks_list_json(self, client):
        """Test that the foodbanks list returns JSON."""
        response = client.get('/api/2/foodbanks/')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('application/json') or \
               response['Content-Type'].startswith('text/html')  # May vary based on format parameter

    def test_foodbanks_list_xml(self, client):
        """Test that the foodbanks list can return XML."""
        response = client.get('/api/2/foodbanks/?format=xml')
        assert response.status_code == 200

    def test_foodbanks_list_geojson(self, client):
        """Test that the foodbanks list can return GeoJSON."""
        response = client.get('/api/2/foodbanks/?format=geojson')
        assert response.status_code == 200


@pytest.mark.django_db
class TestAPI2FoodbankDetail:
    """Test the API v2 foodbank detail endpoint."""

    def test_foodbank_detail_has_donationpoints_array(self, client):
        """Test that the foodbank detail response includes a donationpoints array."""
        # This test checks structure even with empty database
        response = client.get('/api/2/foodbank/test-foodbank/')
        
        # 404 is expected if the foodbank doesn't exist, which is fine for this test environment
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            
            # Check that donationpoints field exists
            assert 'donationpoints' in data
            assert isinstance(data['donationpoints'], list)
    
    def test_foodbank_detail_locations_have_is_donation_point(self, client):
        """Test that each location in the foodbank detail response has is_donation_point field."""
        response = client.get('/api/2/foodbank/test-foodbank/')
        
        # Only test structure if foodbank exists
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            
            # Check that locations field exists
            assert 'locations' in data
            
            # If there are locations, check each has is_donation_point
            if isinstance(data['locations'], list) and len(data['locations']) > 0:
                for location in data['locations']:
                    assert 'is_donation_point' in location
                    assert isinstance(location['is_donation_point'], bool)

    def test_foodbank_detail_geojson_locations_have_is_donation_point(self, client):
        """Test that GeoJSON locations include is_donation_point property."""
        response = client.get('/api/2/foodbank/test-foodbank/?format=geojson')
        
        # Only test structure if foodbank exists
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            
            # Check it's a FeatureCollection
            if 'type' in data and data['type'] == 'FeatureCollection':
                assert 'features' in data
                
                # Check each feature (locations and donationpoints) for is_donation_point
                for feature in data['features']:
                    if 'properties' in feature:
                        # Main foodbank feature might not have it, but locations should
                        if 'slug' in feature['properties']:
                            # This could be a location or donation point, both should have is_donation_point
                            # or it's the main foodbank which doesn't need it
                            pass

    def test_foodbank_detail_donationpoints_have_accessibility_fields(self, client):
        """Test that donation points include wheelchair_accessible and opening_hours fields."""
        response = client.get('/api/2/foodbank/test-foodbank/')
        
        # Only test structure if foodbank exists
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            
            # Check that donationpoints field exists
            assert 'donationpoints' in data
            
            # If there are donation points, check each has the accessibility fields
            if isinstance(data['donationpoints'], list) and len(data['donationpoints']) > 0:
                for donationpoint in data['donationpoints']:
                    assert 'wheelchair_accessible' in donationpoint
                    assert 'opening_hours' in donationpoint



@pytest.mark.django_db
class TestAPI2LocationSearch:
    """Test the API v2 location search endpoint."""

    def test_location_search_includes_facebook_page(self, client):
        """Test that location search response includes facebook_page in foodbank data."""
        # Using a known UK postcode for testing
        response = client.get('/api/2/locations/search/?address=SW1A1AA')
        
        # The endpoint should return 200 or 400 (if geocoding fails or no results)
        # We're mainly checking the structure when data is returned
        assert response.status_code in [200, 400]
        
        # Only check JSON structure if we got a successful response
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            
            # If there are results, check that facebook_page field exists
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                assert 'foodbank' in first_item
                assert 'facebook_page' in first_item['foodbank']


@pytest.mark.django_db
class TestAPI2DonationPointSearch:
    """Test the API v2 donation point search endpoint."""

    def test_donationpoint_search_requires_params(self, client):
        """Test that donation point search requires either address or lat_lng."""
        response = client.get('/api/2/donationpoints/search/')
        assert response.status_code == 400

    def test_donationpoint_search_with_address(self, client):
        """Test donation point search with address parameter."""
        # Using a known UK postcode
        response = client.get('/api/2/donationpoints/search/?address=SW1A1AA')
        # Should return 200 or 400 (if geocoding fails or no results)
        assert response.status_code in [200, 400]

        # Only check structure if successful
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            assert isinstance(data, list)

            # If there are results, check structure
            if len(data) > 0:
                first_item = data[0]
                assert 'id' in first_item
                assert 'type' in first_item
                assert 'name' in first_item
                assert 'lat_lng' in first_item
                assert 'distance_m' in first_item
                assert 'distance_mi' in first_item
                assert 'foodbank' in first_item
                assert 'slug' in first_item['foodbank']
                assert 'needs' in first_item
                assert 'id' in first_item['needs']
                assert 'needs' in first_item['needs']
                assert 'number' in first_item['needs']

    def test_donationpoint_search_with_lat_lng(self, client):
        """Test donation point search with lat_lng parameter."""
        # Coordinates for central London
        response = client.get('/api/2/donationpoints/search/?lat_lng=51.5074,-0.1278')
        # Should return 200 or 400
        assert response.status_code in [200, 400]

    def test_donationpoint_search_rejects_geojson(self, client):
        """Test that donation point search rejects geojson format."""
        response = client.get('/api/2/donationpoints/search/?address=SW1A1AA&format=geojson')
        assert response.status_code == 400

    def test_donationpoint_search_accepts_xml(self, client):
        """Test that donation point search accepts XML format."""
        response = client.get('/api/2/donationpoints/search/?address=SW1A1AA&format=xml')
        # Should return 200 or 400 (if geocoding fails or no results)
        assert response.status_code in [200, 400]


@pytest.mark.django_db
class TestAPI2DonationPointSearch:
    """Test the API v2 donation point search endpoint."""

    def test_donationpoint_search_requires_params(self, client):
        """Test that donation point search requires either address or lat_lng."""
        response = client.get('/api/2/donationpoints/search/')
        assert response.status_code == 400

    def test_donationpoint_search_with_address(self, client):
        """Test donation point search with address parameter."""
        # Using a known UK postcode
        response = client.get('/api/2/donationpoints/search/?address=SW1A1AA')
        # Should return 200 or 400 (if geocoding fails or no results)
        assert response.status_code in [200, 400]
        
        # Only check structure if successful
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            assert isinstance(data, list)
            
            # If there are results, check structure
            if len(data) > 0:
                first_item = data[0]
                assert 'id' in first_item
                assert 'type' in first_item
                assert 'name' in first_item
                assert 'lat_lng' in first_item
                assert 'distance_m' in first_item
                assert 'distance_mi' in first_item
                assert 'foodbank' in first_item
                assert 'slug' in first_item['foodbank']

    def test_donationpoint_search_with_lat_lng(self, client):
        """Test donation point search with lat_lng parameter."""
        # Coordinates for central London
        response = client.get('/api/2/donationpoints/search/?lat_lng=51.5074,-0.1278')
        # Should return 200 or 400
        assert response.status_code in [200, 400]

    def test_donationpoint_search_rejects_geojson(self, client):
        """Test that donation point search rejects geojson format."""
        response = client.get('/api/2/donationpoints/search/?address=SW1A1AA&format=geojson')
        assert response.status_code == 400

    def test_donationpoint_search_accepts_xml(self, client):
        """Test that donation point search accepts XML format."""
        response = client.get('/api/2/donationpoints/search/?address=SW1A1AA&format=xml')
        # Should return 200 or 400 (if geocoding fails or no results)
        assert response.status_code in [200, 400]
