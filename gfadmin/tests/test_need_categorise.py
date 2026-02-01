"""Tests for the admin need categorisation view optimizations."""
import pytest
from unittest.mock import patch
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from givefood.models import Foodbank, FoodbankChange, FoodbankChangeLine


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
def need(foodbank):
    """Create a test need with multiple items."""
    need = FoodbankChange(
        foodbank=foodbank,
        change_text='Pasta\nRice\nBeans\nTinned Tomatoes\nCoffee',
        excess_change_text='Bread\nMilk',
        published=False,
        input_method='typed'
    )
    need.save(do_translate=False, do_foodbank_save=False)
    return need


@pytest.fixture
def need_with_existing_lines(need):
    """Create a need with some existing FoodbankChangeLine entries."""
    # Create existing lines for some items (without specifying group, it's auto-set)
    FoodbankChangeLine.objects.create(
        need=need,
        foodbank=need.foodbank,
        item='Pasta',
        type='need',
        category='Pasta',
        created=need.created
    )
    FoodbankChangeLine.objects.create(
        need=need,
        foodbank=need.foodbank,
        item='Rice',
        type='need',
        category='Rice',
        created=need.created
    )
    return need


@pytest.fixture
def previous_need_lines(foodbank):
    """Create previous need lines for historical reference."""
    # Create a previous need
    prev_need = FoodbankChange(
        foodbank=foodbank,
        change_text='Old items',
        published=True,
        input_method='typed'
    )
    prev_need.save(do_translate=False, do_foodbank_save=False)
    
    # Create historical lines for items (without specifying group, it's auto-set)
    FoodbankChangeLine.objects.create(
        need=prev_need,
        foodbank=foodbank,
        item='Beans',
        type='need',
        category='Baked Beans',
        created=prev_need.created
    )
    FoodbankChangeLine.objects.create(
        need=prev_need,
        foodbank=foodbank,
        item='Coffee',
        type='need',
        category='Coffee',
        created=prev_need.created
    )
    return prev_need


@pytest.fixture
def mock_ai_category():
    """Mock the AI categorisation function to avoid API calls during tests."""
    with patch('gfadmin.views.get_ai_category', return_value='Other'):
        yield


