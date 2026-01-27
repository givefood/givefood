import pytest
from givefood.models import Foodbank, FoodbankLocation


@pytest.mark.django_db
class TestFoodbankHasServiceArea:
    """Test the Foodbank.has_service_area() method."""

    def create_foodbank(self, slug_suffix=""):
        """Helper to create a test foodbank."""
        foodbank = Foodbank(
            name=f"Test Food Bank {slug_suffix}",
            slug=f"test-food-bank-{slug_suffix}" if slug_suffix else "test-food-bank",
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
        return foodbank

    def test_has_service_area_returns_false_when_no_locations(self):
        """Test that has_service_area returns False when foodbank has no locations."""
        foodbank = self.create_foodbank("no-locations")
        
        assert foodbank.has_service_area() is False

    def test_has_service_area_returns_false_when_locations_have_null_boundary(self):
        """Test that has_service_area returns False when locations have NULL boundary_geojson."""
        foodbank = self.create_foodbank("null-boundary")
        
        # Create location with NULL boundary_geojson
        FoodbankLocation.objects.create(
            foodbank=foodbank,
            name="Test Location",
            address="Test Location Address",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            boundary_geojson=None,  # NULL
        )
        
        # Refresh foodbank to get updated no_locations count
        foodbank.refresh_from_db()
        
        assert foodbank.has_service_area() is False

    def test_has_service_area_returns_false_when_locations_have_empty_string_boundary(self):
        """Test that has_service_area returns False when locations have empty string boundary_geojson."""
        foodbank = self.create_foodbank("empty-boundary")
        
        # Create location with empty string boundary_geojson
        FoodbankLocation.objects.create(
            foodbank=foodbank,
            name="Test Location",
            address="Test Location Address",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            boundary_geojson="",  # Empty string
        )
        
        # Refresh foodbank to get updated no_locations count
        foodbank.refresh_from_db()
        
        assert foodbank.has_service_area() is False

    def test_has_service_area_returns_true_when_location_has_valid_boundary(self):
        """Test that has_service_area returns True when a location has valid boundary_geojson."""
        foodbank = self.create_foodbank("valid-boundary")
        
        # Create location with valid boundary_geojson
        FoodbankLocation.objects.create(
            foodbank=foodbank,
            name="Test Location",
            address="Test Location Address",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            boundary_geojson='{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-0.1,51.5],[-0.2,51.5],[-0.2,51.6],[-0.1,51.6],[-0.1,51.5]]]}}',
        )
        
        # Refresh foodbank to get updated no_locations count
        foodbank.refresh_from_db()
        
        assert foodbank.has_service_area() is True

    def test_has_service_area_returns_true_when_one_of_multiple_locations_has_boundary(self):
        """Test that has_service_area returns True when at least one location has boundary_geojson."""
        foodbank = self.create_foodbank("mixed-boundary")
        
        # Create location with NULL boundary
        FoodbankLocation.objects.create(
            foodbank=foodbank,
            name="Location 1 (no boundary)",
            address="Test Location Address 1",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            boundary_geojson=None,
        )
        
        # Create location with empty string boundary
        FoodbankLocation.objects.create(
            foodbank=foodbank,
            name="Location 2 (empty boundary)",
            address="Test Location Address 2",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            boundary_geojson="",
        )
        
        # Create location with valid boundary
        FoodbankLocation.objects.create(
            foodbank=foodbank,
            name="Location 3 (valid boundary)",
            address="Test Location Address 3",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            boundary_geojson='{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-0.1,51.5],[-0.2,51.5],[-0.2,51.6],[-0.1,51.6],[-0.1,51.5]]]}}',
        )
        
        # Refresh foodbank to get updated no_locations count
        foodbank.refresh_from_db()
        
        assert foodbank.has_service_area() is True

    def test_has_service_area_returns_false_when_all_locations_have_no_boundary(self):
        """Test that has_service_area returns False when all locations have NULL or empty boundary_geojson."""
        foodbank = self.create_foodbank("all-no-boundary")
        
        # Create location with NULL boundary
        FoodbankLocation.objects.create(
            foodbank=foodbank,
            name="Location 1 (no boundary)",
            address="Test Location Address 1",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            boundary_geojson=None,
        )
        
        # Create location with empty string boundary
        FoodbankLocation.objects.create(
            foodbank=foodbank,
            name="Location 2 (empty boundary)",
            address="Test Location Address 2",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            boundary_geojson="",
        )
        
        # Refresh foodbank to get updated no_locations count
        foodbank.refresh_from_db()
        
        assert foodbank.has_service_area() is False
