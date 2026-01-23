"""
Management command to migrate cost fields from pence (integer) to pounds (decimal).

This command:
1. Adds the MoneyField columns to the database (cost, actual_cost, item_cost, line_cost
   and their corresponding currency columns)
2. Converts existing Order and OrderLine cost field values from pence (stored as integers)
   to pounds (stored as decimals) for use with django-money MoneyField

Usage:
    python manage.py migrate_cost_to_money --dry-run  # Preview changes
    python manage.py migrate_cost_to_money            # Execute migration
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from givefood.const.general import DEFAULT_CURRENCY


class Command(BaseCommand):
    help = (
        'Add MoneyField columns to database and migrate cost fields from pence (integer) '
        'to pounds (decimal) for Order and OrderLine models. Run with --dry-run first to preview changes.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving to database',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process at a time (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be saved')
            )

        self.stdout.write('Starting cost field migration...\n')

        # Step 1: Add MoneyField columns to database
        self._add_money_columns(dry_run)

        # Step 2: Migrate Order cost fields (convert pence to pounds)
        order_count = self._migrate_orders(dry_run, batch_size)

        # Step 3: Migrate OrderLine cost fields (convert pence to pounds)
        orderline_count = self._migrate_orderlines(dry_run, batch_size)

        # Summary
        self.stdout.write('\n' + '=' * 50)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN COMPLETE - Would have:\n'
                    f'  - Added MoneyField columns to givefood_order and givefood_orderline tables\n'
                    f'  - Migrated {order_count} Order records\n'
                    f'  - Migrated {orderline_count} OrderLine records'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Migration complete:\n'
                    f'  - Added MoneyField columns to database\n'
                    f'  - {order_count} Order records migrated\n'
                    f'  - {orderline_count} OrderLine records migrated'
                )
            )

    def _column_exists(self, table_name, column_name):
        """Check if a column exists in the given table (database agnostic)."""
        with connection.cursor() as cursor:
            # Get database vendor to use appropriate query
            vendor = connection.vendor
            
            if vendor == 'sqlite':
                # SQLite uses pragma_table_info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                return column_name in columns
            else:
                # PostgreSQL and other databases use information_schema
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                """, [table_name, column_name])
                return cursor.fetchone() is not None

    def _add_money_columns(self, dry_run):
        """Add MoneyField columns to Order and OrderLine tables."""
        self.stdout.write('\nAdding MoneyField columns to database...')

        # Define the columns to add for Order table
        order_columns = [
            # (column_name, sql_type, default_value, nullable)
            ('cost', 'DECIMAL(6, 2)', '0', False),
            ('cost_currency', 'VARCHAR(3)', f"'{DEFAULT_CURRENCY}'", False),
            ('actual_cost', 'DECIMAL(6, 2)', 'NULL', True),
            ('actual_cost_currency', 'VARCHAR(3)', f"'{DEFAULT_CURRENCY}'", True),
        ]

        # Define the columns to add for OrderLine table
        orderline_columns = [
            ('item_cost', 'DECIMAL(6, 2)', '0', False),
            ('item_cost_currency', 'VARCHAR(3)', f"'{DEFAULT_CURRENCY}'", False),
            ('line_cost', 'DECIMAL(6, 2)', '0', False),
            ('line_cost_currency', 'VARCHAR(3)', f"'{DEFAULT_CURRENCY}'", False),
        ]

        # Add columns to Order table
        self._add_columns_to_table('givefood_order', order_columns, dry_run)

        # Add columns to OrderLine table
        self._add_columns_to_table('givefood_orderline', orderline_columns, dry_run)

    def _add_columns_to_table(self, table_name, columns, dry_run):
        """Add columns to a table if they don't exist."""
        for column_name, sql_type, default_value, nullable in columns:
            if self._column_exists(table_name, column_name):
                self.stdout.write(f'  Column {table_name}.{column_name} already exists, skipping')
                continue

            null_clause = 'NULL' if nullable else 'NOT NULL'
            default_clause = f'DEFAULT {default_value}' if default_value else ''
            
            sql = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type} {null_clause} {default_clause}'
            
            if dry_run:
                self.stdout.write(f'  Would execute: {sql}')
            else:
                self.stdout.write(f'  Adding column {table_name}.{column_name}...')
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                self.stdout.write(f'    Added {table_name}.{column_name}')

    def _migrate_orders(self, dry_run, batch_size):
        """Migrate Order cost and actual_cost fields from pence to pounds using raw SQL."""
        self.stdout.write('\nMigrating Order records (converting pence to pounds)...')

        with connection.cursor() as cursor:
            # Count orders where cost > 100 (likely stored in pence)
            cursor.execute("""
                SELECT COUNT(*) FROM givefood_order 
                WHERE cost > 100 OR (actual_cost IS NOT NULL AND actual_cost > 100)
            """)
            total_to_migrate = cursor.fetchone()[0]
            
            self.stdout.write(f'Found {total_to_migrate} Order records to migrate')

            if total_to_migrate == 0:
                return 0

            if dry_run:
                # Show sample of what would change
                cursor.execute("""
                    SELECT id, order_id, cost, actual_cost FROM givefood_order 
                    WHERE cost > 100 OR (actual_cost IS NOT NULL AND actual_cost > 100)
                    LIMIT 10
                """)
                for row in cursor.fetchall():
                    order_id, order_name, cost, actual_cost = row
                    new_cost = cost / 100 if cost else cost
                    new_actual = actual_cost / 100 if actual_cost else actual_cost
                    self.stdout.write(
                        f'  Would migrate Order {order_name}: '
                        f'cost {cost} -> {new_cost}, actual_cost {actual_cost} -> {new_actual}'
                    )
                if total_to_migrate > 10:
                    self.stdout.write(f'  ... and {total_to_migrate - 10} more records')
            else:
                # Update cost field (divide by 100 to convert pence to pounds)
                cursor.execute("""
                    UPDATE givefood_order 
                    SET cost = cost / 100.0
                    WHERE cost > 100
                """)
                cost_updated = cursor.rowcount
                self.stdout.write(f'  Updated {cost_updated} Order.cost fields')

                # Update actual_cost field
                cursor.execute("""
                    UPDATE givefood_order 
                    SET actual_cost = actual_cost / 100.0
                    WHERE actual_cost IS NOT NULL AND actual_cost > 100
                """)
                actual_cost_updated = cursor.rowcount
                self.stdout.write(f'  Updated {actual_cost_updated} Order.actual_cost fields')

        return total_to_migrate

    def _migrate_orderlines(self, dry_run, batch_size):
        """Migrate OrderLine item_cost and line_cost fields from pence to pounds using raw SQL."""
        self.stdout.write('\nMigrating OrderLine records (converting pence to pounds)...')

        with connection.cursor() as cursor:
            # Count orderlines where costs > 100 (likely stored in pence)
            cursor.execute("""
                SELECT COUNT(*) FROM givefood_orderline 
                WHERE item_cost > 100 OR line_cost > 100
            """)
            total_to_migrate = cursor.fetchone()[0]
            
            self.stdout.write(f'Found {total_to_migrate} OrderLine records to migrate')

            if total_to_migrate == 0:
                return 0

            if dry_run:
                # Show sample of what would change
                cursor.execute("""
                    SELECT id, item_cost, line_cost FROM givefood_orderline 
                    WHERE item_cost > 100 OR line_cost > 100
                    LIMIT 10
                """)
                for row in cursor.fetchall():
                    line_id, item_cost, line_cost = row
                    new_item = item_cost / 100 if item_cost else item_cost
                    new_line = line_cost / 100 if line_cost else line_cost
                    self.stdout.write(
                        f'  Would migrate OrderLine {line_id}: '
                        f'item_cost {item_cost} -> {new_item}, line_cost {line_cost} -> {new_line}'
                    )
                if total_to_migrate > 10:
                    self.stdout.write(f'  ... and {total_to_migrate - 10} more records')
            else:
                # Update item_cost field (divide by 100 to convert pence to pounds)
                cursor.execute("""
                    UPDATE givefood_orderline 
                    SET item_cost = item_cost / 100.0
                    WHERE item_cost > 100
                """)
                item_cost_updated = cursor.rowcount
                self.stdout.write(f'  Updated {item_cost_updated} OrderLine.item_cost fields')

                # Update line_cost field
                cursor.execute("""
                    UPDATE givefood_orderline 
                    SET line_cost = line_cost / 100.0
                    WHERE line_cost > 100
                """)
                line_cost_updated = cursor.rowcount
                self.stdout.write(f'  Updated {line_cost_updated} OrderLine.line_cost fields')

        return total_to_migrate
