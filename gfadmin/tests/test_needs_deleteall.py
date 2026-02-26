"""Tests for the admin needs_deleteall view."""
import uuid
import pytest
from django.urls import reverse
from django.utils import timezone

from givefood.models import Foodbank, FoodbankChange


@pytest.fixture
def foodbank():
    """Create a test foodbank."""
    fb = Foodbank(
        name='Test Food Bank Deleteall',
        slug='test-food-bank-deleteall',
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
    fb.save(do_geoupdate=False, do_decache=False)
    return fb


@pytest.mark.django_db
class TestNeedsDeleteAll:
    """Tests for the needs_deleteall view."""

    def test_deleteall_with_already_deleted_id_does_not_500(self, admin_client, foodbank):
        """Test that passing an already-deleted need_id does not cause a 500 error."""
        # Create a need and capture its UUID
        need = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Tinned Tomatoes",
            published=False,
        )
        deleted_uuid = str(need.need_id)

        # Delete the need before calling deleteall
        need.delete()

        # POST to needs_deleteall with the already-deleted UUID
        url = reverse('admin:needs_deleteall')
        response = admin_client.post(url, {'need': deleted_uuid})

        # Should redirect (302), not raise a 500 error
        assert response.status_code == 302

    def test_deleteall_deletes_existing_needs(self, admin_client, foodbank):
        """Test that needs_deleteall successfully deletes existing unpublished needs."""
        need = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Tinned Tomatoes",
            published=False,
        )
        need_uuid = str(need.need_id)

        url = reverse('admin:needs_deleteall')
        response = admin_client.post(url, {'need': need_uuid})

        assert response.status_code == 302
        assert not FoodbankChange.objects.filter(need_id=need_uuid).exists()

    def test_deleteall_with_mixed_existing_and_deleted_ids(self, admin_client, foodbank):
        """Test deleteall handles a mix of existing and already-deleted need_ids."""
        # Create two needs
        need1 = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Tinned Tomatoes",
            published=False,
        )
        need2 = FoodbankChange.objects.create(
            foodbank=foodbank,
            change_text="Pasta",
            published=False,
        )
        uuid1 = str(need1.need_id)
        uuid2 = str(need2.need_id)

        # Delete need1 before calling deleteall
        need1.delete()

        url = reverse('admin:needs_deleteall')
        response = admin_client.post(url, {'need': [uuid1, uuid2]})

        # Should redirect successfully
        assert response.status_code == 302
        # need2 should be deleted
        assert not FoodbankChange.objects.filter(need_id=uuid2).exists()
