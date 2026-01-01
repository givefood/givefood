"""Test that excess comparison is displayed correctly on the admin need page."""
import pytest
from bs4 import BeautifulSoup
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
        
        # Parse HTML with BeautifulSoup for robust testing
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the published excess panel
        excess_panel = soup.find('div', id='published-excess-panel')
        assert excess_panel is not None, "published-excess-panel not found"
        
        # Check that it has the published class
        assert 'published' in excess_panel.get('class', [])
        
        # Check that it does NOT have is-hidden class
        assert 'is-hidden' not in excess_panel.get('class', []), \
            "published-excess-panel should not be hidden by default"
        
        # Check aria attributes
        assert excess_panel.get('aria-labelledby') == 'published-tab'
        
        # Check inner data-tab attribute
        inner_div = excess_panel.find('div', attrs={'data-tab': 'published'})
        assert inner_div is not None, "Inner div with data-tab='published' not found"
        
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
        
        # Parse HTML with BeautifulSoup for robust testing
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all published column divs
        published_divs = soup.find_all('div', class_='published')
        published_columns = [d for d in published_divs if 'column' in d.get('class', [])]
        
        # There should be at least 2 published column divs (Need and Excess columns)
        assert len(published_columns) >= 2, \
            f"Expected at least 2 published column divs, found {len(published_columns)}"
        
    def test_no_conflicting_panel_ids(self, current_need, prev_published_need):
        """Test that panel IDs don't conflict (published-excess should not use nonpert-panel id)."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need', args=[current_need.need_id])
        response = client.get(url)
        
        assert response.status_code == 200
        
        # Parse HTML with BeautifulSoup for robust testing
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all published columns
        published_divs = soup.find_all('div', class_='published')
        
        # Check that no published div has the nonpert-panel id
        for div in published_divs:
            assert div.get('id') != 'nonpert-panel', \
                "Published column incorrectly uses nonpert-panel ID"
        
        # Verify published-excess-panel exists
        excess_panel = soup.find('div', id='published-excess-panel')
        assert excess_panel is not None, "published-excess-panel not found"
        assert 'published' in excess_panel.get('class', []), \
            "published-excess-panel should have published class"
