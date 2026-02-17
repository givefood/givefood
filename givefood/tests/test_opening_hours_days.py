"""
Tests for the opening_hours_days method and is_open property of FoodbankDonationPoint.
"""
import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock
from givefood.models import _get_bank_holidays


# Test constant for opening hours
OPENING_HOURS_SAMPLE = "Monday: 9:00 AM – 5:00 PM\nTuesday: 9:00 AM – 5:00 PM\nWednesday: 9:00 AM – 5:00 PM\nThursday: 9:00 AM – 5:00 PM\nFriday: 9:00 AM – 5:00 PM\nSaturday: Closed\nSunday: Closed"

# Sunday open 10am-4pm sample (from the issue)
OPENING_HOURS_SUNDAY_SAMPLE = "Monday: 7:00 AM – 10:00 PM\nTuesday: 7:00 AM – 10:00 PM\nWednesday: 7:00 AM – 10:00 PM\nThursday: 7:00 AM – 10:00 PM\nFriday: 7:00 AM – 10:00 PM\nSaturday: 7:00 AM – 10:00 PM\nSunday: 10:00 AM – 4:00 PM"

# Midnight closing time sample (e.g. 6:00 AM – 12:00 AM)
OPENING_HOURS_MIDNIGHT_SAMPLE = "Monday: 6:00 AM – 12:00 AM\nTuesday: 6:00 AM – 12:00 AM\nWednesday: 6:00 AM – 12:00 AM\nThursday: 6:00 AM – 12:00 AM\nFriday: 6:00 AM – 12:00 AM\nSaturday: 6:00 AM – 10:00 PM\nSunday: 10:00 AM – 4:00 PM"


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

    def test_opening_hours_days_includes_day_name_and_hours(self):
        """Test that opening_hours_days returns day_name and hours fields."""
        mock_donation_point = MagicMock()
        mock_donation_point.opening_hours = OPENING_HOURS_SAMPLE
        mock_donation_point.country = "England"

        mock_holidays = {"england-and-wales": {"events": []}}

        with patch('givefood.models._get_bank_holidays', return_value=mock_holidays):
            from givefood.models import FoodbankDonationPoint
            result = FoodbankDonationPoint.opening_hours_days(mock_donation_point)

            for day in result:
                assert "day_name" in day
                assert "hours" in day
                assert "is_today" in day
                # day_name should not contain the hours part
                assert "–" not in day["day_name"]

    def test_opening_hours_days_splits_day_name_and_hours_correctly(self):
        """Test that day_name and hours are correctly split from the text."""
        mock_donation_point = MagicMock()
        mock_donation_point.opening_hours = OPENING_HOURS_SAMPLE
        mock_donation_point.country = "England"

        # Use a fixed date (a Wednesday) to make assertions predictable
        mock_holidays = {"england-and-wales": {"events": []}}

        with patch('givefood.models._get_bank_holidays', return_value=mock_holidays):
            with patch('givefood.models.date') as mock_date:
                mock_date.today.return_value = date(2026, 2, 16)  # A Monday
                mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
                from givefood.models import FoodbankDonationPoint
                result = FoodbankDonationPoint.opening_hours_days(mock_donation_point)

                # First day should be Monday (today in mock)
                assert result[0]["is_today"] is True
                # A weekday should have hours
                assert result[0]["hours"] == "9:00 AM – 5:00 PM"

    def test_opening_hours_days_is_today_only_for_first_day(self):
        """Test that is_today is True only for the first day (today)."""
        mock_donation_point = MagicMock()
        mock_donation_point.opening_hours = OPENING_HOURS_SAMPLE
        mock_donation_point.country = "England"

        mock_holidays = {"england-and-wales": {"events": []}}

        with patch('givefood.models._get_bank_holidays', return_value=mock_holidays):
            from givefood.models import FoodbankDonationPoint
            result = FoodbankDonationPoint.opening_hours_days(mock_donation_point)

            # Only the first day (today) should have is_today = True
            assert result[0]["is_today"] is True
            for day in result[1:]:
                assert day["is_today"] is False


