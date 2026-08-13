"""
Tests for the main givefood app utility functions.
"""
import json
import logging
from unittest.mock import patch, MagicMock

import pytest
from unittest.mock import patch
from givefood.utils.geo import (
    foodbank_queryset,
    distance_meters,
    geocode,
    geojson_dict,
    get_place_id,
    is_uk,
    miles,
    oc_geocode,
    pluscode,
)
from givefood.utils.text import (
    clean_foodbank_need_text,
    diff_html,
    htmlbodytext,
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

    def test_htmlbodytext_extracts_body_text(self):
        """Test that htmlbodytext extracts text from body."""
        html = "<html><body><p>Hello World</p></body></html>"
        assert "Hello World" in htmlbodytext(html)

    def test_htmlbodytext_no_body(self):
        """Test that htmlbodytext returns False when no body tag."""
        assert htmlbodytext("<html><head></head></html>") is False

    def test_htmlbodytext_removes_script_content(self):
        """Test that htmlbodytext removes script tags and their content."""
        html = "<html><body><p>Hello</p><script>var x = 1;</script><p>World</p></body></html>"
        result = htmlbodytext(html)
        assert "Hello" in result
        assert "World" in result
        assert "var x" not in result

    def test_htmlbodytext_removes_style_content(self):
        """Test that htmlbodytext removes style tags and their content."""
        html = "<html><body><p>Hello</p><style>.red { color: red; }</style></body></html>"
        result = htmlbodytext(html)
        assert "Hello" in result
        assert "color" not in result

    def test_htmlbodytext_removes_svg_content(self):
        """Test that htmlbodytext removes svg tags and their content."""
        html = "<html><body><p>Hello</p><svg><title>Chart</title><desc>A bar chart</desc><text x='10' y='20'>Label</text></svg></body></html>"
        result = htmlbodytext(html)
        assert "Hello" in result
        assert "Chart" not in result
        assert "bar chart" not in result
        assert "Label" not in result

    def test_htmlbodytext_removes_iframe_content(self):
        """Test that htmlbodytext removes iframe tags and their content."""
        html = "<html><body><p>Hello</p><iframe>Fallback text</iframe></body></html>"
        result = htmlbodytext(html)
        assert "Hello" in result
        assert "Fallback" not in result

    def test_htmlbodytext_removes_canvas_content(self):
        """Test that htmlbodytext removes canvas tags and their content."""
        html = "<html><body><p>Hello</p><canvas>Canvas not supported</canvas></body></html>"
        result = htmlbodytext(html)
        assert "Hello" in result
        assert "Canvas not supported" not in result

    def test_htmlbodytext_removes_multiple_unwanted_tags(self):
        """Test that htmlbodytext removes multiple unwanted tags at once."""
        html = "<html><body><p>Content</p><script>js()</script><style>css{}</style><svg><text>chart label</text></svg><iframe>if</iframe><canvas>cv</canvas></body></html>"
        result = htmlbodytext(html)
        assert "Content" in result
        assert "js()" not in result
        assert "css{}" not in result
        assert "chart label" not in result
        assert "if" not in result
        assert "cv" not in result



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


class TestGetPlaceId:
    """Test get_place_id function exception handling."""

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_get_place_id_success(self, mock_get, mock_cred):
        """Test get_place_id returns correct place_id on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"place_id": "ChIJdd4hrwug2EcRmSrV3Vo6llI"}]
        }
        mock_get.return_value = mock_response

        result = get_place_id("London")
        assert result == "ChIJdd4hrwug2EcRmSrV3Vo6llI"

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_get_place_id_non_200_returns_none(self, mock_get, mock_cred):
        """Test get_place_id returns None when API returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_place_id("some address")
        assert result is None

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_get_place_id_empty_results_returns_none(self, mock_get, mock_cred):
        """Test get_place_id returns None when results array is empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        result = get_place_id("some address")
        assert result is None

    @patch("givefood.utils.geo.get_cred", return_value="fake_key")
    @patch("givefood.utils.geo.requests.get")
    def test_get_place_id_missing_key_returns_none(self, mock_get, mock_cred):
        """Test get_place_id returns None when place_id key is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"geometry": {}}]}
        mock_get.return_value = mock_response

        result = get_place_id("some address")
        assert result is None


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
    """Test foodbank_queryset helper function."""

    @patch("django.utils.translation.get_language", return_value="en")
    def test_foodbank_queryset_english_no_translation_prefetch(self, mock_lang):
        """Test that English language does not add translation prefetch."""
        qs = foodbank_queryset()
        prefetches = [p.prefetch_through for p in qs._prefetch_related_lookups]
        assert "latest_need__foodbankchangetranslation_set" not in prefetches

    @patch("django.utils.translation.get_language", return_value="es")
    def test_foodbank_queryset_non_english_adds_translation_prefetch(self, mock_lang):
        """Test that non-English language adds translation prefetch."""
        qs = foodbank_queryset()
        prefetches = [p.prefetch_through for p in qs._prefetch_related_lookups]
        assert "latest_need__foodbankchangetranslation_set" in prefetches

    @patch("django.utils.translation.get_language", return_value=None)
    def test_foodbank_queryset_none_language_no_translation_prefetch(self, mock_lang):
        """Test that None language does not add translation prefetch."""
        qs = foodbank_queryset()
        prefetches = [p.prefetch_through for p in qs._prefetch_related_lookups]
        assert "latest_need__foodbankchangetranslation_set" not in prefetches


