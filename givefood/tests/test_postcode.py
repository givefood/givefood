import pytest
import csv
import tempfile
import os
from io import StringIO
from django.core.management import call_command

from givefood.models import Postcode


@pytest.mark.django_db
class TestPostcodeModel:
    """Test the Postcode model."""

    def test_postcode_create(self):
        """Test creating a postcode instance."""
        postcode = Postcode.objects.create(
            postcode="SW1A 1AA",
            lat_lng="51.501009,-0.141588",
            county="Greater London",
            district="Westminster",
            ward="St James's",
            country="England",
            region="London",
            lsoa_code="E01004736",
            msoa_code="E02000977",
            police="Metropolitan Police",
        )
        
        assert postcode.postcode == "SW1A 1AA"
        assert postcode.lat_lng == "51.501009,-0.141588"
        assert postcode.county == "Greater London"
        assert postcode.district == "Westminster"
        assert postcode.ward == "St James's"
        assert postcode.country == "England"
        assert postcode.region == "London"
        assert postcode.lsoa_code == "E01004736"
        assert postcode.msoa_code == "E02000977"
        assert postcode.police == "Metropolitan Police"

    def test_postcode_str(self):
        """Test the string representation of a Postcode."""
        postcode = Postcode(postcode="SW1A 1AA", lat_lng="51.501,-0.141", country="England")
        assert str(postcode) == "SW1A 1AA"

    def test_postcode_unique(self):
        """Test that postcodes must be unique."""
        Postcode.objects.create(
            postcode="SW1A 1AA",
            lat_lng="51.501009,-0.141588",
            country="England",
        )
        
        with pytest.raises(Exception):  # IntegrityError
            Postcode.objects.create(
                postcode="SW1A 1AA",
                lat_lng="51.501009,-0.141588",
                country="England",
            )

    def test_postcode_nullable_fields(self):
        """Test that optional fields can be null."""
        postcode = Postcode.objects.create(
            postcode="SW1A 2AA",
            lat_lng="51.501,-0.141",
            country="England",
        )
        
        assert postcode.county is None
        assert postcode.district is None
        assert postcode.ward is None
        assert postcode.region is None
        assert postcode.lsoa_code is None
        assert postcode.msoa_code is None
        assert postcode.police is None


