import pytest
from givefood.models import Foodbank, FoodbankLocation, FoodbankDonationPoint


@pytest.fixture
def test_foodbank(db):
    """Create a test foodbank for use in tests."""
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
    return foodbank


@pytest.mark.django_db
class TestFoodbankBounds:
    """Test that Foodbank bounds are correctly calculated and updated."""

    def test_new_foodbank_bounds_use_foodbank_coordinates(self, test_foodbank):
        """Test that a new foodbank uses its own coordinates for bounds."""
        # Check bounds are set to foodbank coordinates
        assert test_foodbank.bounds_north == 51.5014
        assert test_foodbank.bounds_south == 51.5014
        assert test_foodbank.bounds_east == -0.1419
        assert test_foodbank.bounds_west == -0.1419

    def test_foodbank_bounds_updated_when_location_added(self, test_foodbank):
        """Test that foodbank bounds are updated when a location is added."""
        # Initial bounds should be foodbank coordinates
        initial_north = test_foodbank.bounds_north
        initial_south = test_foodbank.bounds_south
        initial_east = test_foodbank.bounds_east
        initial_west = test_foodbank.bounds_west

        # Add a location north and east of the foodbank
        location = FoodbankLocation(
            foodbank=test_foodbank,
            name="North Location",
            address="North Address",
            postcode="SW1A 2AA",
            lat_lng="51.6014,-0.0419",  # North: +0.1, East: +0.1
            latitude=51.6014,
            longitude=-0.0419,
        )
        location.save(do_geoupdate=False)

        # Reload foodbank from database
        test_foodbank.refresh_from_db()

        # Bounds should now be expanded
        assert test_foodbank.bounds_north > initial_north
        assert test_foodbank.bounds_south == initial_south  # Should stay the same
        assert test_foodbank.bounds_east > initial_east
        assert test_foodbank.bounds_west == initial_west  # Should stay the same

        # Check specific values
        assert test_foodbank.bounds_north == 51.6014
        assert test_foodbank.bounds_south == 51.5014
        assert test_foodbank.bounds_east == -0.0419
        assert test_foodbank.bounds_west == -0.1419

    def test_foodbank_bounds_updated_when_donation_point_added(self, test_foodbank):
        """Test that foodbank bounds are updated when a donation point is added."""
        # Initial bounds should be foodbank coordinates
        initial_north = test_foodbank.bounds_north
        initial_south = test_foodbank.bounds_south
        initial_east = test_foodbank.bounds_east
        initial_west = test_foodbank.bounds_west

        # Add a donation point south and west of the foodbank
        donation_point = FoodbankDonationPoint(
            foodbank=test_foodbank,
            name="South Donation Point",
            address="South Address",
            postcode="SW1A 3AA",
            lat_lng="51.4014,-0.2419",  # South: -0.1, West: -0.1
            latitude=51.4014,
            longitude=-0.2419,
        )
        donation_point.save(do_geoupdate=False, do_photo_update=False)

        # Reload foodbank from database
        test_foodbank.refresh_from_db()

        # Bounds should now be expanded
        assert test_foodbank.bounds_north == initial_north  # Should stay the same
        assert test_foodbank.bounds_south < initial_south
        assert test_foodbank.bounds_east == initial_east  # Should stay the same
        assert test_foodbank.bounds_west < initial_west

        # Check specific values
        assert test_foodbank.bounds_north == 51.5014
        assert test_foodbank.bounds_south == 51.4014
        assert test_foodbank.bounds_east == -0.1419
        assert test_foodbank.bounds_west == -0.2419

    def test_foodbank_bounds_updated_when_location_deleted(self, test_foodbank):
        """Test that foodbank bounds are updated when a location is deleted."""
        # Add a location
        location = FoodbankLocation(
            foodbank=test_foodbank,
            name="North Location",
            address="North Address",
            postcode="SW1A 2AA",
            lat_lng="51.6014,-0.0419",
            latitude=51.6014,
            longitude=-0.0419,
        )
        location.save(do_geoupdate=False)

        # Reload foodbank
        test_foodbank.refresh_from_db()

        # Verify bounds are expanded
        assert test_foodbank.bounds_north == 51.6014
        assert test_foodbank.bounds_east == -0.0419

        # Delete the location
        location.delete()

        # Reload foodbank
        test_foodbank.refresh_from_db()

        # Bounds should revert to foodbank coordinates
        assert test_foodbank.bounds_north == 51.5014
        assert test_foodbank.bounds_south == 51.5014
        assert test_foodbank.bounds_east == -0.1419
        assert test_foodbank.bounds_west == -0.1419

    def test_foodbank_bounds_with_multiple_locations_and_donation_points(self, test_foodbank):
        """Test bounds calculation with multiple locations and donation points."""
        # Add location to the north
        north_location = FoodbankLocation(
            foodbank=test_foodbank,
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
            foodbank=test_foodbank,
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
            foodbank=test_foodbank,
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
            foodbank=test_foodbank,
            name="West Donation Point",
            address="West Address",
            postcode="SW1A 5AA",
            lat_lng="51.5014,-0.3419",  # Westmost
            latitude=51.5014,
            longitude=-0.3419,
        )
        west_dp.save(do_geoupdate=False, do_photo_update=False)

        # Reload foodbank
        test_foodbank.refresh_from_db()

        # Bounds should encompass all points
        assert test_foodbank.bounds_north == 51.7014
        assert test_foodbank.bounds_south == 51.3014
        assert test_foodbank.bounds_east == 0.0581
        assert test_foodbank.bounds_west == -0.3419
