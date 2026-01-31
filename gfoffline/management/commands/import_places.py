import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from givefood.models import Place


class Command(BaseCommand):

    help = 'Replace all Places rows with the contents of places.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default=str(settings.BASE_DIR / 'givefood' / 'data' / 'places.csv'),
            help='Path to the places CSV file (default: givefood/data/places.csv)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without making changes'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process before committing (default: 1000)'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        if dry_run:
            self.stdout.write("DRY RUN: No changes will be made")

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file}"))
            return

        existing_count = Place.objects.count()
        self.stdout.write(f"Found {existing_count} existing places - these will be replaced")

        imported = 0
        would_import = 0
        skipped_missing_data = 0
        missing_field_counts = {
            'gbpnid': 0,
            'name': 0,
            'latitude': 0,
            'longitude': 0,
        }
        errors = 0
        total_rows = 0
        batch = []

        self.stdout.write(f"Opening CSV file: {csv_file}")

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_rows += 1

                # Get required fields
                gbpnid = row.get('GBPNID', '').strip()
                name = row.get('Place Name', '').strip()
                latitude = row.get('Latitude', '').strip()
                longitude = row.get('Longitude', '').strip()

                # Validate required fields
                if not gbpnid:
                    skipped_missing_data += 1
                    missing_field_counts['gbpnid'] += 1
                    continue

                if not name:
                    skipped_missing_data += 1
                    missing_field_counts['name'] += 1
                    continue

                if not latitude:
                    skipped_missing_data += 1
                    missing_field_counts['latitude'] += 1
                    continue

                if not longitude:
                    skipped_missing_data += 1
                    missing_field_counts['longitude'] += 1
                    continue

                lat_lng = f"{latitude},{longitude}"

                # Validate gbpnid is numeric
                try:
                    gbpnid_int = int(gbpnid)
                except ValueError:
                    skipped_missing_data += 1
                    missing_field_counts['gbpnid'] += 1
                    self.stdout.write(self.style.WARNING(
                        f"Row {total_rows}: Invalid gbpnid value '{gbpnid}' - skipping"
                    ))
                    continue

                if dry_run:
                    would_import += 1
                else:
                    place_obj = Place(
                        gbpnid=gbpnid_int,
                        name=name,
                        lat_lng=lat_lng,
                        histcounty=row.get('Historic County', '').strip() or None,
                        adcounty=row.get('Administrative County', '').strip() or None,
                        district=row.get('District', '').strip() or None,
                        uniauth=row.get('Unitary Authority Area', '').strip() or None,
                        police=row.get('Police Area', '').strip() or None,
                        region=row.get('Country', '').strip() or None,
                        type=row.get('Type', '').strip() or None,
                    )
                    batch.append(place_obj)

                # Progress every 10,000 rows
                if total_rows % 10000 == 0:
                    count = would_import if dry_run else len(batch) + imported
                    self.stdout.write(f"Processing row {total_rows}... (places: {count})")

        # Perform the replacement in a transaction
        if not dry_run and batch:
            self.stdout.write(f"Deleting {existing_count} existing places...")
            self.stdout.write(f"Importing {len(batch)} new places in batches of {batch_size}...")

            try:
                with transaction.atomic():
                    # Delete all existing places
                    Place.objects.all().delete()

                    # Bulk create in batches
                    for i in range(0, len(batch), batch_size):
                        batch_slice = batch[i:i + batch_size]
                        Place.objects.bulk_create(batch_slice)
                        imported += len(batch_slice)
                        self.stdout.write(f"Imported {imported} places...")

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Failed to import places: {e}"))
                return

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import complete!"))
        self.stdout.write(f"  Total rows processed: {total_rows}")
        if dry_run:
            self.stdout.write(f"  Would delete: {existing_count}")
            self.stdout.write(f"  Would import: {would_import}")
        else:
            self.stdout.write(f"  Deleted: {existing_count}")
            self.stdout.write(f"  Imported: {imported}")
        self.stdout.write(f"  Skipped (missing data): {skipped_missing_data}")
        if skipped_missing_data > 0:
            for field, count in missing_field_counts.items():
                if count > 0:
                    self.stdout.write(f"    - missing {field}: {count}")
        self.stdout.write(f"  Errors: {errors}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes were made"))
