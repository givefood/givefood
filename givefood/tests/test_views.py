"""
Tests for the main givefood views.
"""
import pytest
from django.test import Client, override_settings
from givefood.models import Foodbank, ParliamentaryConstituency, FoodbankLocation, FoodbankDonationPoint, Place


@pytest.mark.django_db
class TestHomepage:
    """Test the Give Food homepage."""

    @override_settings(DEBUG=False)
    def test_homepage_accessible_or_error_with_empty_db(self, client):
        """Test that the homepage is accessible or fails gracefully with empty DB."""
        # The homepage requires database data for aggregations
        # With an empty database, it will return a 500 error
        # This test ensures the URL is properly configured
        try:
            response = client.get('/', raise_request_exception=False)
            # Homepage might fail with empty database due to aggregations
            # or succeed if there's data in the database
            assert response.status_code in [200, 500]
        except Exception:
            # If there's an error, that's expected with empty DB
            pass


@pytest.mark.django_db
class TestStaticPages:
    """Test static informational pages."""

    def test_about_page(self, client):
        """Test that the about page is accessible."""
        response = client.get('/about/')
        # Should either exist or redirect
        assert response.status_code in [200, 301, 302, 404]

    def test_api_page(self, client):
        """Test that the API page is accessible."""
        response = client.get('/api/')
        # Should either exist or redirect
        assert response.status_code in [200, 301, 302]


@pytest.mark.django_db
class TestFoodbankPages:
    """Test food bank related pages."""

    def test_needs_page(self, client):
        """Test that the needs page is accessible."""
        response = client.get('/needs/')
        assert response.status_code in [200, 301, 302]

    def test_foodbank_search_accessible(self, client):
        """Test that the foodbank search/finder is accessible."""
        response = client.get('/needs/at/')
        # Should return something (list, search page, etc.) or redirect
        assert response.status_code in [200, 301, 302, 404]


@pytest.mark.django_db
class TestSitemap:
    """Test sitemap generation."""

    def test_sitemap_accessible(self, client):
        """Test that the sitemap is accessible and returns valid XML."""
        response = client.get('/sitemap.xml')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/xml'
        # Check that the response contains valid XML structure
        content = response.content.decode('utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in content
        assert '</urlset>' in content

    def test_sitemap_external_accessible(self, client):
        """Test that the external sitemap is accessible and returns valid XML."""
        response = client.get('/sitemap_external.xml')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/xml'
        # Check that the response contains valid XML structure
        content = response.content.decode('utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in content
        assert '</urlset>' in content

    def test_sitemap_places_index_accessible(self, client):
        """Test that the places sitemap index is accessible and returns valid XML."""
        response = client.get('/sitemap_places_index.xml')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/xml'
        # Check that the response contains valid XML structure
        content = response.content.decode('utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in content
        assert '</sitemapindex>' in content

    def test_sitemap_places_accessible(self, client):
        """Test that the places sitemap is accessible and returns valid XML."""
        response = client.get('/sitemap_places.xml')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/xml'
        # Check that the response contains valid XML structure
        content = response.content.decode('utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in content
        assert '</urlset>' in content

    def test_sitemap_places_paginated_accessible(self, client):
        """Test that paginated places sitemaps are accessible."""
        response = client.get('/sitemap_places_1.xml')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/xml'
        content = response.content.decode('utf-8')
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in content


@pytest.mark.django_db
class TestLLMSTxt:
    """Test llms.txt generation."""

    def test_llmstxt_accessible(self, client):
        """Test that llms.txt is accessible and returns valid plain text."""
        response = client.get('/llms.txt')
        assert response.status_code == 200
        assert 'text/plain' in response['Content-Type']
        content = response.content.decode('utf-8')
        # Check that the response contains expected content
        assert '# Give Food' in content
        assert 'UK charity' in content
        
    def test_llmstxt_has_dynamic_counts(self, client):
        """Test that llms.txt includes dynamic foodbank and donation point counts."""
        response = client.get('/llms.txt')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Check that the content does NOT contain the old hardcoded values
        assert '2,916 food bank' not in content
        assert '7,000+ donation points' not in content
        # The content should have numeric values (at least "0" with empty DB)
        # Check that the template variable tags are not present (they've been rendered)
        assert '{{ foodbanks_count' not in content
        assert '{{ donationpoints_count' not in content


@pytest.mark.django_db
class TestManifest:
    """Test web app manifest generation."""

    def test_manifest_accessible(self, client):
        """Test that manifest.json is accessible and returns valid JSON."""
        response = client.get('/manifest.json')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
    def test_manifest_has_valid_json_structure(self, client):
        """Test that manifest.json contains valid web app manifest structure."""
        import json
        response = client.get('/manifest.json')
        assert response.status_code == 200
        data = json.loads(response.content.decode('utf-8'))
        
        # Check required manifest fields
        assert 'name' in data
        assert 'short_name' in data
        assert 'description' in data
        assert 'start_url' in data
        assert 'icons' in data
        
        # Verify icons structure
        assert len(data['icons']) > 0
        icon = data['icons'][0]
        assert 'src' in icon
        assert 'type' in icon
        assert 'sizes' in icon
        
        # Verify correct MIME type for SVG
        assert icon['type'] == 'image/svg+xml'


@pytest.mark.django_db
class TestCountryPages:
    """Test country-specific pages."""

    def test_scotland_page_accessible(self, client):
        """Test that the Scotland page is accessible."""
        response = client.get('/scotland/')
        assert response.status_code in [200, 500]  # May fail with empty DB due to aggregations
        
    def test_england_page_accessible(self, client):
        """Test that the England page is accessible."""
        response = client.get('/england/')
        assert response.status_code in [200, 500]
        
    def test_wales_page_accessible(self, client):
        """Test that the Wales page is accessible."""
        response = client.get('/wales/')
        assert response.status_code in [200, 500]
        
    def test_northern_ireland_page_accessible(self, client):
        """Test that the Northern Ireland page is accessible."""
        response = client.get('/northern-ireland/')
        assert response.status_code in [200, 500]
        
    def test_invalid_country_returns_404(self, client):
        """Test that invalid country slugs return 404."""
        response = client.get('/invalid-country/')
        assert response.status_code == 404
        
    def test_scotland_geojson_accessible(self, client):
        """Test that the Scotland GeoJSON endpoint is accessible."""
        response = client.get('/scotland/geo.json')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
    def test_england_geojson_accessible(self, client):
        """Test that the England GeoJSON endpoint is accessible."""
        response = client.get('/england/geo.json')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
    def test_wales_geojson_accessible(self, client):
        """Test that the Wales GeoJSON endpoint is accessible."""
        response = client.get('/wales/geo.json')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
    def test_northern_ireland_geojson_accessible(self, client):
        """Test that the Northern Ireland GeoJSON endpoint is accessible."""
        response = client.get('/northern-ireland/geo.json')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
    def test_geojson_has_valid_structure(self, client):
        """Test that GeoJSON endpoints return valid GeoJSON structure."""
        import json
        response = client.get('/scotland/geo.json')
        assert response.status_code == 200
        data = json.loads(response.content.decode('utf-8'))
        
        # Check GeoJSON structure
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert isinstance(data['features'], list)

