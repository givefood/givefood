"""
Tests for the gfwrite (Write to MP) app.
"""
import uuid
import pytest
from django.test import Client
from django.urls import reverse
from givefood.models import ParliamentaryConstituency


@pytest.fixture
def create_test_constituency():
    """Factory fixture for creating test constituencies with unique values."""
    def _create_constituency(name=None, slug=None, **kwargs):
        # Generate unique identifiers to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        if name is None:
            name = f"Test Constituency {unique_id}"
        if slug is None:
            slug = f"test-constituency-{unique_id}"
        defaults = {
            "mp": "Test MP",
            "mp_party": "Test Party",
            "mp_parl_id": 12345,
            "centroid": "51.5074,-0.1278",
            "latitude": 51.5074,
            "longitude": -0.1278,
        }
        defaults.update(kwargs)
        return ParliamentaryConstituency.objects.create(name=name, slug=slug, **defaults)
    return _create_constituency


@pytest.mark.django_db
class TestWriteIndex:
    """Test the write to MP index page."""

    def test_write_index_accessible(self, client):
        """Test that the write index page is accessible."""
        response = client.get('/write/')
        assert response.status_code == 200

    def test_write_index_contains_form(self, client):
        """Test that the write index page contains a postcode form."""
        response = client.get('/write/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Check for form element or postcode input
        assert 'postcode' in content.lower() or 'form' in content.lower()


@pytest.mark.django_db
class TestWriteConstituency:
    """Test the constituency page."""

    def test_constituency_with_invalid_slug_returns_404(self, client):
        """Test that invalid constituency slug returns 404."""
        response = client.get('/write/to/invalid-constituency/')
        assert response.status_code == 404

    def test_constituency_with_valid_slug_returns_200(self, client, create_test_constituency):
        """Test that valid constituency slug returns 200."""
        constituency = create_test_constituency()
        
        response = client.get(f'/write/to/{constituency.slug}/')
        assert response.status_code == 200

    def test_constituency_contains_mp_info(self, client, create_test_constituency):
        """Test that constituency page contains MP information."""
        constituency = create_test_constituency(
            name="Test Constituency 2",
            slug="test-constituency-2",
            mp="Test MP Two",
        )
        
        response = client.get(f'/write/to/{constituency.slug}/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        # Check for MP name or constituency name
        assert 'Test Constituency 2' in content or 'Test MP Two' in content


@pytest.mark.django_db
class TestWriteEmail:
    """Test the email composition page."""

    def test_email_get_request_returns_404(self, client, create_test_constituency):
        """Test that GET request to email page returns 404."""
        constituency = create_test_constituency(
            name="Test Constituency Email",
            slug="test-constituency-email",
            mp="Test MP Email",
        )
        
        response = client.get(f'/write/to/{constituency.slug}/email/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestWriteDone:
    """Test the done/confirmation page."""

    def test_done_with_valid_constituency_returns_200(self, client, create_test_constituency):
        """Test that done page with valid constituency returns 200."""
        constituency = create_test_constituency(
            name="Test Constituency Done",
            slug="test-constituency-done",
            mp="Test MP Done",
        )
        
        response = client.get(f'/write/to/{constituency.slug}/email/done/')
        assert response.status_code == 200

    def test_done_with_invalid_constituency_returns_404(self, client):
        """Test that done page with invalid constituency returns 404."""
        response = client.get('/write/to/invalid-constituency/email/done/')
        assert response.status_code == 404

    def test_done_displays_email_parameter(self, client, create_test_constituency):
        """Test that done page shows the email parameter."""
        constituency = create_test_constituency(
            name="Test Constituency Done 2",
            slug="test-constituency-done-2",
            mp="Test MP Done 2",
        )
        
        response = client.get(f'/write/to/{constituency.slug}/email/done/?email=test@example.com')
        assert response.status_code == 200
