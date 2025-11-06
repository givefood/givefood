#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from django.template import Context, Template


class TestFriendlyUrlTemplateTag:
    """Tests for the friendly_url template tag."""

    def test_friendly_url_removes_https(self):
        """Test that friendly_url removes https:// prefix."""
        template = Template("{% load custom_tags %}{{ url|friendly_url }}")
        context = Context({"url": "https://example.com/page"})
        result = template.render(context)
        assert result == "example.com/page"

    def test_friendly_url_removes_http(self):
        """Test that friendly_url removes http:// prefix."""
        template = Template("{% load custom_tags %}{{ url|friendly_url }}")
        context = Context({"url": "http://example.com/page"})
        result = template.render(context)
        assert result == "example.com/page"

    def test_friendly_url_removes_trailing_slash(self):
        """Test that friendly_url removes trailing slash."""
        template = Template("{% load custom_tags %}{{ url|friendly_url }}")
        context = Context({"url": "https://example.com/"})
        result = template.render(context)
        assert result == "example.com"

    def test_friendly_url_with_path_and_trailing_slash(self):
        """Test that friendly_url removes trailing slash from path."""
        template = Template("{% load custom_tags %}{{ url|friendly_url }}")
        context = Context({"url": "https://example.com/page/"})
        result = template.render(context)
        assert result == "example.com/page"

    def test_friendly_url_with_none(self):
        """Test that friendly_url handles None gracefully."""
        template = Template("{% load custom_tags %}{{ url|friendly_url }}")
        context = Context({"url": None})
        result = template.render(context)
        assert result == "None"

    def test_friendly_url_chain_with_truncatechars(self):
        """Test that friendly_url can be chained with other filters."""
        template = Template("{% load custom_tags %}{{ url|friendly_url|truncatechars:20 }}")
        context = Context({"url": "https://example.com/very/long/path/here"})
        result = template.render(context)
        # truncatechars adds ... if text is longer than specified
        assert "example.com" in result
        assert len(result) <= 20
