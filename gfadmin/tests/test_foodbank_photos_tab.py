"""Tests for the Photos tab on foodbank admin page."""
import pytest
from django.test import Client, RequestFactory
from django.urls import reverse

from givefood.models import Foodbank, FoodbankLocation, FoodbankDonationPoint, PlacePhoto


@pytest.mark.django_db
class TestFoodbankPhotosTab:
    """Test the Photos tab functionality on foodbank admin page."""

    def _setup_authenticated_session(self, client):
        """Helper to setup an authenticated session for testing admin views."""
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()

    def _create_foodbank(self, **kwargs):
        """Helper to create a foodbank with common defaults."""
        defaults = {
            'name': 'Test Foodbank',
            'url': 'https://example.com',
            'shopping_list_url': 'https://example.com/shopping',
            'address': '123 Test St',
            'postcode': 'AB12 3CD',
            'country': 'England',
            'lat_lng': '51.5074,-0.1278',
            'contact_email': 'test@example.com',
        }
        defaults.update(kwargs)
        foodbank = Foodbank(**defaults)
        foodbank.save(do_geoupdate=False, do_decache=False)
        return foodbank

    def _get_foodbank_page(self, foodbank):
        """Helper to get the foodbank admin page with authentication."""
        client = Client()
        self._setup_authenticated_session(client)
        return client.get(reverse('admin:foodbank', kwargs={'slug': foodbank.slug}))

    def test_photos_tab_not_shown_when_no_photos(self):
        """Test that Photos tab is not displayed when foodbank has no photos."""
        foodbank = self._create_foodbank()
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify photos tab is not present when no photos
        assert 'data-tab="photos"' not in content
        assert 'id="photos-tab"' not in content
        assert 'id="photos-panel"' not in content

    def test_photos_tab_shown_when_foodbank_has_photo(self):
        """Test that Photos tab is displayed when foodbank has a photo."""
        foodbank = self._create_foodbank(
            place_id='test_place_id_123',
            place_has_photo=True,
        )
        
        # Create a PlacePhoto for the foodbank
        photo = PlacePhoto.objects.create(
            place_id='test_place_id_123',
            photo_ref='test_ref_123',
            html_attributions='Test Attribution',
            blob=b'fake_photo_data',
        )
        
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify photos tab is present
        assert 'data-tab="photos"' in content
        assert 'id="photos-tab"' in content
        assert 'mdi-image' in content  # Icon for photos tab
        
    def test_photos_tab_shows_foodbank_photo(self):
        """Test that Photos tab displays foodbank photo correctly."""
        foodbank = self._create_foodbank(
            place_id='test_place_id_456',
            place_has_photo=True,
        )
        
        photo = PlacePhoto.objects.create(
            place_id='test_place_id_456',
            photo_ref='test_ref_456',
            html_attributions='Test Attribution',
            blob=b'fake_photo_data',
        )
        
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify photo table content
        assert 'Place Name &amp; Type' in content
        assert 'Place ID' in content
        assert 'Photo' in content
        assert foodbank.name in content
        assert 'foodbank' in content  # place_type
        
    def test_photos_count_in_tab(self):
        """Test that Photos tab shows correct count."""
        foodbank = self._create_foodbank(
            place_id='test_place_count',
            place_has_photo=True,
        )
        
        photo = PlacePhoto.objects.create(
            place_id='test_place_count',
            photo_ref='test_ref_count',
            html_attributions='Test Attribution',
            blob=b'fake_photo_data',
        )
        
        response = self._get_foodbank_page(foodbank)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify count is shown (should be 1)
        # The count is shown in a tag like: <span class="tag is-info is-normal is-light">1</span>
        assert 'Photos <span class="tag is-info is-normal is-light">1</span>' in content


@pytest.mark.django_db
class TestPhotoDelete:
    """Test the photo delete functionality."""

    def setup_method(self):
        """Create test foodbank with photo."""
        self.foodbank = Foodbank(
            name='Test Foodbank',
            url='https://example.com',
            shopping_list_url='https://example.com/shopping',
            address='123 Test St',
            postcode='AB12 3CD',
            country='England',
            lat_lng='51.5074,-0.1278',
            contact_email='test@example.com',
            network='Independent',
            place_id='test_delete_place_id',
            place_has_photo=True,
        )
        self.foodbank.save(do_geoupdate=False, do_decache=False)
        
        self.photo = PlacePhoto.objects.create(
            place_id='test_delete_place_id',
            photo_ref='test_delete_ref',
            html_attributions='Test Attribution',
            blob=b'fake_photo_data',
        )

    def test_photo_delete_htmx_returns_empty_response(self):
        """Test that photo_delete returns empty response for HTMX requests."""
        from gfadmin.views import photo_delete
        factory = RequestFactory()
        request = factory.post(f'/admin/foodbank/{self.foodbank.slug}/photo/{self.photo.id}/delete/')
        request.META['HTTP_HX_REQUEST'] = 'true'
        
        response = photo_delete(request, slug=self.foodbank.slug, photo_id=self.photo.id)
        
        assert response.status_code == 200
        assert response.content == b''
        assert not PlacePhoto.objects.filter(pk=self.photo.pk).exists()

    def test_photo_delete_non_htmx_returns_redirect(self):
        """Test that photo_delete returns redirect for non-HTMX requests."""
        from gfadmin.views import photo_delete
        factory = RequestFactory()
        request = factory.post(f'/admin/foodbank/{self.foodbank.slug}/photo/{self.photo.id}/delete/')
        
        response = photo_delete(request, slug=self.foodbank.slug, photo_id=self.photo.id)
        
        assert response.status_code == 302
        assert not PlacePhoto.objects.filter(pk=self.photo.pk).exists()
