"""Test that excess comparison is displayed correctly on the admin need page."""
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from givefood.models import Foodbank, FoodbankChange


def _setup_authenticated_session(client):
    """Helper to setup an authenticated session for testing admin views."""
    session = client.session
    session['user_data'] = {
        'email': 'test@givefood.org.uk',
        'email_verified': True,
        'hd': 'givefood.org.uk',
    }
    session.save()


@pytest.fixture
def foodbank():
    """Create a test foodbank."""
    fb = Foodbank(
        name='Test Food Bank',
        slug='test-food-bank',
        address='123 Test St',
        postcode='TE1 1ST',
        lat_lng='51.5074,-0.1278',
        country='England',
        contact_email='test@example.com',
        url='https://example.com',
        shopping_list_url='https://example.com/shopping',
        edited=timezone.now(),
        is_closed=False
    )
    fb.latitude = 51.5074
    fb.longitude = -0.1278
    fb.parliamentary_constituency_slug = 'test-constituency'
    fb.save(do_geoupdate=False, do_decache=False)
    return fb


@pytest.fixture
def current_need(foodbank):
    """Create a current need with excess items."""
    need = FoodbankChange(
        foodbank=foodbank,
        change_text='Pasta\nRice\nBeans',
        excess_change_text='Bottles Of Water\nVery Large Bags Or Boxes Of Food e.g. 3kg Bags Of Pasta / Rice',
        published=False,
        input_method='typed'
    )
    need.save(do_translate=False, do_foodbank_save=False)
    return need


@pytest.fixture
def prev_published_need(foodbank, current_need):
    """Create a previous published need with different excess items."""
    prev_need = FoodbankChange(
        foodbank=foodbank,
        change_text='Old Pasta\nOld Rice',
        excess_change_text='Old Bread\nOld Water',
        published=True,
        input_method='typed'
    )
    prev_need.save(do_translate=False, do_foodbank_save=False)
    # Update created timestamp to be before current need using Django ORM
    # The created field is auto-populated by Django's auto_now_add
    prev_need.refresh_from_db()
    FoodbankChange.objects.filter(pk=prev_need.pk).update(
        created=prev_need.created - timezone.timedelta(days=1)
    )
    prev_need.refresh_from_db()
    return prev_need


@pytest.mark.django_db
class TestExcessComparison:
    """Test that excess comparison is properly displayed."""
    
    def test_excess_comparison_visible_for_published_tab(self, current_need, prev_published_need):
        """Test that the excess comparison section is visible by default (published tab)."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[current_need.need_id])
        response = client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Check that the published tab's excess comparison div exists and is NOT hidden initially
        # It should have class="published" but NOT class="is-hidden"
        assert 'class="published column is-half tabcontent"' in content
        assert 'id="published-excess-panel"' in content
        
        # Check that it has correct aria attributes for published tab
        assert 'aria-labelledby="published-tab"' in content
        
        # Check that the inner content uses published tab
        assert 'data-tab="published"' in content
        
    def test_excess_content_displayed(self, current_need, prev_published_need):
        """Test that actual excess comparison content is present."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[current_need.need_id])
        response = client.get(url)
        
        assert response.status_code == 200
        
        # Check that diff_from_pub_excess is in the context
        assert 'diff_from_pub_excess' in response.context
        
    def test_template_structure_two_columns_per_tab(self, current_need, prev_published_need):
        """Test that each tab (published/nonpert) should show 2 columns side by side."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[current_need.need_id])
        response = client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Count the published tab content divs - should be 2 (one for Need, one for Excess)
        published_divs = content.count('class="published column is-half tabcontent"')
        
        # There should be at least 2 published divs (Need and Excess columns)
        assert published_divs >= 2, f"Expected at least 2 published column divs, found {published_divs}"
        
    def test_no_conflicting_panel_ids(self, current_need, prev_published_need):
        """Test that panel IDs don't conflict (published-excess should not use nonpert-panel id)."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[current_need.need_id])
        response = client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Check that published excess panel has its own unique ID
        assert 'id="published-excess-panel"' in content
        
        # Count occurrences of nonpert-panel - should only appear in the actual nonpert section
        # and not in any published section
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # If we find a line with published class and nonpert-panel id, that's the bug
            if 'class="published' in line and 'is-half' in line:
                # Check the surrounding lines for nonpert-panel
                context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                assert 'id="nonpert-panel"' not in context, \
                    "Published column incorrectly uses nonpert-panel ID"
