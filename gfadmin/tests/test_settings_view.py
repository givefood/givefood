"""Tests for the admin settings view template."""
import pytest
from datetime import date, timedelta
from django.urls import reverse


@pytest.mark.django_db
class TestSettingsView:
    """Test the settings view template rendering."""

    def test_settings_page_date_inputs_have_bulma_classes(self, admin_client):
        """Test that date inputs have the Bulma 'input' class and current quarter dates."""
        # Access the settings page
        url = reverse('admin:settings')
        response = admin_client.get(url)
        
        # Check response is successful
        assert response.status_code == 200
        
        # Calculate expected quarter dates (same logic as the view)
        today = date.today()
        current_quarter = (today.month - 1) // 3 + 1
        quarter_start = date(today.year, (current_quarter - 1) * 3 + 1, 1)
        if current_quarter == 4:
            quarter_end = date(today.year, 12, 31)
        else:
            quarter_end = date(today.year, current_quarter * 3 + 1, 1) - timedelta(days=1)
        
        # Check that date inputs have the Bulma 'input' class with current quarter dates
        content = response.content.decode('utf-8')
        assert f'type="date" name="start" value="{quarter_start.isoformat()}" class="input"' in content
        assert f'type="date" name="end" value="{quarter_end.isoformat()}" class="input"' in content

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
