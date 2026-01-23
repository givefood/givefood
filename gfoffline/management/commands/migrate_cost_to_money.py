"""
Management command to migrate cost fields from pence (integer) to pounds (decimal).

This command converts existing Order and OrderLine cost field values from pence
(stored as integers) to pounds (stored as decimals) for use with django-money MoneyField.

Usage:
    python manage.py migrate_cost_to_money --dry-run  # Preview changes
    python manage.py migrate_cost_to_money            # Execute migration
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from givefood.models import Order, OrderLine


class Command(BaseCommand):
    help = (
        'Migrate cost fields from pence (integer) to pounds (decimal) '
        'for Order and OrderLine models. Run with --dry-run first to preview changes.'
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

        self.stdout.write('Starting cost migration...\n')

        # Migrate Order cost fields
        order_count = self._migrate_orders(dry_run, batch_size)

        # Migrate OrderLine cost fields
        orderline_count = self._migrate_orderlines(dry_run, batch_size)

        # Summary
        self.stdout.write('\n' + '=' * 50)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN COMPLETE - Would have migrated:\n'
                    f'  - {order_count} Order records\n'
                    f'  - {orderline_count} OrderLine records'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Migration complete:\n'
                    f'  - {order_count} Order records migrated\n'
                    f'  - {orderline_count} OrderLine records migrated'
                )
            )

    def _migrate_orders(self, dry_run, batch_size):
        """Migrate Order cost and actual_cost fields from pence to pounds."""
        self.stdout.write('\nMigrating Order records...')

        # Get orders where cost appears to be in pence (> 100, which would be > £1)
        # This heuristic assumes costs stored as integers > 100 are likely pence
        orders = Order.objects.all()
        total_count = orders.count()
        migrated_count = 0

        self.stdout.write(f'Found {total_count} Order records to check')

        for i, order in enumerate(orders.iterator(chunk_size=batch_size)):
            needs_update = False
            original_cost = order.cost
            original_actual_cost = order.actual_cost

            # Check if cost looks like it's in pence (amount > 100)
            # MoneyField stores Decimal, so we check the amount attribute
            if order.cost and hasattr(order.cost, 'amount'):
                cost_amount = order.cost.amount
                if cost_amount > 100:
                    # Convert pence to pounds
                    order.cost.amount = cost_amount / Decimal('100')
                    needs_update = True

            # Check actual_cost similarly
            if order.actual_cost and hasattr(order.actual_cost, 'amount'):
                actual_cost_amount = order.actual_cost.amount
                if actual_cost_amount > 100:
                    order.actual_cost.amount = actual_cost_amount / Decimal('100')
                    needs_update = True

            if needs_update:
                migrated_count += 1
                if dry_run:
                    self.stdout.write(
                        f'  Would migrate Order {order.order_id}: '
                        f'cost {original_cost} -> {order.cost}, '
                        f'actual_cost {original_actual_cost} -> {order.actual_cost}'
                    )
                else:
                    # Use update() to avoid triggering save() side effects
                    Order.objects.filter(pk=order.pk).update(
                        cost=order.cost,
                        actual_cost=order.actual_cost
                    )
                    if (migrated_count % batch_size == 0):
                        self.stdout.write(f'  Migrated {migrated_count} orders...')

        return migrated_count

    def _migrate_orderlines(self, dry_run, batch_size):
        """Migrate OrderLine item_cost and line_cost fields from pence to pounds."""
        self.stdout.write('\nMigrating OrderLine records...')

        orderlines = OrderLine.objects.all()
        total_count = orderlines.count()
        migrated_count = 0

        self.stdout.write(f'Found {total_count} OrderLine records to check')

        for i, orderline in enumerate(orderlines.iterator(chunk_size=batch_size)):
            needs_update = False
            original_item_cost = orderline.item_cost
            original_line_cost = orderline.line_cost

            # Check if item_cost looks like it's in pence (amount > 100)
            if orderline.item_cost and hasattr(orderline.item_cost, 'amount'):
                item_cost_amount = orderline.item_cost.amount
                if item_cost_amount > 100:
                    orderline.item_cost.amount = item_cost_amount / Decimal('100')
                    needs_update = True

            # Check line_cost similarly
            if orderline.line_cost and hasattr(orderline.line_cost, 'amount'):
                line_cost_amount = orderline.line_cost.amount
                if line_cost_amount > 100:
                    orderline.line_cost.amount = line_cost_amount / Decimal('100')
                    needs_update = True

            if needs_update:
                migrated_count += 1
                if dry_run:
                    self.stdout.write(
                        f'  Would migrate OrderLine {orderline.pk}: '
                        f'item_cost {original_item_cost} -> {orderline.item_cost}, '
                        f'line_cost {original_line_cost} -> {orderline.line_cost}'
                    )
                else:
                    OrderLine.objects.filter(pk=orderline.pk).update(
                        item_cost=orderline.item_cost,
                        line_cost=orderline.line_cost
                    )
                    if (migrated_count % batch_size == 0):
                        self.stdout.write(f'  Migrated {migrated_count} order lines...')

        return migrated_count
