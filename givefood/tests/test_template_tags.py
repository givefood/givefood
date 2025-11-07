#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
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
        assert result == ""

    def test_friendly_url_chain_with_truncatechars(self):
        """Test that friendly_url can be chained with other filters."""
        template = Template("{% load custom_tags %}{{ url|friendly_url|truncatechars:20 }}")
        context = Context({"url": "https://example.com/very/long/path/here"})
        result = template.render(context)
        # truncatechars adds ... if text is longer than specified
        assert "example.com" in result
        assert len(result) <= 20


class TestTruncateNeedIdTemplateTag:
    """Tests for the truncate_need_id template tag."""

    def test_truncate_need_id_full_uuid(self):
        """Test that truncate_need_id returns first 8 characters of a UUID."""
        template = Template("{% load custom_tags %}{{ need_id|truncate_need_id }}")
        context = Context({"need_id": "550e8400-e29b-41d4-a716-446655440000"})
        result = template.render(context)
        assert result == "550e8400"

    def test_truncate_need_id_short_string(self):
        """Test that truncate_need_id handles strings shorter than 8 characters."""
        template = Template("{% load custom_tags %}{{ need_id|truncate_need_id }}")
        context = Context({"need_id": "abc123"})
        result = template.render(context)
        assert result == "abc123"

    def test_truncate_need_id_exactly_8_chars(self):
        """Test that truncate_need_id handles exactly 8 character strings."""
        template = Template("{% load custom_tags %}{{ need_id|truncate_need_id }}")
        context = Context({"need_id": "12345678"})
        result = template.render(context)
        assert result == "12345678"

    def test_truncate_need_id_with_none(self):
        """Test that truncate_need_id handles None gracefully."""
        template = Template("{% load custom_tags %}{{ need_id|truncate_need_id }}")
        context = Context({"need_id": None})
        result = template.render(context)
        assert result == ""

    def test_truncate_need_id_with_uuid_object(self):
        """Test that truncate_need_id works with UUID objects."""
        template = Template("{% load custom_tags %}{{ need_id|truncate_need_id }}")
        test_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        context = Context({"need_id": test_uuid})
        result = template.render(context)
        assert result == "550e8400"
