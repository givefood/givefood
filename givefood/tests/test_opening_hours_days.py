"""
Tests for the opening_hours_days method of FoodbankDonationPoint.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from givefood.models import _get_bank_holidays


# Test constant for opening hours
OPENING_HOURS_SAMPLE = "Monday: 9:00 AM – 5:00 PM\nTuesday: 9:00 AM – 5:00 PM\nWednesday: 9:00 AM – 5:00 PM\nThursday: 9:00 AM – 5:00 PM\nFriday: 9:00 AM – 5:00 PM\nSaturday: Closed\nSunday: Closed"


class TestOpeningHoursDays:
    """Test opening_hours_days method of FoodbankDonationPoint."""

    def test_opening_hours_days_handles_already_converted_dates(self):
        """Test that opening_hours_days doesn't fail when called multiple times.
        
        The bank holidays data is cached at module level and the dates are
        converted from strings to date objects on first call. Subsequent calls
        should handle dates that are already datetime.date objects without
        raising a TypeError.
        
        This tests the fix for issue #1117 where strptime() was called on
        datetime.date objects instead of strings.
        """
        # Create a mock donation point
        mock_donation_point = MagicMock()
        mock_donation_point.opening_hours = OPENING_HOURS_SAMPLE
        mock_donation_point.country = "England"
        
        # Import the method and bind it to our mock object
        from givefood.models import FoodbankDonationPoint
        
        # Call the actual opening_hours_days method with our mock's data
        # Use the real method from the class
        result1 = FoodbankDonationPoint.opening_hours_days(mock_donation_point)
        
        # The second call should not fail with TypeError
        # because the dates are already datetime.date objects
        result2 = FoodbankDonationPoint.opening_hours_days(mock_donation_point)

        # Both results should be valid lists
        assert result1 is not False
        assert result2 is not False
        assert len(result1) == 7  # 7 days of the week
        assert len(result2) == 7

    def test_opening_hours_days_returns_false_without_opening_hours(self):
        """Test that opening_hours_days returns False when no opening hours are set."""
        # Create a mock donation point without opening hours
        mock_donation_point = MagicMock()
        mock_donation_point.opening_hours = None
        mock_donation_point.country = "England"
        
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.opening_hours_days(mock_donation_point)
        assert result is False

    def test_opening_hours_days_with_string_dates(self):
        """Test that opening_hours_days handles string dates from fresh JSON load."""
        # This simulates what happens when bank holidays are first loaded from JSON
        # (dates are strings) and then converted
        
        mock_donation_point = MagicMock()
        mock_donation_point.opening_hours = OPENING_HOURS_SAMPLE
        mock_donation_point.country = "England"
        
        # Mock the bank holidays cache to return fresh string dates
        mock_holidays = {
            "england-and-wales": {
                "events": [
                    {"date": "2025-12-25", "title": "Christmas Day", "bunting": True, "notes": ""},
                    {"date": "2025-12-26", "title": "Boxing Day", "bunting": True, "notes": ""},
                ]
            }
        }
        
        with patch('givefood.models._get_bank_holidays', return_value=mock_holidays):
            from givefood.models import FoodbankDonationPoint
            result = FoodbankDonationPoint.opening_hours_days(mock_donation_point)
            
            assert result is not False
            assert len(result) == 7
            # Verify dates were processed
            for day in result:
                assert "date" in day
                assert isinstance(day["date"], date)

    def test_opening_hours_days_with_date_objects(self):
        """Test that opening_hours_days handles already converted date objects."""
        # This simulates what happens on subsequent calls when dates are already
        # converted to date objects (the bug scenario)
        
        mock_donation_point = MagicMock()
        mock_donation_point.opening_hours = OPENING_HOURS_SAMPLE
        mock_donation_point.country = "England"
        
        # Mock the bank holidays cache to return already converted date objects
        mock_holidays = {
            "england-and-wales": {
                "events": [
                    {"date": date(2025, 12, 25), "title": "Christmas Day", "bunting": True, "notes": ""},
                    {"date": date(2025, 12, 26), "title": "Boxing Day", "bunting": True, "notes": ""},
                ]
            }
        }
        
        with patch('givefood.models._get_bank_holidays', return_value=mock_holidays):
            from givefood.models import FoodbankDonationPoint
            # This should NOT raise TypeError: strptime() argument 1 must be str, not datetime.date
            result = FoodbankDonationPoint.opening_hours_days(mock_donation_point)
            
            assert result is not False
            assert len(result) == 7

