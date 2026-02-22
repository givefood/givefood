"""
Tests for the main givefood app utility functions.
"""
import logging
from unittest.mock import patch, MagicMock

import pytest
from unittest.mock import patch
from givefood.utils.geo import (
    _foodbank_queryset,
    distance_meters,
    geocode,
    geojson_dict,
    is_uk,
    miles,
    oc_geocode,
    pluscode,
)
from givefood.utils.text import (
    clean_foodbank_need_text,
    diff_html,
    text_for_comparison,
)


class TestTextUtilities:
    """Test text processing utility functions."""

    def test_text_for_comparison_lowercase(self):
        """Test that text_for_comparison converts to lowercase."""
        assert text_for_comparison("Hello World") == "helloworld"

    def test_text_for_comparison_removes_spaces(self):
        """Test that text_for_comparison removes spaces."""
        assert text_for_comparison("Hello World") == "helloworld"

    def test_text_for_comparison_removes_newlines(self):
        """Test that text_for_comparison removes newlines."""
        assert text_for_comparison("Hello\nWorld\r\n") == "helloworld"

    def test_text_for_comparison_removes_tabs(self):
        """Test that text_for_comparison removes tabs."""
        assert text_for_comparison("Hello\tWorld") == "helloworld"

    def test_text_for_comparison_removes_dots(self):
        """Test that text_for_comparison removes dots."""
        assert text_for_comparison("Hello.World.") == "helloworld"

    def test_text_for_comparison_none(self):
        """Test that text_for_comparison handles None."""
        assert text_for_comparison(None) is None

    def test_clean_foodbank_need_text_removes_double_spaces(self):
        """Test that clean_foodbank_need_text removes double spaces."""
        assert clean_foodbank_need_text("Hello  World") == "Hello World"

    def test_clean_foodbank_need_text_strips_whitespace(self):
        """Test that clean_foodbank_need_text strips whitespace."""
        assert clean_foodbank_need_text("  Hello World  ") == "Hello World"

    def test_clean_foodbank_need_text_removes_empty_lines(self):
        """Test that clean_foodbank_need_text removes empty lines."""
        text = "Line 1\n\nLine 2\n  \nLine 3"
        result = clean_foodbank_need_text(text)
        assert "\n\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_clean_foodbank_need_text_fixes_uht(self):
        """Test that clean_foodbank_need_text fixes UHT capitalization."""
        assert "UHT" in clean_foodbank_need_text("Uht milk")



class TestGeographicUtilities:
    """Test geographic utility functions."""

    def test_is_uk_valid_location(self):
        """Test is_uk with a valid UK location (London)."""
        assert is_uk("51.5074,-0.1278") is True

    def test_is_uk_scotland(self):
        """Test is_uk with a valid Scottish location."""
        assert is_uk("55.9533,-3.1883") is True

    def test_is_uk_invalid_location_usa(self):
        """Test is_uk with a location outside UK (USA)."""
        assert is_uk("40.7128,-74.0060") is False

    def test_is_uk_invalid_location_france(self):
        """Test is_uk with a location outside UK (France)."""
        assert is_uk("48.8566,2.3522") is False

    def test_miles_conversion_zero(self):
        """Test miles conversion with zero meters."""
        assert miles(0) == 0

    def test_miles_conversion_1000_meters(self):
        """Test miles conversion with 1000 meters."""
        result = miles(1000)
        assert 0.62 < result < 0.63

    def test_miles_conversion_1609_meters(self):
        """Test miles conversion with 1609 meters (approximately 1 mile)."""
        result = miles(1609)
        assert 0.99 < result < 1.01

    def test_distance_meters_same_point(self):
        """Test distance calculation between the same point."""
        distance = distance_meters(51.5074, -0.1278, 51.5074, -0.1278)
        assert distance == 0

    def test_distance_meters_london_to_manchester(self):
        """Test distance calculation from London to Manchester."""
        # London: 51.5074, -0.1278
        # Manchester: 53.4808, -2.2426
        distance = distance_meters(51.5074, -0.1278, 53.4808, -2.2426)
        # Distance should be around 260-270 km (260000-270000 meters)
        assert 250000 < distance < 280000


