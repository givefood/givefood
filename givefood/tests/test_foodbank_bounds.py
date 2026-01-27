import pytest
from givefood.models import Foodbank, FoodbankLocation, FoodbankDonationPoint


@pytest.mark.django_db
class TestFoodbankBounds:
    """Test that Foodbank bounds are correctly calculated and updated."""

    def test_new_foodbank_bounds_use_foodbank_coordinates(self):
        """Test that a new foodbank uses its own coordinates for bounds."""
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
            contact_email="test@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Check bounds are set to foodbank coordinates
        assert foodbank.bounds_north == 51.5014
        assert foodbank.bounds_south == 51.5014
        assert foodbank.bounds_east == -0.1419
        assert foodbank.bounds_west == -0.1419

    def test_foodbank_bounds_updated_when_location_added(self):
        """Test that foodbank bounds are updated when a location is added."""
        # Create a foodbank
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
            contact_email="test@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Initial bounds should be foodbank coordinates
        initial_north = foodbank.bounds_north
        initial_south = foodbank.bounds_south
        initial_east = foodbank.bounds_east
        initial_west = foodbank.bounds_west

        # Add a location north and east of the foodbank
        location = FoodbankLocation(
            foodbank=foodbank,
            name="North Location",
            address="North Address",
            postcode="SW1A 2AA",
            lat_lng="51.6014,-0.0419",  # North: +0.1, East: +0.1
            latitude=51.6014,
            longitude=-0.0419,
        )
        location.save(do_geoupdate=False)

        # Reload foodbank from database
        foodbank.refresh_from_db()

        # Bounds should now be expanded
        assert foodbank.bounds_north > initial_north
        assert foodbank.bounds_south == initial_south  # Should stay the same
        assert foodbank.bounds_east > initial_east
        assert foodbank.bounds_west == initial_west  # Should stay the same

        # Check specific values
        assert foodbank.bounds_north == 51.6014
        assert foodbank.bounds_south == 51.5014
        assert foodbank.bounds_east == -0.0419
        assert foodbank.bounds_west == -0.1419

    def test_foodbank_bounds_updated_when_donation_point_added(self):
        """Test that foodbank bounds are updated when a donation point is added."""
        # Create a foodbank
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
            contact_email="test@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Initial bounds should be foodbank coordinates
        initial_north = foodbank.bounds_north
        initial_south = foodbank.bounds_south
        initial_east = foodbank.bounds_east
        initial_west = foodbank.bounds_west

        # Add a donation point south and west of the foodbank
        donation_point = FoodbankDonationPoint(
            foodbank=foodbank,
            name="South Donation Point",
            address="South Address",
            postcode="SW1A 3AA",
            lat_lng="51.4014,-0.2419",  # South: -0.1, West: -0.1
            latitude=51.4014,
            longitude=-0.2419,
        )
        donation_point.save(do_geoupdate=False, do_photo_update=False)

        # Reload foodbank from database
        foodbank.refresh_from_db()

        # Bounds should now be expanded
        assert foodbank.bounds_north == initial_north  # Should stay the same
        assert foodbank.bounds_south < initial_south
        assert foodbank.bounds_east == initial_east  # Should stay the same
        assert foodbank.bounds_west < initial_west

        # Check specific values
        assert foodbank.bounds_north == 51.5014
        assert foodbank.bounds_south == 51.4014
        assert foodbank.bounds_east == -0.1419
        assert foodbank.bounds_west == -0.2419

    def test_foodbank_bounds_updated_when_location_deleted(self):
        """Test that foodbank bounds are updated when a location is deleted."""
        # Create a foodbank
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
            contact_email="test@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Add a location
        location = FoodbankLocation(
            foodbank=foodbank,
            name="North Location",
            address="North Address",
            postcode="SW1A 2AA",
            lat_lng="51.6014,-0.0419",
            latitude=51.6014,
            longitude=-0.0419,
        )
        location.save(do_geoupdate=False)

        # Reload foodbank
        foodbank.refresh_from_db()

        # Verify bounds are expanded
        assert foodbank.bounds_north == 51.6014
        assert foodbank.bounds_east == -0.0419

        # Delete the location
        location.delete()

        # Reload foodbank
        foodbank.refresh_from_db()

        # Bounds should revert to foodbank coordinates
        assert foodbank.bounds_north == 51.5014
        assert foodbank.bounds_south == 51.5014
        assert foodbank.bounds_east == -0.1419
        assert foodbank.bounds_west == -0.1419

    def test_foodbank_bounds_with_multiple_locations_and_donation_points(self):
        """Test bounds calculation with multiple locations and donation points."""
        # Create a foodbank at the center
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
            contact_email="test@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Add location to the north
        north_location = FoodbankLocation(
            foodbank=foodbank,
            name="North Location",
            address="North Address",
            postcode="SW1A 2AA",
            lat_lng="51.7014,-0.1419",  # Northmost
            latitude=51.7014,
            longitude=-0.1419,
        )
        north_location.save(do_geoupdate=False)

        # Add location to the south
        south_location = FoodbankLocation(
            foodbank=foodbank,
            name="South Location",
            address="South Address",
            postcode="SW1A 3AA",
            lat_lng="51.3014,-0.1419",  # Southmost
            latitude=51.3014,
            longitude=-0.1419,
        )
        south_location.save(do_geoupdate=False)

        # Add donation point to the east
        east_dp = FoodbankDonationPoint(
            foodbank=foodbank,
            name="East Donation Point",
            address="East Address",
            postcode="SW1A 4AA",
            lat_lng="51.5014,0.0581",  # Eastmost
            latitude=51.5014,
            longitude=0.0581,
        )
        east_dp.save(do_geoupdate=False, do_photo_update=False)

        # Add donation point to the west
        west_dp = FoodbankDonationPoint(
            foodbank=foodbank,
            name="West Donation Point",
            address="West Address",
            postcode="SW1A 5AA",
            lat_lng="51.5014,-0.3419",  # Westmost
            latitude=51.5014,
            longitude=-0.3419,
        )
        west_dp.save(do_geoupdate=False, do_photo_update=False)

        # Reload foodbank
        foodbank.refresh_from_db()

        # Bounds should encompass all points
        assert foodbank.bounds_north == 51.7014
        assert foodbank.bounds_south == 51.3014
        assert foodbank.bounds_east == 0.0581
        assert foodbank.bounds_west == -0.3419