@pytest.mark.django_db
@pytest.mark.usefixtures('mock_ai_category')
class TestNeedCategoriseView:
    """Test the admin need categorise view."""

    def test_need_categorise_view_returns_200(self, need):
        """Test that the need categorise view returns a 200 status code."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need_categorise', args=[need.need_id])
        response = client.get(url)
        assert response.status_code == 200

    def test_need_categorise_view_includes_need_in_context(self, need):
        """Test that the need object is in the context."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need_categorise', args=[need.need_id])
        response = client.get(url)
        assert 'need' in response.context
        assert response.context['need'].need_id == need.need_id

    def test_need_categorise_view_creates_forms_for_all_items(self, need):
        """Test that forms are created for all items in the need."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need_categorise', args=[need.need_id])
        response = client.get(url)
        
        assert 'forms' in response.context
        # Should have 5 need items + 2 excess items = 7 forms
        assert len(response.context['forms']) == 7

    def test_need_categorise_view_with_existing_lines(self, need_with_existing_lines):
        """Test that existing lines are properly loaded into forms."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need_categorise', args=[need_with_existing_lines.need_id])
        response = client.get(url)
        
        assert 'forms' in response.context
        forms = response.context['forms']
        
        # Check that forms for existing lines have instance data
        pasta_form = None
        rice_form = None
        for form in forms:
            if form.prefix == 'Pasta':
                pasta_form = form
            elif form.prefix == 'Rice':
                rice_form = form
        
        assert pasta_form is not None
        assert rice_form is not None
        assert pasta_form.instance.pk is not None  # Has existing instance
        assert rice_form.instance.pk is not None   # Has existing instance

    def test_need_categorise_view_with_previous_lines(self, need, previous_need_lines):
        """Test that previous line categories are used for initial values."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need_categorise', args=[need.need_id])
        response = client.get(url)
        
        assert 'forms' in response.context
        forms = response.context['forms']
        
        # Check that forms for items with previous history have initial category
        beans_form = None
        coffee_form = None
        for form in forms:
            if form.prefix == 'Beans':
                beans_form = form
            elif form.prefix == 'Coffee':
                coffee_form = form
        
        assert beans_form is not None
        assert coffee_form is not None
        # These should have initial values from previous lines
        assert beans_form.initial.get('category') == 'Baked Beans'
        assert coffee_form.initial.get('category') == 'Coffee'

    def test_need_categorise_view_query_count(self, need_with_existing_lines, previous_need_lines, django_assert_num_queries):
        """Test that the view doesn't have N+1 queries."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need_categorise', args=[need_with_existing_lines.need_id])
        
        # The view should execute a bounded number of queries regardless of item count:
        # 1. Session load
        # 2. Get the need
        # 3. Prefetch existing need lines
        # 4. Get latest lines for all items (aggregation + fetch)
        # 5-9. Context processor queries for credentials (5 queries)
        # Should be around 9 queries total, not N queries where N = number of items
        with django_assert_num_queries(9):
            response = client.get(url)
        
        assert response.status_code == 200

    def test_need_categorise_post_saves_correctly(self, need):
        """Test that POST request saves categorisations correctly."""
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need_categorise', args=[need.need_id])
        
        # Submit form data for categorisation - need, foodbank fields are required
        post_data = {
            'Pasta-item': 'Pasta',
            'Pasta-type': 'need',
            'Pasta-category': 'Pasta',
            'Pasta-need': str(need.pk),
            'Pasta-foodbank': str(need.foodbank.pk),
            'Rice-item': 'Rice',
            'Rice-type': 'need',
            'Rice-category': 'Rice',
            'Rice-need': str(need.pk),
            'Rice-foodbank': str(need.foodbank.pk),
            'Beans-item': 'Beans',
            'Beans-type': 'need',
            'Beans-category': 'Baked Beans',
            'Beans-need': str(need.pk),
            'Beans-foodbank': str(need.foodbank.pk),
            'Tinned Tomatoes-item': 'Tinned Tomatoes',
            'Tinned Tomatoes-type': 'need',
            'Tinned Tomatoes-category': 'Tinned Tomatoes',
            'Tinned Tomatoes-need': str(need.pk),
            'Tinned Tomatoes-foodbank': str(need.foodbank.pk),
            'Coffee-item': 'Coffee',
            'Coffee-type': 'need',
            'Coffee-category': 'Coffee',
            'Coffee-need': str(need.pk),
            'Coffee-foodbank': str(need.foodbank.pk),
            'Bread-item': 'Bread',
            'Bread-type': 'excess',
            'Bread-category': 'Cereal',
            'Bread-need': str(need.pk),
            'Bread-foodbank': str(need.foodbank.pk),
            'Milk-item': 'Milk',
            'Milk-type': 'excess',
            'Milk-category': 'Milk',
            'Milk-need': str(need.pk),
            'Milk-foodbank': str(need.foodbank.pk),
        }
        
        response = client.post(url, post_data, follow=False)
        
        # Should redirect to the need view
        assert response.status_code == 302
        assert f'/admin/need/{need.need_id}/' in response.url
        
        # Check that need is marked as categorised
        need.refresh_from_db()
        assert need.is_categorised is True
        
        # Check that all lines were saved
        lines = FoodbankChangeLine.objects.filter(need=need)
        assert lines.count() == 7

    def test_need_categorise_without_excess_items(self, foodbank):
        """Test that the view handles needs without excess items."""
        need = FoodbankChange(
            foodbank=foodbank,
            change_text='Pasta\nRice',
            excess_change_text=None,
            published=False,
            input_method='typed'
        )
        need.save(do_translate=False, do_foodbank_save=False)
        
        client = Client()
        _setup_authenticated_session(client)
        url = reverse('admin:need_categorise', args=[need.need_id])
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'forms' in response.context
        # Should have only 2 forms for need items
        assert len(response.context['forms']) == 2

    def test_need_categorise_ai_category_called_for_new_items(self, foodbank):
        """Test that AI categorisation is called for items without previous categories."""
        need = FoodbankChange(
            foodbank=foodbank,
            change_text='Pasta',
            excess_change_text=None,
            published=False,
            input_method='typed'
        )
        need.save(do_translate=False, do_foodbank_save=False)
        
        client = Client()
        _setup_authenticated_session(client)
        
        # Use a specific mock value so we can verify it was used
        with patch('gfadmin.views.get_ai_category', return_value='Pasta') as mock_ai:
            url = reverse('admin:need_categorise', args=[need.need_id])
            response = client.get(url)
            
            # The AI function should have been called for 'Pasta' item
            mock_ai.assert_called_once_with('Pasta')
            
            # Verify the form has the AI-generated category as initial value
            forms = response.context['forms']
            assert len(forms) == 1
            assert forms[0].initial.get('category') == 'Pasta'

    def test_need_categorise_ai_category_not_called_for_existing_items(self, foodbank):
        """Test that AI categorisation is not called for items with previous categories."""
        # Create a previous need line
        prev_need = FoodbankChange(
            foodbank=foodbank,
            change_text='Pasta',
            published=True,
            input_method='typed'
        )
        prev_need.save(do_translate=False, do_foodbank_save=False)
        FoodbankChangeLine.objects.create(
            need=prev_need,
            foodbank=foodbank,
            item='Pasta',
            type='need',
            category='Pasta',
            created=prev_need.created
        )
        
        # Create a new need with the same item
        need = FoodbankChange(
            foodbank=foodbank,
            change_text='Pasta',
            excess_change_text=None,
            published=False,
            input_method='typed'
        )
        need.save(do_translate=False, do_foodbank_save=False)
        
        client = Client()
        _setup_authenticated_session(client)
        
        with patch('gfadmin.views.get_ai_category') as mock_ai:
            url = reverse('admin:need_categorise', args=[need.need_id])
            response = client.get(url)
            
            # The AI function should NOT have been called since we have a previous category
            mock_ai.assert_not_called()
            
            # Verify the form has the previous category as initial value
            forms = response.context['forms']
            assert len(forms) == 1
            assert forms[0].initial.get('category') == 'Pasta'