class TestGemini:
    """Test gemini utility function."""

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.genai")
    def test_gemini_returns_parsed_when_available(self, mock_genai, mock_cred):
        """Test that gemini returns response.parsed when it is not None."""
        from givefood.utils.ai import gemini

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = [{"name": "Pasta", "quantity": 2}]
        mock_client.models.generate_content.return_value = mock_response

        result = gemini("test prompt", 0.5, response_schema={"type": "array"})
        assert result == [{"name": "Pasta", "quantity": 2}]

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.genai")
    def test_gemini_falls_back_to_text_json_parsing(self, mock_genai, mock_cred):
        """Test that gemini parses response.text as JSON when parsed is None."""
        from givefood.utils.ai import gemini

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = None
        mock_response.text = '"Pasta"'
        mock_client.models.generate_content.return_value = mock_response

        result = gemini("test prompt", 0.1)
        assert result == "Pasta"

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.genai")
    def test_gemini_strips_text_on_json_decode_error(self, mock_genai, mock_cred):
        """Test that gemini strips and returns text when JSON decode fails."""
        from givefood.utils.ai import gemini

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = None
        mock_response.text = "Pasta\n"
        mock_client.models.generate_content.return_value = mock_response

        result = gemini("test prompt", 0.1)
        assert result == "Pasta"

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.genai")
    def test_gemini_returns_none_when_text_is_none(self, mock_genai, mock_cred):
        """Test that gemini returns None when both parsed and text are None."""
        from givefood.utils.ai import gemini

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = None
        mock_response.text = None
        mock_client.models.generate_content.return_value = mock_response

        result = gemini("test prompt", 0.1)
        assert result is None

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.genai")
    def test_gemini_timeout_sets_http_options(self, mock_genai, mock_cred):
        """Test that a timeout (seconds) is sent as http_options in milliseconds."""
        from givefood.utils.ai import gemini

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = {"needed": [], "excess": []}
        mock_client.models.generate_content.return_value = mock_response

        gemini("test prompt", 0, timeout=120)

        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.http_options is not None
        assert config.http_options.timeout == 120000

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.genai")
    def test_gemini_no_timeout_omits_http_options(self, mock_genai, mock_cred):
        """Test that http_options is omitted when no timeout is given."""
        from givefood.utils.ai import gemini

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = {"needed": [], "excess": []}
        mock_client.models.generate_content.return_value = mock_response

        gemini("test prompt", 0)

        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.http_options is None

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.genai")
    def test_gemini_return_usage_returns_tuple(self, mock_genai, mock_cred):
        """Test that return_usage=True returns a (result, usage_metadata) tuple."""
        from givefood.utils.ai import gemini

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = {"needed": [], "excess": []}
        mock_response.usage_metadata = MagicMock(total_token_count=1613)
        mock_client.models.generate_content.return_value = mock_response

        result, usage = gemini("test prompt", 0, return_usage=True)
        assert result == {"needed": [], "excess": []}
        assert usage.total_token_count == 1613

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.genai")
    def test_gemini_default_returns_bare_result(self, mock_genai, mock_cred):
        """Test that without return_usage the result is returned directly (not a tuple)."""
        from givefood.utils.ai import gemini

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.parsed = {"needed": [], "excess": []}
        mock_client.models.generate_content.return_value = mock_response

        result = gemini("test prompt", 0)
        assert result == {"needed": [], "excess": []}
        assert not isinstance(result, tuple)


