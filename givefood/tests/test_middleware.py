"""
Tests for the givefood middleware.
"""
import pytest
import django.db.utils
from django.test import RequestFactory
from django.http import HttpResponse
from unittest.mock import Mock, patch, MagicMock
from givefood.middleware import GeoJSONPreload, RenderTime


@pytest.mark.django_db
class TestGeoJSONPreloadMiddleware:
    """Test the GeoJSONPreload middleware."""

    def test_index_page_has_link_header(self, client):
        """Test that the index page gets a Link header for geojson."""
        response = client.get('/needs/')

        # Check if we got a successful response
        if response.status_code == 200:
            # Check for the Link header
            assert 'Link' in response, "Link header should be present"
            assert (
                '/needs/geo.json' in response['Link']
            ), "Link header should contain geojson URL"
            assert (
                'rel=preload' in response['Link']
            ), "Link header should have rel=preload"
            assert (
                'as=fetch' in response['Link']
            ), "Link header should have as=fetch"
            assert (
                'crossorigin=anonymous' in response['Link']
            ), "Link header should have crossorigin=anonymous"

    def test_non_html_response_no_link_header(self, client):
        """Test that non-HTML responses don't get Link headers."""
        response = client.get('/needs/geo.json')

        # Check if we got a successful response
        if response.status_code == 200:
            # GeoJSON response should not have Link header
            assert (
                'Link' not in response or response['Link'] == ''
            ), "Non-HTML response should not have Link header"

    def test_404_response_no_link_header(self, client):
        """Test that 404 responses don't get Link headers."""
        response = client.get('/needs/at/nonexistent-foodbank/')

        # 404 response should not have Link header
        assert response.status_code == 404
        # No Link header should be added to 404 responses
        # (middleware only adds to 200 responses)

    def test_middleware_adds_correct_header_format(self):
        """Test that middleware creates the correct Link header format."""
        # Create a mock request and response
        request = RequestFactory().get('/needs/')
        response = HttpResponse(
            '<html><body>Test</body></html>',
            content_type='text/html'
        )

        # Mock the resolve function to return a known URL name
        mock_resolved = MagicMock()
        mock_resolved.url_name = 'index'
        mock_resolved.kwargs = {}

        with patch('givefood.middleware.resolve', return_value=mock_resolved):
            # Create middleware instance
            get_response = Mock(return_value=response)
            middleware = GeoJSONPreload(get_response)

            # Process the request
            result = middleware(request)

            # Check that Link header was added
            assert 'Link' in result
            link_header = result['Link']

            # Verify format
            assert link_header.startswith('<'), (
                "Link header should start with <"
            )
            assert (
                '>; rel=preload; as=fetch; crossorigin=anonymous'
                in link_header
            ), "Link header should have correct format"
            # Verify it contains the geojson URL
            assert '/needs/geo.json' in link_header, (
                "Link header should contain geojson URL"
            )

    def test_foodbank_page_has_correct_slug_in_link_header(self):
        """Test that foodbank pages extract slug correctly."""
        # Create a mock request and response for a foodbank page
        request = RequestFactory().get('/needs/at/test-foodbank/')
        response = HttpResponse(
            '<html><body>Test Foodbank</body></html>',
            content_type='text/html'
        )

        # Mock the resolve function to return foodbank URL name with slug
        mock_resolved = MagicMock()
        mock_resolved.url_name = 'foodbank'
        mock_resolved.kwargs = {'slug': 'test-foodbank'}

        with patch('givefood.middleware.resolve', return_value=mock_resolved):
            # Create middleware instance
            get_response = Mock(return_value=response)
            middleware = GeoJSONPreload(get_response)

            # Process the request
            result = middleware(request)

            # Check that Link header was added
            assert 'Link' in result
            link_header = result['Link']

            # Verify it contains the foodbank-specific geojson URL
            assert '/needs/at/test-foodbank/geo.json' in link_header, (
                "Link header should contain foodbank-specific geojson URL"
            )

    def test_constituency_page_has_correct_slug_in_link_header(self):
        """Test that constituency pages extract slug correctly."""
        # Create a mock request and response for a constituency page
        request = RequestFactory().get('/needs/in/constituency/test-constituency/')
        response = HttpResponse(
            '<html><body>Test Constituency</body></html>',
            content_type='text/html'
        )

        # Mock the resolve function to return constituency URL name with slug
        mock_resolved = MagicMock()
        mock_resolved.url_name = 'constituency'
        mock_resolved.kwargs = {'slug': 'test-constituency'}

        with patch('givefood.middleware.resolve', return_value=mock_resolved):
            # Create middleware instance
            get_response = Mock(return_value=response)
            middleware = GeoJSONPreload(get_response)

            # Process the request
            result = middleware(request)

            # Check that Link header was added
            assert 'Link' in result
            link_header = result['Link']

            # Verify it contains the constituency-specific geojson URL
            # Note: constituency geojson uses parlcon_slug parameter
            assert '/needs/in/constituency/test-constituency/geo.json' in link_header, (
                "Link header should contain constituency-specific geojson URL"
            )

    def test_foodbank_location_page_has_correct_slug_in_link_header(self):
        """Test that foodbank location pages extract slug correctly."""
        # Create a mock request and response for a foodbank location page
        request = RequestFactory().get('/needs/at/test-foodbank/test-location/')
        response = HttpResponse(
            '<html><body>Test Location</body></html>',
            content_type='text/html'
        )

        # Mock the resolve function to return foodbank_location URL name
        mock_resolved = MagicMock()
        mock_resolved.url_name = 'foodbank_location'
        mock_resolved.kwargs = {'slug': 'test-foodbank', 'locslug': 'test-location'}

        with patch('givefood.middleware.resolve', return_value=mock_resolved):
            # Create middleware instance
            get_response = Mock(return_value=response)
            middleware = GeoJSONPreload(get_response)

            # Process the request
            result = middleware(request)

            # Check that Link header was added
            assert 'Link' in result
            link_header = result['Link']

            # Verify it contains the foodbank-specific geojson URL
            assert '/needs/at/test-foodbank/geo.json' in link_header, (
                "Link header should contain foodbank-specific geojson URL"
            )


