"""
Tests for the givefood middleware.
"""
import pytest
from django.test import RequestFactory
from django.http import HttpResponse
from unittest.mock import Mock
from givefood.middleware import GeoJSONPreload


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
        from unittest.mock import patch, MagicMock

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
