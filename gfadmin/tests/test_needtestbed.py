"""Tests for the admin needtestbed view."""
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse


class TestNeedtestbedURL:
    """Test the needtestbed URL resolves correctly."""

    def test_needtestbed_url_resolves(self):
        url = reverse('admin:needtestbed')
        assert url == '/admin/needtestbed/'


class TestNeedtestbedViewConstants:
    """Test the needtestbed view has the expected models configured."""

    def test_openrouter_models_list(self):
        """Verify the expected OpenRouter models are configured."""
        expected_models = [
            "google/gemini-2.5-flash",
            "amazon/nova-micro-v1",
            "google/gemini-3-flash-preview",
            "openai/gpt-5-nano",
            "mistralai/mistral-nemo",
            "mistralai/devstral-small",
            "anthropic/claude-3-haiku",
        ]
        # Import the view and check the models list is defined
        from gfadmin.views import needtestbed
        import inspect
        source = inspect.getsource(needtestbed)
        for model in expected_models:
            assert model in source, f"Model {model} not found in needtestbed view"