@pytest.mark.django_db
class TestImportPostcodesCommand:
    """Test the import_postcodes management command."""

    def create_csv_file(self, rows):
        """Helper to create a temporary CSV file."""
        header = [
            'Postcode', 'In Use?', 'Latitude', 'Longitude', 'Easting', 'Northing',
            'Grid Ref', 'County', 'District', 'Ward', 'District Code', 'Ward Code',
            'Country', 'County Code', 'Introduced', 'Terminated', 'Parish',
            'National Park', 'Population', 'Households', 'Built up area',
            'Lower layer super output area', 'Rural/urban', 'Region', 'Altitude',
            'London zone', 'LSOA Code', 'Local authority', 'MSOA Code',
            'Middle layer super output area', 'Parish Code', 'Census output area',
            'Index of Multiple Deprivation', 'Quality', 'User Type', 'Last updated',
            'Nearest station', 'Distance to station', 'Postcode area',
            'Postcode district', 'Police force', 'Plus Code', 'Average Income',
            'Travel To Work Area', 'ITL level 2', 'ITL level 3', 'UPRNs',
            'Distance to sea', 'LSOA21 Code', 'Lower layer super output area 2021',
            'MSOA21 Code', 'Middle layer super output area 2021',
            'Census output area 2021', 'IMD decile', 'Constituency Code 2024',
            'Constituency Name 2024', 'Property Type', 'Roads', 'FixPhrase',
            'Rural/urban 2021'
        ]
        
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)
        return path

    def test_import_in_use_postcodes(self):
        """Test that only 'In Use' postcodes are imported."""
        csv_path = self.create_csv_file([
            # In use postcode
            ['SW1A 1AA', 'Yes', '51.501009', '-0.141588', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004736', '', 'E02000977', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
            # Not in use postcode
            ['SW1A 0AA', 'No', '51.501', '-0.141', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004736', '', 'E02000977', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ])
        
        try:
            out = StringIO()
            call_command('import_postcodes', csv_path, stdout=out)
            
            # Check only the 'In Use' postcode was imported
            assert Postcode.objects.count() == 1
            assert Postcode.objects.filter(postcode='SW1A 1AA').exists()
            assert not Postcode.objects.filter(postcode='SW1A 0AA').exists()
        finally:
            os.unlink(csv_path)

    def test_import_dry_run(self):
        """Test that dry-run does not create records."""
        csv_path = self.create_csv_file([
            ['SW1A 1AA', 'Yes', '51.501009', '-0.141588', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004736', '', 'E02000977', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ])
        
        try:
            out = StringIO()
            call_command('import_postcodes', csv_path, '--dry-run', stdout=out)
            
            # No postcodes should be created in dry run
            assert Postcode.objects.count() == 0
            assert 'DRY RUN' in out.getvalue()
        finally:
            os.unlink(csv_path)

    def test_import_restartable(self):
        """Test that import skips existing postcodes (restartable)."""
        # Create an existing postcode
        Postcode.objects.create(
            postcode='SW1A 1AA',
            lat_lng='51.501,-0.141',
            country='England',
        )
        
        csv_path = self.create_csv_file([
            # Existing postcode
            ['SW1A 1AA', 'Yes', '51.501009', '-0.141588', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004736', '', 'E02000977', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
            # New postcode
            ['SW1A 2AA', 'Yes', '51.502', '-0.142', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004737', '', 'E02000978', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ])
        
        try:
            out = StringIO()
            call_command('import_postcodes', csv_path, stdout=out)
            
            # Should have 2 postcodes total (1 existing + 1 new)
            assert Postcode.objects.count() == 2
            assert 'skipped existing' in out.getvalue().lower() or 'skipped (already existing)' in out.getvalue().lower()
        finally:
            os.unlink(csv_path)

    def test_import_field_mapping(self):
        """Test that fields are correctly mapped from CSV."""
        csv_path = self.create_csv_file([
            ['SW1A 1AA', 'Yes', '51.501009', '-0.141588', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004736', '', 'E02000977', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ])
        
        try:
            call_command('import_postcodes', csv_path)
            
            postcode = Postcode.objects.get(postcode='SW1A 1AA')
            assert postcode.lat_lng == '51.501009,-0.141588'
            assert postcode.county == 'Greater London'
            assert postcode.district == 'Westminster'
            assert postcode.ward == 'St James'
            assert postcode.country == 'England'
            assert postcode.region == 'London'
            assert postcode.lsoa_code == 'E01004736'
            assert postcode.msoa_code == 'E02000977'
            assert postcode.police == 'Metropolitan Police'
        finally:
            os.unlink(csv_path)

    def test_import_skips_missing_coordinates(self):
        """Test that postcodes with missing coordinates are skipped."""
        csv_path = self.create_csv_file([
            # Postcode with missing latitude
            ['SW1A 1AA', 'Yes', '', '-0.141588', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004736', '', 'E02000977', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
            # Postcode with valid coordinates
            ['SW1A 2AA', 'Yes', '51.501', '-0.141', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004737', '', 'E02000978', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ])
        
        try:
            out = StringIO()
            call_command('import_postcodes', csv_path, stdout=out)
            
            # Only the valid postcode should be imported
            assert Postcode.objects.count() == 1
            assert Postcode.objects.filter(postcode='SW1A 2AA').exists()
            assert not Postcode.objects.filter(postcode='SW1A 1AA').exists()
            assert 'missing data' in out.getvalue().lower()
        finally:
            os.unlink(csv_path)

    def test_import_skips_missing_country(self):
        """Test that postcodes with missing country are skipped."""
        csv_path = self.create_csv_file([
            # Postcode with missing country
            ['SW1A 1AA', 'Yes', '51.501009', '-0.141588', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', '', '', '', '', '', '', '', '',  # Country is empty
             '', '', '', 'London', '', '', 'E01004736', '', 'E02000977', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
            # Postcode with valid country
            ['SW1A 2AA', 'Yes', '51.501', '-0.141', '', '', '', 'Greater London',
             'Westminster', 'St James', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', 'London', '', '', 'E01004737', '', 'E02000978', '', '', '', '',
             '', '', '', '', '', '', '', 'Metropolitan Police', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ])
        
        try:
            out = StringIO()
            call_command('import_postcodes', csv_path, stdout=out)
            
            # Only the valid postcode should be imported
            assert Postcode.objects.count() == 1
            assert Postcode.objects.filter(postcode='SW1A 2AA').exists()
            assert not Postcode.objects.filter(postcode='SW1A 1AA').exists()
            assert 'missing data' in out.getvalue().lower()
        finally:
            os.unlink(csv_path)

    def test_import_batch_size(self):
        """Test that batching works correctly with different batch sizes."""
        # Create 5 postcodes
        csv_path = self.create_csv_file([
            ['SW1A 1AA', 'Yes', '51.501', '-0.141', '', '', '', '',
             '', '', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
            ['SW1A 2AA', 'Yes', '51.502', '-0.142', '', '', '', '',
             '', '', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
            ['SW1A 3AA', 'Yes', '51.503', '-0.143', '', '', '', '',
             '', '', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
            ['SW1A 4AA', 'Yes', '51.504', '-0.144', '', '', '', '',
             '', '', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
            ['SW1A 5AA', 'Yes', '51.505', '-0.145', '', '', '', '',
             '', '', '', '', 'England', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', '', '',
             '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ])
        
        try:
            # Use batch size of 2 so we have 2 full batches + 1 remaining
            call_command('import_postcodes', csv_path, '--batch-size=2')
            
            # All 5 postcodes should be imported
            assert Postcode.objects.count() == 5
        finally:
            os.unlink(csv_path)
