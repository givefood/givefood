"""Tests for the migrate_cost_to_money management command."""
import pytest
from io import StringIO
from django.core.management import call_command


@pytest.mark.django_db
class TestMigrateCostToMoneyCommand:
    """Test the migrate_cost_to_money management command."""

    def test_command_runs_with_dry_run(self):
        """Test that the command runs successfully with --dry-run option."""
        out = StringIO()
        call_command('migrate_cost_to_money', '--dry-run', stdout=out)
        output = out.getvalue()
        
        assert 'DRY RUN' in output
        assert 'Starting cost field migration' in output
        assert 'Adding MoneyField columns' in output
        assert 'Migrating Order records' in output
        assert 'Migrating OrderLine records' in output

    def test_command_runs_without_dry_run(self):
        """Test that the command runs successfully without --dry-run option."""
        out = StringIO()
        call_command('migrate_cost_to_money', stdout=out)
        output = out.getvalue()
        
        assert 'Starting cost field migration' in output
        assert 'Adding MoneyField columns' in output
        assert 'Migration complete' in output

    def test_command_accepts_batch_size_argument(self):
        """Test that the command accepts --batch-size argument."""
        out = StringIO()
        call_command('migrate_cost_to_money', '--dry-run', '--batch-size=50', stdout=out)
        output = out.getvalue()
        
        assert 'DRY RUN' in output
