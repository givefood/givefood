"""Tests for article featured toggle functionality."""
import pytest
from unittest.mock import patch
from django.urls import reverse
from django.utils import timezone

from givefood.models import Foodbank, FoodbankArticle


@pytest.mark.django_db
class TestArticleFeaturedToggle:
    """Test the article featured toggle functionality."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    @pytest.fixture
    def foodbank(self):
        """Create a test foodbank."""
        foodbank = Foodbank(
            name='Test Food Bank',
            slug='test-food-bank',
            address='123 Test St',
            postcode='TE1 1ST',
            lat_lng='51.5074,-0.1278',
            country='England',
            url='https://example.com',
            shopping_list_url='https://example.com/needs',
            contact_email='test@example.com',
            edited=timezone.now(),
            is_closed=False
        )
        foodbank.latitude = 51.5074
        foodbank.longitude = -0.1278
        foodbank.save(do_geoupdate=False)
        return foodbank

    @pytest.fixture
    def article(self, foodbank):
        """Create a test article."""
        return FoodbankArticle.objects.create(
            foodbank=foodbank,
            title='Test Article',
            url='https://example.com/article1',
            published_date=timezone.now(),
            featured=False
        )

    def test_article_has_featured_field_default_false(self, article):
        """Test that articles have featured field defaulting to False."""
        assert hasattr(article, 'featured')
        assert article.featured is False

    def test_toggle_featured_from_false_to_true(self, client, article):
        """Test toggling featured status from False to True."""
        self._setup_authenticated_session(client)
        assert article.featured is False
        
        url = reverse('gfadmin:article_toggle_featured', args=[article.id])
        response = client.post(url, HTTP_HX_REQUEST='true')
        
        assert response.status_code == 200
        article.refresh_from_db()
        assert article.featured is True
        assert '★' in response.content.decode()
        assert 'is-warning' in response.content.decode()
        assert 'is-light' in response.content.decode()

    def test_toggle_featured_from_true_to_false(self, client, article):
        """Test toggling featured status from True to False."""
        self._setup_authenticated_session(client)
        article.featured = True
        article.save()
        
        url = reverse('gfadmin:article_toggle_featured', args=[article.id])
        response = client.post(url, HTTP_HX_REQUEST='true')
        
        assert response.status_code == 200
        article.refresh_from_db()
        assert article.featured is False
        assert '☆' in response.content.decode()
        assert 'is-light' in response.content.decode()

    def test_toggle_featured_multiple_times(self, client, article):
        """Test toggling featured status multiple times."""
        self._setup_authenticated_session(client)
        url = reverse('gfadmin:article_toggle_featured', args=[article.id])
        
        # Toggle 1: False -> True
        client.post(url, HTTP_HX_REQUEST='true')
        article.refresh_from_db()
        assert article.featured is True
        
        # Toggle 2: True -> False
        client.post(url, HTTP_HX_REQUEST='true')
        article.refresh_from_db()
        assert article.featured is False
        
        # Toggle 3: False -> True
        client.post(url, HTTP_HX_REQUEST='true')
        article.refresh_from_db()
        assert article.featured is True

    def test_toggle_featured_nonexistent_article(self, client):
        """Test toggling featured status for non-existent article returns 404."""
        self._setup_authenticated_session(client)
        url = reverse('gfadmin:article_toggle_featured', args=[99999])
        response = client.post(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 404

    def test_admin_index_shows_featured_button(self, client, article):
        """Test that admin index page shows the featured toggle button."""
        self._setup_authenticated_session(client)
        url = reverse('gfadmin:index')
        response = client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check that the article appears
        assert article.title in content
        
        # Check that the toggle button exists
        assert f'/admin/article/{article.id}/toggle-featured/' in content
        assert 'hx-post' in content

    def test_featured_button_appearance_when_not_featured(self, client, article):
        """Test button appearance when article is not featured."""
        self._setup_authenticated_session(client)
        article.featured = False
        article.save()
        
        url = reverse('gfadmin:index')
        response = client.get(url)
        content = response.content.decode()
        
        # Should show empty star
        assert '☆' in content

    def test_featured_button_appearance_when_featured(self, client, article):
        """Test button appearance when article is featured."""
        self._setup_authenticated_session(client)
        article.featured = True
        article.save()
        
        url = reverse('gfadmin:index')
        response = client.get(url)
        content = response.content.decode()
        
        # Should show filled star
        assert '★' in content

    def test_toggling_featured_clears_homepage_cache(self, article):
        """Test that toggling featured status triggers cache clearing for homepage."""
        with patch('givefood.models.decache_async') as mock_decache:
            # Toggle featured from False to True
            article.featured = True
            article.save()
            
            # Verify decache_async.enqueue was called
            assert mock_decache.enqueue.called
            call_args = mock_decache.enqueue.call_args[0][0]
            
            # Check that homepage URLs are included
            assert any('/' in url or url == '/' for url in call_args)
            
            # Reset mock
            mock_decache.enqueue.reset_mock()
            
            # Toggle featured from True to False
            article.featured = False
            article.save()
            
            # Verify decache_async.enqueue was called again
            assert mock_decache.enqueue.called
            call_args = mock_decache.enqueue.call_args[0][0]
            
            # Check that homepage URLs are included
            assert any('/' in url or url == '/' for url in call_args)

    def test_saving_without_changing_featured_does_not_clear_cache(self, article):
        """Test that saving an article without changing featured status doesn't clear cache."""
        with patch('givefood.models.decache_async') as mock_decache:
            # Save without changing featured status
            article.title = "Updated Title"
            article.save()
            
            # Verify decache_async.enqueue was NOT called
            assert not mock_decache.enqueue.called
