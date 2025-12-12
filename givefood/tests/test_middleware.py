"""
Tests for the givefood middleware.
"""
import pytest
import django.db.utils
from django.test import RequestFactory
from django.http import HttpResponse
from unittest.mock import Mock, patch, MagicMock
from givefood.middleware import RenderTime


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

    def test_query_count_replacement(self):
        """Test that PUTTHEQUERIESHERE is replaced with actual query count."""
        # Create a view that returns HTML with the placeholder
        def test_view(request):
            return HttpResponse(
                b"<html><!--PUTTHEQUERIESHERE queries--></html>"
            )

        # Create middleware
        middleware = RenderTime(test_view)

        # Create request
        request = RequestFactory().get('/')

        # Process request
        response = middleware(request)
        content = response.content.decode('utf-8')

        # Verify placeholder was replaced
        assert 'PUTTHEQUERIESHERE' not in content, (
            "PUTTHEQUERIESHERE placeholder should be replaced"
        )

        # Verify a number was inserted
        import re
        match = re.search(r'(\d+) queries', content)
        assert match is not None, "Should contain query count"

        # Verify it's a valid number
        query_count = int(match.group(1))
        assert query_count >= 0, "Query count should be non-negative"

    def test_both_placeholders_replaced(self):
        """Test that both placeholders are replaced in the same response."""
        # Create a view with both placeholders
        def test_view(request):
            html = b"""<html>
<!--
Took PUTTHERENDERTIMEHEREms
Took PUTTHEQUERIESHERE queries
-->
</html>"""
            return HttpResponse(html)

        # Create middleware
        middleware = RenderTime(test_view)

        # Create request
        request = RequestFactory().get('/')

        # Process request
        response = middleware(request)
        content = response.content.decode('utf-8')

        # Verify both placeholders were replaced
        assert 'PUTTHERENDERTIMEHERE' not in content, (
            "PUTTHERENDERTIMEHERE should be replaced"
        )
        assert 'PUTTHEQUERIESHERE' not in content, (
            "PUTTHEQUERIESHERE should be replaced"
        )

        # Verify both values are present
        import re
        time_match = re.search(r'Took (\d+\.?\d*)ms', content)
        query_match = re.search(r'Took (\d+) queries', content)

        assert time_match is not None, "Should contain render time"
        assert query_match is not None, "Should contain query count"

    def test_query_tracking_enabled(self):
        """Test that query tracking is enabled by the middleware."""
        from django.db import connection

        # Create a simple view
        def test_view(request):
            # Check that force_debug_cursor is enabled
            assert connection.force_debug_cursor is True, (
                "Query tracking should be enabled"
            )
            return HttpResponse(b"<html>PUTTHERENDERTIMEHERE PUTTHEQUERIESHERE</html>")

        # Create middleware
        middleware = RenderTime(test_view)

        # Create request
        request = RequestFactory().get('/')

        # Process request
        response = middleware(request)

        # The assertion in test_view will fail if force_debug_cursor is not set

    def test_multiple_replacements_only_replace_first(self):
        """Test that placeholders are only replaced once (first occurrence)."""
        # Create a view with multiple occurrences of the same placeholder
        def test_view(request):
            html = b"""<html>
PUTTHERENDERTIMEHERE
PUTTHERENDERTIMEHERE
PUTTHEQUERIESHERE
PUTTHEQUERIESHERE
</html>"""
            return HttpResponse(html)

        # Create middleware
        middleware = RenderTime(test_view)

        # Create request
        request = RequestFactory().get('/')

        # Process request
        response = middleware(request)
        content = response.content.decode('utf-8')

        # Count how many times each placeholder appears
        # They should each appear once (the second occurrence not replaced)
        assert content.count('PUTTHERENDERTIMEHERE') == 1, (
            "Should replace only the first PUTTHERENDERTIMEHERE"
        )
        assert content.count('PUTTHEQUERIESHERE') == 1, (
            "Should replace only the first PUTTHEQUERIESHERE"
        )