@pytest.mark.django_db
class TestGetAiCategory:
    """Tests for the get_ai_category helper function."""

    def test_get_ai_category_returns_valid_category(self):
        """Test that valid AI responses are returned as-is."""
        from gfadmin.views import get_ai_category
        with patch('gfadmin.views.gemini', return_value='Pasta'):
            result = get_ai_category('Spaghetti')
            assert result == 'Pasta'

    def test_get_ai_category_returns_other_for_invalid_response(self):
        """Test that invalid AI responses fall back to 'Other'."""
        from gfadmin.views import get_ai_category
        with patch('gfadmin.views.gemini', return_value='InvalidCategory'):
            result = get_ai_category('SomeItem')
            assert result == 'Other'

    def test_get_ai_category_returns_other_for_none_response(self):
        """Test that None AI responses fall back to 'Other'."""
        from gfadmin.views import get_ai_category
        with patch('gfadmin.views.gemini', return_value=None):
            result = get_ai_category('SomeItem')
            assert result == 'Other'

    def test_get_ai_category_uses_correct_prompt_template(self):
        """Test that the function uses the categorisation_prompt.txt template."""
        from gfadmin.views import get_ai_category
        with patch('gfadmin.views.gemini', return_value='Other') as mock_gemini:
            with patch('gfadmin.views.render_to_string') as mock_render:
                mock_render.return_value = 'test prompt'
                get_ai_category('TestItem')
                
                # Verify render_to_string was called with correct template
                mock_render.assert_called_once()
                args, kwargs = mock_render.call_args
                assert args[0] == 'categorisation_prompt.txt'
                assert 'item' in args[1]
                assert args[1]['item'] == 'TestItem'
                assert 'item_categories' in args[1]

    def test_get_ai_category_uses_low_temperature(self):
        """Test that the AI is called with low temperature for deterministic results."""
        from gfadmin.views import get_ai_category
        with patch('gfadmin.views.gemini', return_value='Pasta') as mock_gemini:
            get_ai_category('Spaghetti')
            mock_gemini.assert_called_once()
            _, kwargs = mock_gemini.call_args
            assert kwargs['temperature'] == 0.1
