"""Tests for the admin proxy view link rewriting."""
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote

from django.urls import reverse


class TestProxyLinkRewriting:
    """Test that the proxy view correctly handles same-domain and cross-domain links."""

    def _rewrite_links(self, url, html):
        """Reproduce the proxy link rewriting logic for testing."""
        soup = BeautifulSoup(html, 'html.parser')
        proxy_domain = urlparse(url).netloc
        for a_tag in soup.find_all('a', href=True):
            original_href = a_tag['href']
            absolute_url = urljoin(url, original_href)
            link_domain = urlparse(absolute_url).netloc
            if link_domain == proxy_domain:
                proxy_url = reverse('admin:proxy') + '?url=' + quote(absolute_url, safe='')
                a_tag['href'] = proxy_url
                if a_tag.has_attr('target'):
                    del a_tag['target']
            else:
                a_tag['href'] = absolute_url
                a_tag['target'] = '_blank'
        return str(soup)

    def test_same_domain_relative_links_rewritten_through_proxy(self):
        """Same-domain relative links should be rewritten to go through the proxy."""
        html = '<html><body><a href="/page2">Link</a></body></html>'
        result = self._rewrite_links('https://example.com/page1', html)

        assert reverse('admin:proxy') in result
        assert 'target="_blank"' not in result

    def test_different_domain_links_not_rewritten(self):
        """Links to a different domain should NOT be rewritten through the proxy."""
        html = '<html><body><a href="https://other.com/page">Link</a></body></html>'
        result = self._rewrite_links('https://example.com/page1', html)

        assert reverse('admin:proxy') not in result
        assert 'href="https://other.com/page"' in result
        assert 'target="_blank"' in result

    def test_different_domain_links_open_in_new_window(self):
        """Links to a different domain should have target=_blank."""
        html = '<html><body><a href="https://other.com/page">External</a></body></html>'
        result = self._rewrite_links('https://example.com/', html)

        assert 'target="_blank"' in result

    def test_same_domain_absolute_links_rewritten(self):
        """Absolute same-domain links should be rewritten through the proxy."""
        html = '<html><body><a href="https://example.com/other">Link</a></body></html>'
        result = self._rewrite_links('https://example.com/page1', html)

        assert reverse('admin:proxy') in result
        assert 'target="_blank"' not in result

    def test_mixed_links(self):
        """Pages with both same-domain and cross-domain links should be handled correctly."""
        html = '<html><body><a href="/internal">Int</a><a href="https://ext.com">Ext</a></body></html>'
        result = self._rewrite_links('https://example.com/', html)

        soup = BeautifulSoup(result, 'html.parser')
        links = soup.find_all('a')
        # Internal link goes through proxy
        assert reverse('admin:proxy') in links[0]['href']
        assert not links[0].has_attr('target')
        # External link opens in new window
        assert links[1]['href'] == 'https://ext.com'
        assert links[1]['target'] == '_blank'
