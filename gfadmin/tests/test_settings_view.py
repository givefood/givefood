"""Tests for the admin settings view template."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestSettingsView:
    """Test the settings view template rendering."""

    def test_settings_page_date_inputs_have_bulma_classes(self, admin_client):
        """Test that date inputs have the Bulma 'input' class."""
        # Access the settings page
        url = reverse('admin:settings')
        response = admin_client.get(url)
        
        # Check response is successful
        assert response.status_code == 200
        
        # Check that date inputs have the Bulma 'input' class
        content = response.content.decode('utf-8')
        assert 'type="date" name="start" value="2024-01-01" class="input"' in content
        assert 'type="date" name="end" value="2024-03-31" class="input"' in content

    def test_settings_page_submit_button_has_bulma_classes(self, admin_client):
        """Test that the submit button has Bulma button classes."""
        # Access the settings page
        url = reverse('admin:settings')
        response = admin_client.get(url)
        
        # Check response is successful
        assert response.status_code == 200
        
        # Check that submit button has the Bulma button classes
        content = response.content.decode('utf-8')
        assert 'type="submit" value="Go" class="button is-link is-light"' in content