class TestGetMarkdown:
    """Test get_markdown utility function (Cloudflare Browser Rendering)."""

    @patch("givefood.utils.general.get_cred", side_effect=lambda n: {"cf_account_id": "acct123", "cf_need_browser_render": "tok456"}[n])
    @patch("givefood.utils.general.requests.post")
    def test_get_markdown_returns_result(self, mock_post, mock_cred):
        """Test that get_markdown posts to the markdown endpoint and returns the result."""
        from givefood.utils.general import get_markdown

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "result": "# Needs\n- Beans"}
        mock_post.return_value = mock_response

        result = get_markdown("https://example.org/needs")
        assert result == "# Needs\n- Beans"

        call = mock_post.call_args
        assert call.args[0] == "https://api.cloudflare.com/client/v4/accounts/acct123/browser-rendering/markdown"
        assert call.kwargs["json"]["url"] == "https://example.org/needs"
        assert call.kwargs["headers"]["Authorization"] == "Bearer tok456"

    @patch("givefood.utils.general.get_cred", side_effect=lambda n: "x")
    @patch("givefood.utils.general.requests.post")
    def test_get_markdown_returns_none_on_error_status(self, mock_post, mock_cred):
        """Test that get_markdown returns None on a non-200 response."""
        from givefood.utils.general import get_markdown

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        assert get_markdown("https://example.org/needs") is None

    @patch("givefood.utils.general.get_cred", side_effect=lambda n: "x")
    @patch("givefood.utils.general.requests.post")
    def test_get_markdown_returns_none_on_unsuccessful_payload(self, mock_post, mock_cred):
        """Test that get_markdown returns None when the API reports success=False."""
        from givefood.utils.general import get_markdown

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": False, "errors": ["boom"]}
        mock_post.return_value = mock_response

        assert get_markdown("https://example.org/needs") is None

    @patch("givefood.utils.general.get_cred", side_effect=lambda n: "x")
    @patch("givefood.utils.general.requests.post", side_effect=__import__("requests").exceptions.Timeout)
    def test_get_markdown_returns_none_on_request_exception(self, mock_post, mock_cred):
        """Test that get_markdown returns None when the request raises."""
        from givefood.utils.general import get_markdown

        assert get_markdown("https://example.org/needs") is None

    @patch("givefood.utils.general.get_cred", side_effect=lambda n: "x")
    @patch("givefood.utils.general.requests.post")
    def test_get_markdown_returns_none_on_challenge_page(self, mock_post, mock_cred):
        """Test that an anti-bot interstitial page is treated as a failed render (None)."""
        from givefood.utils.general import get_markdown

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "result": "Please wait while we verify you're not a robot! Loading...",
        }
        mock_post.return_value = mock_response

        assert get_markdown("https://example.org/needs") is None
        # all attempts should have been made against the challenge page
        assert mock_post.call_count == 3

    @patch("givefood.utils.general.get_cred", side_effect=lambda n: "x")
    @patch("givefood.utils.general.requests.post")
    def test_get_markdown_retries_past_challenge(self, mock_post, mock_cred):
        """Test that get_markdown retries and returns real content after a challenge page."""
        from givefood.utils.general import get_markdown

        challenge = MagicMock()
        challenge.status_code = 200
        challenge.json.return_value = {"success": True, "result": "Just a moment..."}
        good = MagicMock()
        good.status_code = 200
        good.json.return_value = {"success": True, "result": "# Needs\n- Beans"}
        mock_post.side_effect = [challenge, good]

        assert get_markdown("https://example.org/needs") == "# Needs\n- Beans"
        assert mock_post.call_count == 2

    @patch("givefood.utils.general.get_cred", side_effect=lambda n: "x")
    @patch("givefood.utils.general.requests.post")
    def test_get_markdown_relaxes_wait_until_on_last_attempt(self, mock_post, mock_cred):
        """Test that a site which never reaches network idle falls back to networkidle2."""
        from givefood.utils.general import get_markdown

        timeout = MagicMock()
        timeout.status_code = 422
        good = MagicMock()
        good.status_code = 200
        good.json.return_value = {"success": True, "result": "# Needs\n- Beans"}
        mock_post.side_effect = [timeout, timeout, good]

        assert get_markdown("https://example.org/needs") == "# Needs\n- Beans"
        wait_untils = [call.kwargs["json"]["gotoOptions"]["waitUntil"] for call in mock_post.call_args_list]
        assert wait_untils == ["networkidle0", "networkidle0", "networkidle2"]

    @patch("givefood.utils.general.get_cred", side_effect=lambda n: "x")
    @patch("givefood.utils.general.requests.post")
    def test_get_markdown_strips_inlined_data_uris(self, mock_post, mock_cred):
        """Test that an image inlined as a data: URI is dropped but its line's real content stays."""
        from givefood.utils.general import get_markdown

        # Cardiff's header: two logos inlined on the same line as the nav links. The URL-encoded
        # SVG carries spaces and quotes, and the page's own text sits on later lines.
        logo = "data:image/svg+xml,%3csvg id='a' xmlns='http://www.w3.org/2000/svg'%3e" + ("A" * 500) + "%3c/svg%3e"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "result": (
            "[![](<%s>) Donate](https://example.org/donate) [![](<%s>)](https://example.org)\n"
            "\n### Most needed items\n\n- Beans\n\n### We have plenty of...\n\n- Nappies\n- Pasta\n" % (logo, logo)
        )}
        mock_post.return_value = mock_response

        result = get_markdown("https://example.org/needs")
        assert "data:" not in result
        assert "AAAA" not in result
        # The nav links share the line with the logos, and the lists come after them.
        assert "[![]() Donate](https://example.org/donate)" in result
        assert "- Beans" in result
        assert "- Nappies" in result
        assert "- Pasta" in result

    def test_strip_data_uris_stops_at_the_end_of_a_line(self):
        """Test that a data: URI match can't run on into content further down the page."""
        from givefood.utils.general import _strip_data_uris

        # An unbounded match would span from the first "(<data:" to the last ">)" and eat
        # everything in between, because the markdown has no literal angle brackets to stop it.
        markdown = "![](<data:image/png;base64,AAAA>)\n\n- Nappies\n- Pasta\n\n![](<data:image/png;base64,BBBB>)\n"
        result = _strip_data_uris(markdown)
        assert result == "![]()\n\n- Nappies\n- Pasta\n\n![]()\n"

    def test_strip_data_uris_leaves_ordinary_links_alone(self):
        """Test that links which merely mention data are untouched."""
        from givefood.utils.general import _strip_data_uris

        markdown = "[Our data](https://example.org/data)\n\n- Tinned Potatoes\n"
        assert _strip_data_uris(markdown) == markdown


