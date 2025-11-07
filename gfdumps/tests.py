"""
Tests for the gfdumps app, particularly the dump command.
"""
import pytest
import csv
import io
from django.core.management import call_command
from givefood.models import Foodbank, FoodbankChange, Dump


@pytest.mark.django_db
class TestDumpCommand:
    """Test the dump management command."""

    def test_foodbank_dump_includes_url_fields(self):
        """Test that the foodbank dump includes all URL fields including the new ones."""
        # Create a test foodbank with all URL fields populated
        foodbank = Foodbank(
            name="Test Food Bank for Dump",
            slug="test-food-bank-dump",
            address="123 Test Street",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
            rss_url="https://test.example.com/rss",
            donation_points_url="https://test.example.com/donation-points",
            locations_url="https://test.example.com/locations",
            contacts_url="https://test.example.com/contacts",
            contact_email="test@example.com",
            is_closed=False,
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need so latest_need is not None
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Tinned Tomatoes\nPasta",
            published=True,
        )
        need.save(do_translate=False)
        
        # Update foodbank to have the latest_need
        foodbank.latest_need = need
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Run the dump command
        call_command('dump')

        # Get the latest dump
        dump = Dump.objects.filter(dump_type='foodbanks').latest('created')

        # Parse the CSV
        csv_reader = csv.DictReader(io.StringIO(dump.the_dump))
        
        # Get the first row (should be our test foodbank)
        rows = list(csv_reader)
        assert len(rows) > 0

        # Find our test foodbank in the dump
        test_row = None
        for row in rows:
            if row['organisation_name'] == 'Test Food Bank for Dump':
                test_row = row
                break
        
        assert test_row is not None, "Test foodbank not found in dump"

        # Check that all URL fields are present in the header
        assert 'rss_url' in test_row
        assert 'donation_points_url' in test_row
        assert 'locations_url' in test_row
        assert 'contacts_url' in test_row

        # Check that the values are correct
        assert test_row['rss_url'] == 'https://test.example.com/rss'
        assert test_row['donation_points_url'] == 'https://test.example.com/donation-points'
        assert test_row['locations_url'] == 'https://test.example.com/locations'
        assert test_row['contacts_url'] == 'https://test.example.com/contacts'

    def test_foodbank_dump_handles_null_url_fields(self):
        """Test that the dump handles null URL fields gracefully."""
        # Create a test foodbank with minimal required fields
        foodbank = Foodbank(
            name="Test Food Bank Minimal",
            slug="test-food-bank-minimal",
            address="456 Test Avenue",
            postcode="SW1A 2BB",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://minimal.example.com",
            shopping_list_url="https://minimal.example.com/shopping",
            contact_email="minimal@example.com",
            is_closed=False,
            # URL fields left as None/blank
            rss_url=None,
            donation_points_url=None,
            locations_url=None,
            contacts_url=None,
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a need so latest_need is not None
        need = FoodbankChange(
            foodbank=foodbank,
            change_text="Rice\nBeans",
            published=True,
        )
        need.save(do_translate=False)
        
        # Update foodbank to have the latest_need
        foodbank.latest_need = need
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Run the dump command
        call_command('dump')

        # Get the latest dump
        dump = Dump.objects.filter(dump_type='foodbanks').latest('created')

        # Parse the CSV - should not raise any errors
        csv_reader = csv.DictReader(io.StringIO(dump.the_dump))
        rows = list(csv_reader)
        
        # Find our test foodbank
        test_row = None
        for row in rows:
            if row['organisation_name'] == 'Test Food Bank Minimal':
                test_row = row
                break
        
        assert test_row is not None, "Test minimal foodbank not found in dump"

        # Check that URL fields exist (even if empty)
        assert 'rss_url' in test_row
        assert 'donation_points_url' in test_row
        assert 'locations_url' in test_row
        assert 'contacts_url' in test_row
