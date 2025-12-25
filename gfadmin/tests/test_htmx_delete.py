"""Tests for the HTMX delete functionality on admin check page."""
import pytest
from django.test import RequestFactory

from givefood.models import Foodbank, FoodbankLocation, FoodbankDonationPoint


@pytest.mark.django_db
class TestHTMXDelete:
    """Test the HTMX delete functionality for locations and donation points."""

    def setup_method(self):
        """Create test foodbank with location and donation point."""
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
        )
        self.foodbank.save(do_geoupdate=False, do_decache=False)
        
        self.location = FoodbankLocation(
            foodbank=self.foodbank,
            foodbank_name=self.foodbank.name,
            foodbank_slug=self.foodbank.slug,
            foodbank_network=self.foodbank.network,
            foodbank_email=self.foodbank.contact_email,
            name='Test Location',
            slug='test-location',
            address='456 Location St',
            postcode='CD34 5EF',
            lat_lng='51.5074,-0.1278',
            latitude=51.5074,
            longitude=-0.1278,
            country='England',
        )
        self.location.save(do_geoupdate=False, do_foodbank_resave=False)
        
        self.donation_point = FoodbankDonationPoint(
            foodbank=self.foodbank,
            foodbank_name=self.foodbank.name,
            foodbank_slug=self.foodbank.slug,
            foodbank_network=self.foodbank.network,
            name='Test Donation Point',
            slug='test-donation-point',
            address='789 DP St',
            postcode='EF56 7GH',
            lat_lng='51.5074,-0.1278',
            latitude=51.5074,
            longitude=-0.1278,
            country='England',
        )
        self.donation_point.save(do_geoupdate=False, do_foodbank_resave=False, do_photo_update=False)

    def test_fblocation_delete_htmx_returns_empty_response(self):
        """Test that fblocation_delete returns empty response for HTMX requests."""
        from gfadmin.views import fblocation_delete
        factory = RequestFactory()
        request = factory.post(f'/admin/foodbank/{self.foodbank.slug}/location/{self.location.slug}/delete/')
        request.META['HTTP_HX_REQUEST'] = 'true'
        
        response = fblocation_delete(request, slug=self.foodbank.slug, loc_slug=self.location.slug)
        
        assert response.status_code == 200
        assert response.content == b''
        assert not FoodbankLocation.objects.filter(pk=self.location.pk).exists()

    def test_fblocation_delete_non_htmx_returns_redirect(self):
        """Test that fblocation_delete returns redirect for non-HTMX requests."""
        from gfadmin.views import fblocation_delete
        factory = RequestFactory()
        request = factory.post(f'/admin/foodbank/{self.foodbank.slug}/location/{self.location.slug}/delete/')
        
        response = fblocation_delete(request, slug=self.foodbank.slug, loc_slug=self.location.slug)
        
        assert response.status_code == 302
        assert not FoodbankLocation.objects.filter(pk=self.location.pk).exists()

    def test_donationpoint_delete_htmx_returns_empty_response(self):
        """Test that donationpoint_delete returns empty response for HTMX requests."""
        from gfadmin.views import donationpoint_delete
        factory = RequestFactory()
        request = factory.post(f'/admin/foodbank/{self.foodbank.slug}/donationpoint/{self.donation_point.slug}/delete/')
        request.META['HTTP_HX_REQUEST'] = 'true'
        
        response = donationpoint_delete(request, slug=self.foodbank.slug, dp_slug=self.donation_point.slug)
        
        assert response.status_code == 200
        assert response.content == b''
        assert not FoodbankDonationPoint.objects.filter(pk=self.donation_point.pk).exists()

    def test_donationpoint_delete_non_htmx_returns_redirect(self):
        """Test that donationpoint_delete returns redirect for non-HTMX requests."""
        from gfadmin.views import donationpoint_delete
        factory = RequestFactory()
        request = factory.post(f'/admin/foodbank/{self.foodbank.slug}/donationpoint/{self.donation_point.slug}/delete/')
        
        response = donationpoint_delete(request, slug=self.foodbank.slug, dp_slug=self.donation_point.slug)
        
        assert response.status_code == 302
        assert not FoodbankDonationPoint.objects.filter(pk=self.donation_point.pk).exists()
