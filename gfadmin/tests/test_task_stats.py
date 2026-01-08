"""Tests for task queue statistics on the admin index view."""
import pytest
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse

from django_tasks.backends.database.models import DBTaskResult
from django_tasks.base import TaskResultStatus


@pytest.mark.django_db
class TestTaskStats:
    """Test the task statistics logic on the admin index page."""

    def test_tasks_24h_counts_succeeded_tasks(self):
        """Test that tasks_24h includes SUCCEEDED tasks from the last 24 hours."""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Create a succeeded task within the last 24 hours
        DBTaskResult.objects.create(
            status=TaskResultStatus.SUCCEEDED,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=yesterday,
            finished_at=now - timedelta(hours=12),
        )
        
        # Query mimicking the view logic
        tasks_24h = DBTaskResult.objects.filter(
            finished_at__gte=yesterday
        ).filter(
            status__in=[TaskResultStatus.SUCCEEDED, TaskResultStatus.FAILED]
        ).count()
        
        assert tasks_24h == 1

    def test_tasks_24h_counts_failed_tasks(self):
        """Test that tasks_24h includes FAILED tasks from the last 24 hours."""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Create a failed task within the last 24 hours
        DBTaskResult.objects.create(
            status=TaskResultStatus.FAILED,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=yesterday,
            finished_at=now - timedelta(hours=12),
            exception_class_path='Exception',
            traceback='Test traceback',
        )
        
        # Query mimicking the view logic
        tasks_24h = DBTaskResult.objects.filter(
            finished_at__gte=yesterday
        ).filter(
            status__in=[TaskResultStatus.SUCCEEDED, TaskResultStatus.FAILED]
        ).count()
        
        assert tasks_24h == 1

    def test_tasks_24h_excludes_old_tasks(self):
        """Test that tasks_24h excludes tasks older than 24 hours."""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)
        
        # Create an old succeeded task (should be excluded)
        DBTaskResult.objects.create(
            status=TaskResultStatus.SUCCEEDED,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=two_days_ago,
            finished_at=two_days_ago + timedelta(hours=1),
        )
        
        # Query mimicking the view logic
        tasks_24h = DBTaskResult.objects.filter(
            finished_at__gte=yesterday
        ).filter(
            status__in=[TaskResultStatus.SUCCEEDED, TaskResultStatus.FAILED]
        ).count()
        
        assert tasks_24h == 0

    def test_tasks_24h_excludes_running_tasks(self):
        """Test that tasks_24h excludes RUNNING tasks."""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Create a running task
        DBTaskResult.objects.create(
            status=TaskResultStatus.RUNNING,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=yesterday,
            started_at=now - timedelta(hours=1),
        )
        
        # Query mimicking the view logic
        tasks_24h = DBTaskResult.objects.filter(
            finished_at__gte=yesterday
        ).filter(
            status__in=[TaskResultStatus.SUCCEEDED, TaskResultStatus.FAILED]
        ).count()
        
        assert tasks_24h == 0

    def test_tasks_outstanding_counts_ready_tasks(self):
        """Test that tasks_outstanding counts READY tasks."""
        now = timezone.now()
        
        # Create a ready task
        DBTaskResult.objects.create(
            status=TaskResultStatus.READY,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=now,
        )
        
        # Query mimicking the view logic
        tasks_outstanding = DBTaskResult.objects.filter(
            status=TaskResultStatus.READY
        ).count()
        
        assert tasks_outstanding == 1

    def test_tasks_outstanding_excludes_completed_tasks(self):
        """Test that tasks_outstanding excludes completed tasks."""
        now = timezone.now()
        
        # Create succeeded and failed tasks (should be excluded)
        DBTaskResult.objects.create(
            status=TaskResultStatus.SUCCEEDED,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=now,
            finished_at=now,
        )
        DBTaskResult.objects.create(
            status=TaskResultStatus.FAILED,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=now,
            finished_at=now,
            exception_class_path='Exception',
            traceback='Test traceback',
        )
        
        # Query mimicking the view logic
        tasks_outstanding = DBTaskResult.objects.filter(
            status=TaskResultStatus.READY
        ).count()
        
        assert tasks_outstanding == 0

    def test_tasks_outstanding_excludes_running_tasks(self):
        """Test that tasks_outstanding excludes RUNNING tasks."""
        now = timezone.now()
        
        # Create a running task (should be excluded from outstanding)
        DBTaskResult.objects.create(
            status=TaskResultStatus.RUNNING,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=now,
            started_at=now,
        )
        
        # Query mimicking the view logic
        tasks_outstanding = DBTaskResult.objects.filter(
            status=TaskResultStatus.READY
        ).count()
        
        assert tasks_outstanding == 0

    def test_admin_index_view_has_task_stats(self, client):
        """Test that the admin index view includes task statistics."""
        # Setup authenticated session
        session = client.session
        session['user_data'] = {
            'email': 'test@givefood.org.uk',
            'email_verified': True,
            'hd': 'givefood.org.uk',
        }
        session.save()
        
        # Create some tasks
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Create a test foodbank (required by admin index view)
        from givefood.models import Foodbank
        foodbank = Foodbank(
            name='Test Food Bank',
            slug='test-food-bank',
            address='123 Test St',
            postcode='TE1 1ST',
            lat_lng='51.5074,-0.1278',
            country='England',
            latitude=51.5074,
            longitude=-0.1278,
            is_closed=False,
            edited=now,
        )
        foodbank.save(do_geoupdate=False, do_decache=False)
        
        DBTaskResult.objects.create(
            status=TaskResultStatus.SUCCEEDED,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=yesterday,
            finished_at=now - timedelta(hours=12),
        )
        
        DBTaskResult.objects.create(
            status=TaskResultStatus.READY,
            task_path='test.task',
            args_kwargs={},
            backend_name='database',
            queue_name='default',
            run_after=now,
        )
        
        # Get the admin index page
        response = client.get(reverse('admin:index'))
        
        # Check that the response contains task statistics
        assert response.status_code == 200
        assert 'stats' in response.context
        assert 'tasks_24h' in response.context['stats']
        assert 'tasks_outstanding' in response.context['stats']
        assert response.context['stats']['tasks_24h'] == 1
        assert response.context['stats']['tasks_outstanding'] == 1
