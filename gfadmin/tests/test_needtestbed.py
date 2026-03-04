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
            "openrouter/sherlock-dash-alpha",
            "openai/gpt-4o",
            "qwen/qwen3-coder-next",
            "z-ai/glm-5",
        ]
        # Import the view and check the models list is defined
        from gfadmin.views import needtestbed
        import inspect
        source = inspect.getsource(needtestbed)
        for model in expected_models:
            assert model in source, f"Model {model} not found in needtestbed view"

    def test_models_without_json_schema(self):
        """Verify models without json_schema support are configured and called without response_format."""
        from gfadmin.views import needtestbed
        import inspect
        source = inspect.getsource(needtestbed)
        assert "MODELS_WITHOUT_JSON_SCHEMA" in source
        assert "amazon/nova-micro-v1" in source
        assert "anthropic/claude-3-haiku" in source
        # Ensure the MODELS_WITHOUT_JSON_SCHEMA branch calls openrouter with json_object format
        assert 'openrouter(need_prompt, 0, model, response_format_type="json_object")' in source
