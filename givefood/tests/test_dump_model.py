import pytest
from datetime import datetime
from givefood.models import Dump


@pytest.mark.django_db
class TestDumpModel:
    """Test the Dump model, particularly the file_name() method."""

    def test_file_name_format(self):
        """Test that file_name() generates correct filename without language code."""
        # Create a dump instance
        dump = Dump(
            dump_type="foodbanks",
            dump_format="csv",
            the_dump="test,data\n1,2",
        )
        dump.save()

        # Get the filename
        filename = dump.file_name()

        # Expected format: {dump_type}-{YYYYMMDD}.{dump_format}
        # e.g., "foodbanks-20251102.csv"
        expected_date_str = dump.created.strftime("%Y%m%d")
        expected_filename = f"foodbanks-{expected_date_str}.csv"

        assert filename == expected_filename
        # Verify that language code is NOT in the filename
        # Old format was: {dump_type}-{language}-{YYYYMMDD}.{dump_format}
        # So we should not have a pattern like "foodbanks-en-20251102.csv"
        assert "-en-" not in filename
        assert "-es-" not in filename
        assert "-cy-" not in filename

    def test_file_name_with_different_formats(self):
        """Test file_name() with different dump formats."""
        dump_json = Dump(
            dump_type="items",
            dump_format="json",
            the_dump='{"test": "data"}',
        )
        dump_json.save()

        filename = dump_json.file_name()
        expected_date_str = dump_json.created.strftime("%Y%m%d")
        expected_filename = f"items-{expected_date_str}.json"

        assert filename == expected_filename
        assert filename.endswith(".json")

    def test_file_name_consistency_across_calls(self):
        """Test that file_name() returns the same value on multiple calls."""
        dump = Dump(
            dump_type="donationpoints",
            dump_format="csv",
            the_dump="test,data",
        )
        dump.save()

        # Call file_name() multiple times
        filename1 = dump.file_name()
        filename2 = dump.file_name()
        filename3 = dump.file_name()

        # All should be identical
        assert filename1 == filename2
        assert filename2 == filename3