class TestDiffUtilities:
    """Test diff utility functions."""

    def test_diff_html_no_change(self):
        """Test diff_html with identical strings."""
        result = diff_html(["line1"], ["line1"])
        assert result == ""

    def test_diff_html_addition(self):
        """Test diff_html with added line."""
        result = diff_html(["line1"], ["line1", "line2"])
        assert "<ins>" in result
        assert "line2" in result

    def test_diff_html_deletion(self):
        """Test diff_html with deleted line."""
        result = diff_html(["line1", "line2"], ["line1"])
        assert "<del>" in result
        assert "line2" in result


class TestJSONUtilities:
    """Test JSON utility functions."""

    def test_geojson_dict_valid_json(self):
        """Test geojson_dict with valid JSON."""
        json_str = '{"type": "Point", "coordinates": [0, 0]}'
        result = geojson_dict(json_str)
        assert result["type"] == "Point"
        assert result["coordinates"] == [0, 0]

    def test_geojson_dict_with_trailing_comma(self):
        """Test geojson_dict removes trailing comma."""
        json_str = '{"type": "Point"},'
        result = geojson_dict(json_str)
        assert result["type"] == "Point"

    def test_geojson_dict_with_whitespace(self):
        """Test geojson_dict handles leading/trailing whitespace."""
        json_str = '  {"type": "Point"}  '
        result = geojson_dict(json_str)
        assert result["type"] == "Point"


class TestGetUserIP:
    """Test get_user_ip utility function."""

    def test_get_user_ip_with_cloudflare_header(self):
        """Test get_user_ip with CF-Connecting-IP header."""
        from givefood.utils.text import get_user_ip
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', HTTP_CF_CONNECTING_IP='203.0.113.50')
        
        assert get_user_ip(request) == '203.0.113.50'

    def test_get_user_ip_with_x_forwarded_for(self):
        """Test get_user_ip with X-Forwarded-For header."""
        from givefood.utils.text import get_user_ip
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_FORWARDED_FOR='198.51.100.25, 192.168.1.1')
        
        assert get_user_ip(request) == '198.51.100.25'

    def test_get_user_ip_cloudflare_takes_precedence(self):
        """Test that CF-Connecting-IP takes precedence over X-Forwarded-For."""
        from givefood.utils.text import get_user_ip
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get(
            '/',
            HTTP_CF_CONNECTING_IP='203.0.113.50',
            HTTP_X_FORWARDED_FOR='198.51.100.25, 192.168.1.1'
        )
        
        assert get_user_ip(request) == '203.0.113.50'

    def test_get_user_ip_fallback_to_remote_addr(self):
        """Test get_user_ip falls back to REMOTE_ADDR."""
        from givefood.utils.text import get_user_ip
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        # RequestFactory sets REMOTE_ADDR to '127.0.0.1' by default
        
        assert get_user_ip(request) == '127.0.0.1'

    def test_get_user_ip_x_forwarded_for_with_spaces(self):
        """Test get_user_ip strips spaces from X-Forwarded-For header."""
        from givefood.utils.text import get_user_ip
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_FORWARDED_FOR=' 198.51.100.25 , 192.168.1.1')
        
        assert get_user_ip(request) == '198.51.100.25'


class TestPlusCode:
    """Test Plus Code (Open Location Code) generation."""

    def test_pluscode_generates_global_code(self):
        """Test that pluscode generates a valid global Plus Code."""
        result = pluscode("51.5117,-0.0772")
        assert "global" in result
        assert result["global"].startswith("9C")  # UK codes start with 9C
        assert "+" in result["global"]

    def test_pluscode_generates_compound_with_locality(self):
        """Test that pluscode generates compound code with locality."""
        result = pluscode("51.5117,-0.0772", "Hackney")
        assert "compound" in result
        assert "Hackney" in result["compound"]
        assert "+" in result["compound"]

    def test_pluscode_generates_compound_without_locality(self):
        """Test that pluscode generates compound code without locality."""
        result = pluscode("51.5117,-0.0772")
        assert "compound" in result
        assert "+" in result["compound"]
        # Compound should be the local code (4+2 characters with +)
        assert len(result["compound"]) == 7  # e.g., "GW6F+M4"

    def test_pluscode_with_none_locality(self):
        """Test that pluscode handles None locality."""
        result = pluscode("51.5117,-0.0772", None)
        assert "global" in result
        assert "compound" in result
        # Compound should not contain "None"
        assert "None" not in result["compound"]

    def test_pluscode_invalid_input_returns_empty_dict(self):
        """Test that pluscode returns empty dict for invalid input."""
        result = pluscode("invalid")
        assert result == {}

    def test_pluscode_empty_string_returns_empty_dict(self):
        """Test that pluscode returns empty dict for empty string."""
        result = pluscode("")
        assert result == {}

    def test_pluscode_known_location(self):
        """Test pluscode for a known London location."""
        # Coordinates for London (Shoreditch area)
        result = pluscode("51.5117,-0.0772", "City of London")
        assert result["global"] == "9C3XGW6F+M4"
        assert result["compound"] == "GW6F+M4 City of London"


