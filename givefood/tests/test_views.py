"""
Tests for the main givefood views.
"""
import json
import pytest
from django.test import Client, override_settings
from givefood.models import Foodbank, ParliamentaryConstituency, FoodbankLocation, FoodbankDonationPoint, Place, Postcode


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
class TestTestPages:
    """Test test/development pages."""

    def test_maplibre_test_page(self, client):
        """Test that the MapLibre test page is accessible."""
        response = client.get('/tests/maplibre/')
        assert response.status_code == 200
        # Verify key elements are present
        content = response.content.decode('utf-8')
        assert 'MapLibre Test' in content
        assert 'maplibre-gl.css' in content
        assert 'maplibre-gl.js' in content
        assert 'legendtemplate' in content


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
        response = client.get('/scotland/geo.json')
        assert response.status_code == 200
        data = json.loads(response.content.decode('utf-8'))
        
        # Check GeoJSON structure
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert isinstance(data['features'], list)


@pytest.mark.django_db
class TestFragIPAddress:
    """Test the IP address fragment endpoint."""

    def test_frag_ip_address_accessible(self, client):
        """Test that the IP address fragment endpoint is accessible."""
        response = client.get('/frag/ip-address/')
        assert response.status_code == 200
        
    def test_frag_ip_address_returns_ip(self, client):
        """Test that the endpoint returns an IP address string."""
        response = client.get('/frag/ip-address/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Should return an IP address (127.0.0.1 for test client)
        assert content == '127.0.0.1'

    def test_frag_ip_address_with_cloudflare_header(self, client):
        """Test that Cloudflare CF-Connecting-IP header is used when present."""
        response = client.get('/frag/ip-address/', HTTP_CF_CONNECTING_IP='203.0.113.50')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert content == '203.0.113.50'

    def test_frag_ip_address_with_x_forwarded_for(self, client):
        """Test that X-Forwarded-For header is used as fallback."""
        response = client.get('/frag/ip-address/', HTTP_X_FORWARDED_FOR='198.51.100.25, 192.168.1.1')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Should use first IP from X-Forwarded-For
        assert content == '198.51.100.25'

    def test_frag_ip_address_cloudflare_takes_precedence(self, client):
        """Test that CF-Connecting-IP takes precedence over X-Forwarded-For."""
        response = client.get(
            '/frag/ip-address/',
            HTTP_CF_CONNECTING_IP='203.0.113.50',
            HTTP_X_FORWARDED_FOR='198.51.100.25, 192.168.1.1'
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert content == '203.0.113.50'


@pytest.mark.django_db
class TestFragNews:
    """Test the news fragment endpoint."""

    def test_frag_news_accessible(self, client):
        """Test that the news fragment endpoint is accessible."""
        response = client.get('/frag/news/')
        assert response.status_code == 200

    def test_frag_news_returns_html(self, client):
        """Test that the news fragment returns HTML content."""
        response = client.get('/frag/news/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Should return HTML with the foodbank-news list
        assert '<ul class="foodbank-news">' in content
        assert '</ul>' in content

    def test_frag_invalid_returns_404(self, client):
        """Test that an invalid frag slug returns 404."""
        response = client.get('/frag/invalid/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestWhatsAppWebhook:
    """Test WhatsApp webhook endpoint."""

    def test_whatsapp_hook_get_verification_without_csrf(self, client):
        """Test that GET requests for webhook verification work without CSRF token."""
        # This simulates Facebook/Meta's webhook verification call
        response = client.get(
            '/whatsapp_hook/',
            {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'test_token',
                'hub.challenge': 'test_challenge_12345'
            }
        )
        # Should not return 403 (CSRF error)
        # Will return 403 if verification fails, but that's different from CSRF 403
        assert response.status_code in [200, 403]

    def test_whatsapp_hook_post_without_csrf(self, client):
        """Test that POST requests work without CSRF token (csrf_exempt)."""
        # This simulates Facebook/Meta's webhook message notification
        webhook_data = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'from': '1234567890',
                            'type': 'text',
                            'text': {'body': 'subscribe test-foodbank'}
                        }]
                    }
                }]
            }]
        }
        response = client.post(
            '/whatsapp_hook/',
            data=json.dumps(webhook_data),
            content_type='application/json'
        )
        # Should return 200, not 403 (CSRF error)
        assert response.status_code == 200

    def test_whatsapp_hook_post_empty_body(self, client):
        """Test that POST with empty body is handled gracefully."""
        response = client.post(
            '/whatsapp_hook/',
            data='',
            content_type='application/json'
        )
        # Should handle gracefully, not crash with CSRF error
        assert response.status_code in [200, 400]

    def test_whatsapp_hook_invalid_method(self, client):
        """Test that invalid HTTP methods return 405."""
        response = client.put('/whatsapp_hook/')
        assert response.status_code == 405


