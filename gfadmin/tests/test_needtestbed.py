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
            "google/gemini-2.5-flash-lite",
            "amazon/nova-micro-v1",
            "google/gemini-3-flash-preview",
            "openai/gpt-5-nano",
            "mistralai/mistral-nemo",
            "anthropic/claude-3-haiku",
            "minimax/minimax-m2.5",
            "deepseek/deepseek-v3.2",
            "meta-llama/llama-3.3-70b-instruct",
            "qwen/qwen-2.5-7b-instruct",
            "openai/gpt-4.1-mini",
            "qwen/qwen3-coder-next",
        ]
        # Import the view and check the models list is defined
        from gfadmin.views import needtestbed
        import inspect
        source = inspect.getsource(needtestbed)
        for model in expected_models:
            assert model in source, f"Model {model} not found in needtestbed view"

    def test_all_models_use_json_schema(self):
        """Verify all models use the standard json_schema path via response_schema."""
        from gfadmin.views import needtestbed
        import inspect
        source = inspect.getsource(needtestbed)
        assert "MODELS_WITHOUT_JSON_SCHEMA" not in source
        assert "amazon/nova-micro-v1" in source
        assert "anthropic/claude-3-haiku" in source