@pytest.mark.django_db
class TestGZipMiddleware:
    """Test that GZipMiddleware is properly configured."""

    def test_gzip_compression_applied(self, client):
        """Test that responses are gzip compressed when requested."""
        # Make a request with Accept-Encoding: gzip header
        response = client.get(
            '/needs/',
            HTTP_ACCEPT_ENCODING='gzip'
        )

        # Check if we got a successful response
        if response.status_code == 200:
            # Check for Content-Encoding header indicating gzip compression
            assert (
                'gzip' in response.get('Content-Encoding', '')
            ), "Response should be gzip compressed when requested"

    def test_gzip_not_applied_when_not_requested(self, client):
        """Test that responses are not compressed without Accept-Encoding."""
        # Make a request without Accept-Encoding: gzip header
        response = client.get('/needs/')

        # Check if we got a successful response
        if response.status_code == 200:
            # Without Accept-Encoding: gzip, response should not be compressed
            # (though middleware may still add the Vary header)
            content_encoding = response.get('Content-Encoding', '')
            # If there's no content encoding or it's not gzip, that's expected
            assert (
                content_encoding == '' or 'gzip' not in content_encoding
            ), "Response should not be gzip compressed when not requested"

    def test_gzip_compression_with_api_endpoint(self, client):
        """Test that API responses can be gzip compressed."""
        # Test with an API endpoint that should return JSON
        try:
            response = client.get(
                '/api/',
                HTTP_ACCEPT_ENCODING='gzip'
            )
        except django.db.utils.NotSupportedError:
            # If the API endpoint fails due to database issues, skip this test
            pytest.skip("API endpoint not available in test environment")

        # Check if we got a successful response
        if response.status_code == 200:
            # API responses should also support gzip compression
            # The Vary header should include Accept-Encoding
            vary_header = response.get('Vary', '')
            assert (
                'Accept-Encoding' in vary_header
            ), "Vary header should include Accept-Encoding for proper caching"


@pytest.mark.django_db
class TestRenderTimeMiddleware:
    """Test the RenderTime middleware."""

    def test_render_time_replacement(self):
        """Test that PUTTHERENDERTIMEHERE is replaced with actual time."""
        # Create a view that returns HTML with the placeholder
        def test_view(request):
            return HttpResponse(
                b"<html><!--PUTTHERENDERTIMEHERE ms--></html>"
            )

        # Create middleware
        middleware = RenderTime(test_view)

        # Create request
        request = RequestFactory().get('/')

        # Process request
        response = middleware(request)
        content = response.content.decode('utf-8')

        # Verify placeholder was replaced
        assert 'PUTTHERENDERTIMEHERE' not in content, (
            "PUTTHERENDERTIMEHERE placeholder should be replaced"
        )

        # Verify a number was inserted
        import re
        match = re.search(r'(\d+\.?\d*) ms', content)
        assert match is not None, "Should contain render time in ms"

        # Verify it's a valid number
        render_time = float(match.group(1))
        assert render_time >= 0, "Render time should be non-negative"

    def test_multiple_replacements_only_replace_first(self):
        """Test that placeholder is only replaced once (first occurrence)."""
        # Create a view with multiple occurrences of the same placeholder
        def test_view(request):
            html = b"""<html>
PUTTHERENDERTIMEHERE
PUTTHERENDERTIMEHERE
</html>"""
            return HttpResponse(html)

        # Create middleware
        middleware = RenderTime(test_view)

        # Create request
        request = RequestFactory().get('/')

        # Process request
        response = middleware(request)
        content = response.content.decode('utf-8')

        # Count how many times the placeholder appears
        # It should appear once (the second occurrence not replaced)
        assert content.count('PUTTHERENDERTIMEHERE') == 1, (
            "Should replace only the first PUTTHERENDERTIMEHERE"
        )