class TestGeocode:
    """Test geocode function exception handling."""

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_geocode_empty_results_returns_fallback(self, mock_get, mock_cred):
        """Test geocode returns '0,0' when results array is empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        result = geocode("some address")
        assert result == "0,0"

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_geocode_missing_key_returns_fallback(self, mock_get, mock_cred):
        """Test geocode returns '0,0' when expected keys are missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"geometry": {}}]}
        mock_get.return_value = mock_response

        result = geocode("some address")
        assert result == "0,0"

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_geocode_logs_warning_on_failure(self, mock_get, mock_cred, caplog):
        """Test geocode logs a warning when parsing fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        with caplog.at_level(logging.WARNING):
            geocode("test address")
        assert "Failed to geocode address" in caplog.text

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_geocode_success(self, mock_get, mock_cred):
        """Test geocode returns correct lat_lng on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"geometry": {"location": {"lat": 51.5, "lng": -0.1}}}]
        }
        mock_get.return_value = mock_response

        result = geocode("London")
        assert result == "51.5,-0.1"

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_geocode_non_200_returns_fallback(self, mock_get, mock_cred):
        """Test geocode returns '0,0' when API returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = geocode("some address")
        assert result == "0,0"


class TestOcGeocode:
    """Test oc_geocode function exception handling."""

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_oc_geocode_empty_results_returns_fallback(self, mock_get, mock_cred):
        """Test oc_geocode returns '0,0' when results array is empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        result = oc_geocode("some address")
        assert result == "0,0"

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_oc_geocode_missing_key_returns_fallback(self, mock_get, mock_cred):
        """Test oc_geocode returns '0,0' when expected keys are missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"geometry": {}}]}
        mock_get.return_value = mock_response

        result = oc_geocode("some address")
        assert result == "0,0"

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_oc_geocode_logs_warning_on_failure(self, mock_get, mock_cred, caplog):
        """Test oc_geocode logs a warning when parsing fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        with caplog.at_level(logging.WARNING):
            oc_geocode("test address")
        assert "Failed to geocode address with OpenCage" in caplog.text

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_oc_geocode_success(self, mock_get, mock_cred):
        """Test oc_geocode returns correct lat_lng on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"geometry": {"lat": 51.5, "lng": -0.1}}]
        }
        mock_get.return_value = mock_response

        result = oc_geocode("London")
        assert result == "51.5,-0.1"

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_oc_geocode_non_200_returns_fallback(self, mock_get, mock_cred):
        """Test oc_geocode returns '0,0' when API returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = oc_geocode("some address")
        assert result == "0,0"

class TestFoodbankQueryset:
    """Test _foodbank_queryset helper function."""

    @patch("django.utils.translation.get_language", return_value="en")
    def test_foodbank_queryset_english_no_translation_prefetch(self, mock_lang):
        """Test that English language does not add translation prefetch."""
        qs = _foodbank_queryset()
        prefetches = [p.prefetch_through for p in qs._prefetch_related_lookups]
        assert "latest_need__foodbankchangetranslation_set" not in prefetches

    @patch("django.utils.translation.get_language", return_value="es")
    def test_foodbank_queryset_non_english_adds_translation_prefetch(self, mock_lang):
        """Test that non-English language adds translation prefetch."""
        qs = _foodbank_queryset()
        prefetches = [p.prefetch_through for p in qs._prefetch_related_lookups]
        assert "latest_need__foodbankchangetranslation_set" in prefetches

    @patch("django.utils.translation.get_language", return_value=None)
    def test_foodbank_queryset_none_language_no_translation_prefetch(self, mock_lang):
        """Test that None language does not add translation prefetch."""
        qs = _foodbank_queryset()
        prefetches = [p.prefetch_through for p in qs._prefetch_related_lookups]
        assert "latest_need__foodbankchangetranslation_set" not in prefetches
