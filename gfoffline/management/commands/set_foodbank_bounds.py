import logging
from django.core.management.base import BaseCommand

from givefood.models import Foodbank


class Command(BaseCommand):

    help = (
        'Set the map bounds (bounds_north, bounds_south, bounds_east, bounds_west) '
        'for all foodbanks based on their locations and donation points.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )
        parser.add_argument(
            '--slug',
            type=str,
            help='Only update a specific foodbank by slug'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        slug = options.get('slug')

        if slug:
            foodbanks = Foodbank.objects.filter(slug=slug)
            if not foodbanks.exists():
                self.stdout.write(
                    self.style.ERROR(f'Foodbank with slug "{slug}" not found')
                )
                return
        else:
            foodbanks = Foodbank.objects.all()

        foodbank_count = foodbanks.count()

        if dry_run:
            self.stdout.write(
                f"DRY RUN: Would update bounds for {foodbank_count} foodbanks..."
            )
        else:
            self.stdout.write(
                f"Setting bounds for {foodbank_count} foodbanks..."
            )

        counter = 0
        updated = 0
        for foodbank in foodbanks:
            counter += 1

            # Get bounds
            bounds = foodbank.get_bounds()
            north, south, east, west = bounds

            # Check if bounds have changed
            bounds_changed = (
                foodbank.bounds_north != north or
                foodbank.bounds_south != south or
                foodbank.bounds_east != east or
                foodbank.bounds_west != west
            )

            if bounds_changed:
                updated += 1
                if dry_run:
                    self.stdout.write(
                        f"  Would update {foodbank.name}: "
                        f"N={north:.6f}, S={south:.6f}, E={east:.6f}, W={west:.6f}"
                    )
                else:
                    foodbank.bounds_north = north
                    foodbank.bounds_south = south
                    foodbank.bounds_east = east
                    foodbank.bounds_west = west
                    # Use update_fields to avoid triggering full save() side effects
                    foodbank.save(update_fields=[
                        'bounds_north', 'bounds_south', 'bounds_east', 'bounds_west'
                    ])

            # Log progress for every 100 instances or key milestones
            if counter % 100 == 0 or counter == 1 or counter == foodbank_count:
                logging.info(
                    f"Processing {foodbank.name} ({counter} of {foodbank_count})"
                )
                self.stdout.write(
                    f"Processing ({counter} of {foodbank_count})..."
                )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN: Would have updated {updated} of {foodbank_count} foodbanks'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully set bounds for {updated} of {foodbank_count} foodbanks'
                )
            )