class TestIsOpen:
    """Test is_open property of FoodbankDonationPoint."""

    def test_is_open_returns_none_without_opening_hours(self):
        """Test that is_open returns None when no opening hours are set."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = None

        from givefood.models import FoodbankDonationPoint
        assert FoodbankDonationPoint.is_open.fget(mock_dp) is None

    def test_is_open_returns_false_on_closed_day(self):
        """Test that is_open returns False when today is marked as Closed."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = OPENING_HOURS_SAMPLE  # Saturday and Sunday are Closed

        # Mock timezone.now() to a Saturday at noon
        mock_now = datetime(2026, 2, 14, 12, 0)  # Saturday
        from givefood.models import FoodbankDonationPoint
        with patch('givefood.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = mock_now
            assert FoodbankDonationPoint.is_open.fget(mock_dp) is False

    def test_is_open_returns_true_during_opening_hours(self):
        """Test that is_open returns True when current time is within opening hours."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = OPENING_HOURS_SAMPLE  # Mon-Fri 9am-5pm

        # Mock timezone.now() to a Monday at 2pm
        mock_now = datetime(2026, 2, 16, 14, 0)  # Monday
        from givefood.models import FoodbankDonationPoint
        with patch('givefood.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = mock_now
            assert FoodbankDonationPoint.is_open.fget(mock_dp) is True

    def test_is_open_returns_false_after_closing_time(self):
        """Test that is_open returns False after closing time (the bug from the issue)."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = OPENING_HOURS_SUNDAY_SAMPLE  # Sunday 10am-4pm

        # Mock timezone.now() to Sunday at 5pm (after 4pm closing)
        mock_now = datetime(2026, 2, 15, 17, 0)  # Sunday
        from givefood.models import FoodbankDonationPoint
        with patch('givefood.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = mock_now
            assert FoodbankDonationPoint.is_open.fget(mock_dp) is False

    def test_is_open_returns_false_before_opening_time(self):
        """Test that is_open returns False before opening time."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = OPENING_HOURS_SAMPLE  # Mon-Fri 9am-5pm

        # Mock timezone.now() to a Monday at 7am (before 9am opening)
        mock_now = datetime(2026, 2, 16, 7, 0)  # Monday
        from givefood.models import FoodbankDonationPoint
        with patch('givefood.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = mock_now
            assert FoodbankDonationPoint.is_open.fget(mock_dp) is False

    def test_is_open_returns_none_with_empty_opening_hours(self):
        """Test that is_open returns None with empty opening hours string."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = ""

        from givefood.models import FoodbankDonationPoint
        assert FoodbankDonationPoint.is_open.fget(mock_dp) is None

    def test_is_open_handles_hyphen_separator(self):
        """Test that is_open works with a regular hyphen separator."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = "Monday: 9:00 AM - 5:00 PM\nTuesday: 9:00 AM - 5:00 PM\nWednesday: 9:00 AM - 5:00 PM\nThursday: 9:00 AM - 5:00 PM\nFriday: 9:00 AM - 5:00 PM\nSaturday: Closed\nSunday: Closed"

        mock_now = datetime(2026, 2, 16, 14, 0)  # Monday at 2pm
        from givefood.models import FoodbankDonationPoint
        with patch('givefood.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = mock_now
            assert FoodbankDonationPoint.is_open.fget(mock_dp) is True

    def test_is_open_handles_em_dash_separator(self):
        """Test that is_open works with an em-dash separator."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = "Monday: 9:00 AM \u2014 5:00 PM\nTuesday: 9:00 AM \u2014 5:00 PM\nWednesday: 9:00 AM \u2014 5:00 PM\nThursday: 9:00 AM \u2014 5:00 PM\nFriday: 9:00 AM \u2014 5:00 PM\nSaturday: Closed\nSunday: Closed"

        mock_now = datetime(2026, 2, 16, 14, 0)  # Monday at 2pm
        from givefood.models import FoodbankDonationPoint
        with patch('givefood.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = mock_now
            assert FoodbankDonationPoint.is_open.fget(mock_dp) is True

    def test_is_open_handles_midnight_closing(self):
        """Test that is_open works when closing time is 12:00 AM (midnight)."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = OPENING_HOURS_MIDNIGHT_SAMPLE  # Mon 6am-12am

        # Monday at 5:13pm should be open (6am-midnight)
        mock_now = datetime(2026, 2, 16, 17, 13)  # Monday
        from givefood.models import FoodbankDonationPoint
        with patch('givefood.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = mock_now
            assert FoodbankDonationPoint.is_open.fget(mock_dp) is True

    def test_is_open_handles_midnight_closing_before_open(self):
        """Test that is_open returns False before opening when closing is midnight."""
        mock_dp = MagicMock()
        mock_dp.opening_hours = OPENING_HOURS_MIDNIGHT_SAMPLE  # Mon 6am-12am

        # Monday at 5am should be closed (before 6am)
        mock_now = datetime(2026, 2, 16, 5, 0)  # Monday
        from givefood.models import FoodbankDonationPoint
        with patch('givefood.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = mock_now
            assert FoodbankDonationPoint.is_open.fget(mock_dp) is False

