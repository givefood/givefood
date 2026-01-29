"""Tests for N+1 query prevention on the foodbank admin page."""
import pytest
from django.test import RequestFactory
from unittest.mock import patch

from givefood.models import (
    Foodbank, FoodbankLocation, FoodbankDonationPoint
)


@pytest.mark.django_db
class TestFoodbankN1Queries:
    """Test that the foodbank admin page doesn't have N+1 queries."""

    @pytest.fixture
    def foodbank_with_locations(self):
        """Create a foodbank with multiple locations and donation points."""
        foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='Independent',  # Required for location denormalization
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        # Create multiple locations - using .save() with do_geoupdate=False 
        # to skip external API calls during tests
        for i in range(5):
            location = FoodbankLocation(
                foodbank=foodbank,
                name=f'Location {i}',
                address=f'{i} Test Street',
                postcode='AB12 3CD',
                lat_lng='51.5074,-0.1278',
            )
            location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        # Create multiple donation points
        for i in range(5):
            donation_point = FoodbankDonationPoint(
                foodbank=foodbank,
                name=f'Donation Point {i}',
                address=f'{i} Donation Street',
                postcode='AB12 3CD',
                lat_lng='51.5074,-0.1278',
            )
            donation_point.save(do_geoupdate=False, do_foodbank_resave=False)
        
        return foodbank

    def test_location_fields_no_n1_queries(self, foodbank_with_locations, django_assert_num_queries):
        """Test that accessing all location fields in template doesn't cause N+1 queries.
        
        This test verifies that the .only() optimization includes all fields
        that are actually used in the template, preventing Django from making
        additional queries when those fields are accessed.
        """
        from gfadmin.views import foodbank as foodbank_view
        
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank_with_locations.slug}/')
        
        # Mock render to get context without template rendering
        with patch('gfadmin.views.render') as mock_render:
            mock_render.return_value = None
            foodbank_view(request, slug=foodbank_with_locations.slug)
            
            # Get the template context
            render_args = mock_render.call_args
            template_vars = render_args[0][2]
            locations = list(template_vars['locations'])
        
        # Now access all fields that the template uses - this should not cause
        # additional queries if the .only() optimization is correct
        with django_assert_num_queries(0):
            for location in locations:
                # These fields must be in the .only() clause
                _ = location.name
                _ = location.slug
                _ = location.address
                _ = location.postcode
                _ = location.place_id
                _ = location.place_has_photo
                _ = location.phone_number
                _ = location.email
                _ = location.lat_lng
                _ = location.is_donation_point
                _ = location.boundary_geojson

    def test_donation_point_fields_no_n1_queries(self, foodbank_with_locations, django_assert_num_queries):
        """Test that accessing all donation point fields in template doesn't cause N+1 queries.
        
        This test verifies that the .only() optimization includes all fields
        that are actually used in the template, preventing Django from making
        additional queries when those fields are accessed.
        """
        from gfadmin.views import foodbank as foodbank_view
        
        factory = RequestFactory()
        request = factory.get(f'/admin/foodbank/{foodbank_with_locations.slug}/')
        
        # Mock render to get context without template rendering
        with patch('gfadmin.views.render') as mock_render:
            mock_render.return_value = None
            foodbank_view(request, slug=foodbank_with_locations.slug)
            
            # Get the template context
            render_args = mock_render.call_args
            template_vars = render_args[0][2]
            donation_points = list(template_vars['donation_points'])
        
        # Now access all fields that the template uses - this should not cause
        # additional queries if the .only() optimization is correct
        with django_assert_num_queries(0):
            for dp in donation_points:
                # These fields must be in the .only() clause
                _ = dp.name
                _ = dp.slug
                _ = dp.address
                _ = dp.postcode
                _ = dp.place_id
                _ = dp.place_has_photo
                _ = dp.lat_lng
                _ = dp.company
                _ = dp.store_id
                _ = dp.in_store_only
                _ = dp.notes
