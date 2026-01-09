"""Tests for the admin frag endpoint."""
import pytest
from django.urls import reverse
from django_tasks.backends.database.models import DBTaskResult
from django_tasks.base import TaskResultStatus


@pytest.mark.django_db
class TestFragEndpoint:
    """Test the frag endpoint for CSI includes."""

    def test_frag_outstandingtaskcount_returns_count(self, client):
        """Test that outstandingtaskcount returns the correct count."""
        # Create some test tasks
        DBTaskResult.objects.create(
            status=TaskResultStatus.READY,
            task_name='test_task_1'
        )
        DBTaskResult.objects.create(
            status=TaskResultStatus.READY,
            task_name='test_task_2'
        )
        # Create a completed task (should not be counted)
        DBTaskResult.objects.create(
            status=TaskResultStatus.SUCCEEDED,
            task_name='test_task_3'
        )
        
        # Get the frag endpoint
        url = reverse('admin:frag', kwargs={'frag': 'outstandingtaskcount'})
        response = client.get(url)
        
        # Should return 200 OK
        assert response.status_code == 200
        # Should return just the count as text
        assert response.content.decode() == '2'

    def test_frag_outstandingtaskcount_returns_zero_when_empty(self, client):
        """Test that outstandingtaskcount returns zero when no tasks exist."""
        # Clear all tasks
        DBTaskResult.objects.all().delete()
        
        # Get the frag endpoint
        url = reverse('admin:frag', kwargs={'frag': 'outstandingtaskcount'})
        response = client.get(url)
        
        # Should return 200 OK
        assert response.status_code == 200
        # Should return zero
        assert response.content.decode() == '0'

    def test_frag_invalid_slug_returns_403(self, client):
        """Test that an invalid frag slug returns 403 Forbidden."""
        # Get the frag endpoint with invalid slug
        url = reverse('admin:frag', kwargs={'frag': 'invalid'})
        response = client.get(url)
        
        # Should return 403 Forbidden
        assert response.status_code == 403
