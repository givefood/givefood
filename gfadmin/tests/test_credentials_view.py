"""Tests for the admin credentials views."""
import pytest
from django.test import Client
from django.urls import reverse

from givefood.models import GfCredential


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
def credential():
    """Create a test credential."""
    return GfCredential.objects.create(
        cred_name="test_key",
        cred_value="test_value",
    )


@pytest.mark.django_db
class TestCredentialDetail:
    """Test the credential_detail view."""

    def test_credential_detail_returns_plain_text(self, credential):
        """Test that credential detail returns the value as plain text."""
        client = Client()
        _setup_authenticated_session(client)

        response = client.get(
            reverse("admin:credential_detail", args=["test_key"]),
        )

        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain"
        assert response.content.decode() == "test_value"

    def test_credential_detail_returns_404_for_missing(self):
        """Test that a non-existent credential returns 404."""
        client = Client()
        _setup_authenticated_session(client)

        response = client.get(
            reverse("admin:credential_detail", args=["nonexistent"]),
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestDeleteCredential:
    """Test the delete_credential view."""

    def test_delete_credential_removes_record(self, credential):
        """Test that POSTing to delete_credential removes the credential."""
        client = Client()
        _setup_authenticated_session(client)

        assert GfCredential.objects.filter(id=credential.id).exists()

        response = client.post(
            reverse("admin:credential_delete"),
            {"id": credential.id},
        )

        assert response.status_code == 302
        assert response.url == reverse("admin:credentials")
        assert not GfCredential.objects.filter(id=credential.id).exists()

    def test_delete_credential_returns_404_for_missing(self):
        """Test that deleting a non-existent credential returns 404."""
        client = Client()
        _setup_authenticated_session(client)

        response = client.post(
            reverse("admin:credential_delete"),
            {"id": 99999},
        )

        assert response.status_code == 404

    def test_delete_credential_rejects_get(self):
        """Test that GET requests are rejected."""
        client = Client()
        _setup_authenticated_session(client)

        response = client.get(reverse("admin:credential_delete"))

        assert response.status_code == 405
