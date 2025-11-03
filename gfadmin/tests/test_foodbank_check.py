"""Tests for the foodbank check comparison functionality."""
import pytest
import json
from gfadmin.views import compare_foodbank_data


class TestCompareFoodbankData:
    """Test the compare_foodbank_data function."""

    def test_no_differences_in_details(self):
        """Test when details are identical."""
        foodbank_json = {
            "details": {
                "name": "Test Foodbank",
                "address": "123 Test St",
                "postcode": "TE1 1ST",
                "country": "England",
                "phone_number": "01234567890",
                "contact_email": "test@example.com",
                "network": "Independent"
            },
            "locations": [],
            "donation_points": []
        }
        check_result = foodbank_json.copy()
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        assert len(differences["details_diff"]["deletions"]) == 0
        assert len(differences["details_diff"]["additions"]) == 0

    def test_details_field_changed(self):
        """Test when a detail field is changed."""
        foodbank_json = {
            "details": {
                "name": "Old Name",
                "address": "Old Address",
                "postcode": "TE1 1ST",
                "country": "England",
                "phone_number": "01234567890",
                "contact_email": "old@example.com",
                "network": "Independent"
            },
            "locations": [],
            "donation_points": []
        }
        check_result = {
            "details": {
                "name": "New Name",
                "address": "Old Address",
                "postcode": "TE1 1ST",
                "country": "England",
                "phone_number": "01234567890",
                "contact_email": "new@example.com",
                "network": "Independent"
            },
            "locations": [],
            "donation_points": []
        }
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        assert "name" in differences["details_diff"]["deletions"]
        assert differences["details_diff"]["deletions"]["name"] == "Old Name"
        assert differences["details_diff"]["additions"]["name"] == "New Name"
        assert "contact_email" in differences["details_diff"]["deletions"]

    def test_no_differences_in_locations(self):
        """Test when locations are identical."""
        foodbank_json = {
            "details": {},
            "locations": [
                {"name": "Location 1", "address": "Address 1", "postcode": "PC1 1AA"},
                {"name": "Location 2", "address": "Address 2", "postcode": "PC2 2BB"}
            ],
            "donation_points": []
        }
        check_result = foodbank_json.copy()
        check_result["locations"] = list(foodbank_json["locations"])
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        assert len(differences["locations_diff"]["deletions"]) == 0
        assert len(differences["locations_diff"]["additions"]) == 0

    def test_location_added(self):
        """Test when a location is added."""
        foodbank_json = {
            "details": {},
            "locations": [
                {"name": "Location 1", "address": "Address 1", "postcode": "PC1 1AA"}
            ],
            "donation_points": []
        }
        check_result = {
            "details": {},
            "locations": [
                {"name": "Location 1", "address": "Address 1", "postcode": "PC1 1AA"},
                {"name": "Location 2", "address": "Address 2", "postcode": "PC2 2BB"}
            ],
            "donation_points": []
        }
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        assert len(differences["locations_diff"]["additions"]) == 1
        assert differences["locations_diff"]["additions"][0]["name"] == "Location 2"
        assert len(differences["locations_diff"]["deletions"]) == 0

    def test_location_removed(self):
        """Test when a location is removed."""
        foodbank_json = {
            "details": {},
            "locations": [
                {"name": "Location 1", "address": "Address 1", "postcode": "PC1 1AA"},
                {"name": "Location 2", "address": "Address 2", "postcode": "PC2 2BB"}
            ],
            "donation_points": []
        }
        check_result = {
            "details": {},
            "locations": [
                {"name": "Location 1", "address": "Address 1", "postcode": "PC1 1AA"}
            ],
            "donation_points": []
        }
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        assert len(differences["locations_diff"]["deletions"]) == 1
        assert differences["locations_diff"]["deletions"][0]["name"] == "Location 2"
        assert len(differences["locations_diff"]["additions"]) == 0

    def test_donation_point_added(self):
        """Test when a donation point is added."""
        foodbank_json = {
            "details": {},
            "locations": [],
            "donation_points": []
        }
        check_result = {
            "details": {},
            "locations": [],
            "donation_points": [
                {"name": "Tesco", "address": "High Street", "postcode": "PC3 3CC"}
            ]
        }
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        assert len(differences["donation_points_diff"]["additions"]) == 1
        assert differences["donation_points_diff"]["additions"][0]["name"] == "Tesco"
        assert len(differences["donation_points_diff"]["deletions"]) == 0

    def test_donation_point_removed(self):
        """Test when a donation point is removed."""
        foodbank_json = {
            "details": {},
            "locations": [],
            "donation_points": [
                {"name": "Tesco", "address": "High Street", "postcode": "PC3 3CC"}
            ]
        }
        check_result = {
            "details": {},
            "locations": [],
            "donation_points": []
        }
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        assert len(differences["donation_points_diff"]["deletions"]) == 1
        assert differences["donation_points_diff"]["deletions"][0]["name"] == "Tesco"
        assert len(differences["donation_points_diff"]["additions"]) == 0

    def test_handles_string_check_result(self):
        """Test that function handles JSON string check_result."""
        foodbank_json = {
            "details": {"name": "Test"},
            "locations": [],
            "donation_points": []
        }
        check_result_str = json.dumps({
            "details": {"name": "Test"},
            "locations": [],
            "donation_points": []
        })
        
        differences = compare_foodbank_data(foodbank_json, check_result_str)
        
        assert len(differences["details_diff"]["deletions"]) == 0

    def test_handles_invalid_check_result(self):
        """Test that function handles invalid check_result gracefully."""
        foodbank_json = {
            "details": {"name": "Test"},
            "locations": [],
            "donation_points": []
        }
        
        differences = compare_foodbank_data(foodbank_json, "invalid json")
        
        # Should return empty differences without crashing
        assert len(differences["details_diff"]["deletions"]) == 0
        assert len(differences["locations_diff"]["deletions"]) == 0
        assert len(differences["donation_points_diff"]["deletions"]) == 0

    def test_whitespace_normalization(self):
        """Test that whitespace differences are ignored."""
        foodbank_json = {
            "details": {"name": "Test Name  ", "address": " Address "},
            "locations": [],
            "donation_points": []
        }
        check_result = {
            "details": {"name": "  Test Name", "address": "Address"},
            "locations": [],
            "donation_points": []
        }
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        # Should not detect differences due to whitespace
        assert len(differences["details_diff"]["deletions"]) == 0

    def test_case_insensitive_location_comparison(self):
        """Test that location comparison is case-insensitive."""
        foodbank_json = {
            "details": {},
            "locations": [
                {"name": "Location One", "address": "123 Main St", "postcode": "PC1 1AA"}
            ],
            "donation_points": []
        }
        check_result = {
            "details": {},
            "locations": [
                {"name": "LOCATION ONE", "address": "123 MAIN ST", "postcode": "pc1 1aa"}
            ],
            "donation_points": []
        }
        
        differences = compare_foodbank_data(foodbank_json, check_result)
        
        # Should not detect differences due to case
        assert len(differences["locations_diff"]["deletions"]) == 0
        assert len(differences["locations_diff"]["additions"]) == 0