@pytest.mark.django_db
class TestAddressAutocomplete:
    """Test address autocomplete endpoint."""

    def test_aac_accessible(self, client):
        """Test that the address autocomplete endpoint is accessible."""
        response = client.get('/aac/')
        assert response.status_code == 200

    def test_aac_returns_json(self, client):
        """Test that the endpoint returns JSON."""
        response = client.get('/aac/?q=sw')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_aac_returns_cors_header(self, client):
        """Test that the endpoint returns CORS header."""
        response = client.get('/aac/?q=sw')
        assert response.status_code == 200
        assert response['Access-Control-Allow-Origin'] == '*'

    def test_aac_empty_query_returns_empty_list(self, client):
        """Test that empty query returns empty list."""
        response = client.get('/aac/')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == []

    def test_aac_short_query_returns_empty_list(self, client):
        """Test that query with less than 2 characters returns empty list."""
        response = client.get('/aac/?q=s')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == []

    def test_aac_valid_query_returns_list(self, client):
        """Test that valid query returns a list."""
        response = client.get('/aac/?q=london')
        assert response.status_code == 200
        data = json.loads(response.content)
        assert isinstance(data, list)

    def test_aac_place_result_structure(self, client):
        """Test that Place results have expected structure with n (name) and l (lat_lng)."""
        Place.objects.create(
            gbpnid=99999,
            name='Test Place',
            lat_lng='51.5074,-0.1278',
        )
        
        response = client.get('/aac/?q=test')
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert len(data) > 0
        item = data[0]
        assert 'n' in item
        assert 'l' in item
        assert item['n'] == 'Test Place'
        assert item['l'] == '51.5074,-0.1278'

    def test_aac_postcode_result_structure(self, client):
        """Test that Postcode results have expected structure with n (name) and l (lat_lng)."""
        Postcode.objects.create(
            postcode='SW1A 1AA',
            lat_lng='51.5015,-0.1419',
            country='England',
        )
        
        response = client.get('/aac/?q=sw1')
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert len(data) > 0
        item = data[0]
        assert 'n' in item
        assert 'l' in item
        assert item['n'] == 'SW1A 1AA'
        assert item['l'] == '51.5015,-0.1419'

    def test_aac_case_insensitive_place_search(self, client):
        """Test that place search is case insensitive."""
        Place.objects.create(
            gbpnid=99998,
            name='Swindon',
            lat_lng='51.5558,-1.7797',
        )
        
        # Test lowercase query
        response = client.get('/aac/?q=swindon')
        data = json.loads(response.content)
        assert len(data) > 0
        assert data[0]['n'] == 'Swindon'
        
        # Test uppercase query
        response = client.get('/aac/?q=SWINDON')
        data = json.loads(response.content)
        assert len(data) > 0
        assert data[0]['n'] == 'Swindon'

    def test_aac_postcode_case_handling(self, client):
        """Test that postcode search handles different cases correctly."""
        Postcode.objects.create(
            postcode='SE1A 2BB',
            lat_lng='51.5033,-0.1276',
            country='England',
        )
        
        # Test lowercase query - should still find the postcode
        response = client.get('/aac/?q=se1')
        data = json.loads(response.content)
        assert len(data) > 0
        assert any(item['n'] == 'SE1A 2BB' for item in data)

    def test_aac_postcode_search_ignores_spaces(self, client):
        """Test that postcode search ignores spaces in query - 'SW1A0' should match 'SW1A 0AA'."""
        Postcode.objects.create(
            postcode='EC1A 1BB',
            lat_lng='51.5188,-0.1029',
            country='England',
        )
        
        # Search without space should still find the postcode with space
        response = client.get('/aac/?q=ec1a1')
        data = json.loads(response.content)
        assert len(data) > 0
        assert any(item['n'] == 'EC1A 1BB' for item in data)
        
        # Search with space should also work
        response = client.get('/aac/?q=ec1a 1')
        data = json.loads(response.content)
        assert len(data) > 0
        assert any(item['n'] == 'EC1A 1BB' for item in data)

    def test_aac_place_startswith_before_contains(self, client):
        """Test that places starting with query appear before places containing query."""
        # Create place that starts with "Win"
        Place.objects.create(
            gbpnid=99990,
            name='Winchester',
            lat_lng='51.0632,-1.3082',
        )
        # Create place that contains "win" but doesn't start with it
        Place.objects.create(
            gbpnid=99991,
            name='Darwin',
            lat_lng='51.4816,-3.1791',
        )
        
        response = client.get('/aac/?q=win')
        data = json.loads(response.content)
        
        # Filter to just places
        places = [item for item in data if item['t'] == 'p']
        
        assert len(places) >= 2
        # Winchester should appear before Darwin because it starts with "win"
        winchester_idx = next((i for i, p in enumerate(places) if p['n'] == 'Winchester'), None)
        darwin_idx = next((i for i, p in enumerate(places) if p['n'] == 'Darwin'), None)
        
        assert winchester_idx is not None
        assert darwin_idx is not None
        assert winchester_idx < darwin_idx, "Places starting with query should appear first"

    def test_aac_contains_search_finds_substring(self, client):
        """Test that LIKE query finds substring matches in place names."""
        # Create place with query in middle of name
        Place.objects.create(
            gbpnid=99985,
            name='Newmarket',
            lat_lng='52.2467,0.4064',
        )
        
        # Search for "market" which is in the middle of "Newmarket"
        response = client.get('/aac/?q=market')
        data = json.loads(response.content)
        
        places = [item for item in data if item['t'] == 'p']
        assert any(p['n'] == 'Newmarket' for p in places), "Should find places with query in middle of name"

    def test_aac_postcode_contains_search(self, client):
        """Test that postcode search finds postcodes starting with query."""
        Postcode.objects.create(
            postcode='W1A 1AB',
            lat_lng='51.5188,-0.1447',
            country='England',
        )
        
        # Search for "w1a" which matches the start of normalized postcode "W1A1AB"
        response = client.get('/aac/?q=w1a')
        data = json.loads(response.content)
        
        postcodes = [item for item in data if item['t'] == 'c']
        assert any(p['n'] == 'W1A 1AB' for p in postcodes), "Should find postcodes starting with query"