class TestOpenrouter:
    """Test openrouter utility function."""

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.requests.post")
    def test_openrouter_json_schema_format(self, mock_post, mock_cred):
        """Test that openrouter sends json_schema response_format when schema is provided."""
        from givefood.utils.ai import openrouter

        mock_response = MagicMock()
        mock_post.return_value = mock_response

        schema = {"type": "object", "properties": {"needed": {"type": "array", "items": {"type": "string"}}}, "required": ["needed"]}
        openrouter("test prompt", 0, "google/gemini-2.5-flash", response_schema=schema)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["response_format"]["json_schema"]["schema"] == schema

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.requests.post")
    def test_openrouter_json_object_format(self, mock_post, mock_cred):
        """Test that openrouter sends json_object response_format when type is json_object."""
        from givefood.utils.ai import openrouter

        mock_response = MagicMock()
        mock_post.return_value = mock_response

        openrouter("test prompt", 0, "amazon/nova-micro-v1", response_format_type="json_object")

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["response_format"] == {"type": "json_object"}

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.requests.post")
    def test_openrouter_no_response_format_by_default(self, mock_post, mock_cred):
        """Test that openrouter omits response_format when no schema and default type."""
        from givefood.utils.ai import openrouter

        mock_response = MagicMock()
        mock_post.return_value = mock_response

        openrouter("test prompt", 0, "google/gemini-2.5-flash")

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert "response_format" not in payload

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.requests.post")
    def test_openrouter_reasoning_disabled(self, mock_post, mock_cred):
        """Test that openrouter sends reasoning.enabled False when reasoning is False."""
        from givefood.utils.ai import openrouter

        mock_response = MagicMock()
        mock_post.return_value = mock_response

        openrouter("test prompt", 0, "qwen/qwen3.5-flash-02-23", reasoning=False)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["reasoning"] == {"enabled": False}

    @patch("givefood.utils.ai.get_cred", return_value="fake_api_key")
    @patch("givefood.utils.ai.requests.post")
    def test_openrouter_no_reasoning_by_default(self, mock_post, mock_cred):
        """Test that openrouter omits reasoning when not specified."""
        from givefood.utils.ai import openrouter

        mock_response = MagicMock()
        mock_post.return_value = mock_response

        openrouter("test prompt", 0, "google/gemini-2.5-flash")

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert "reasoning" not in payload
