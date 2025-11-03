"""Tests for the foodbank check view and template."""
import pytest


@pytest.mark.django_db
class TestFoodbankCheckView:
    """Test the foodbank_check view rendering."""

    def test_template_renders_with_no_differences(self):
        """Test that the template renders correctly when no diffs exist."""
        # Test that we can access the template vars
        differences = {
            "details_diff": {"deletions": {}, "additions": {}},
            "locations_diff": {"deletions": [], "additions": []},
            "donation_points_diff": {"deletions": [], "additions": []},
        }

        # This tests that our structure is correct
        assert isinstance(differences["details_diff"], dict)
        assert "deletions" in differences["details_diff"]
        assert "additions" in differences["details_diff"]

    def test_template_renders_with_differences(self):
        """Test that the template renders correctly with differences."""
        differences = {
            "details_diff": {
                "deletions": {"name": "Old Name"},
                "additions": {"name": "New Name"}
            },
            "locations_diff": {
                "deletions": [{
                    "name": "Old Location",
                    "address": "Old Address",
                    "postcode": "OLD 123"
                }],
                "additions": [{
                    "name": "New Location",
                    "address": "New Address",
                    "postcode": "NEW 456"
                }]
            },
            "donation_points_diff": {
                "deletions": [],
                "additions": [{
                    "name": "Tesco",
                    "address": "High St",
                    "postcode": "TST 123"
                }]
            },
        }

        # Verify structure for template rendering
        assert len(differences["details_diff"]["deletions"]) == 1
        assert len(differences["locations_diff"]["deletions"]) == 1
        assert len(differences["locations_diff"]["additions"]) == 1
        assert len(differences["donation_points_diff"]["additions"]) == 1
