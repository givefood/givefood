import csv
import logging
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from givefood.models import Postcode


class Command(BaseCommand):

    help = 'Import postcodes from a CSV file. Only imports postcodes that are "In Use".'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the postcodes CSV file'
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

        # Get existing postcodes for restart support
        existing_postcodes = set(Postcode.objects.values_list('postcode', flat=True))
        existing_count = len(existing_postcodes)
        
        if existing_count > 0:
            self.stdout.write(f"Found {existing_count} existing postcodes - will skip these (restartable import)")

        imported = 0
        would_import = 0  # Counter for dry-run mode
        skipped_not_in_use = 0
        skipped_existing = 0
        skipped_missing_data = 0
        errors = 0
        total_rows = 0
        batch = []

        self.stdout.write(f"Opening CSV file: {csv_file}")

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_rows += 1

                # Check if postcode is in use
                in_use = row.get('In Use?', '').strip()
                if in_use != 'Yes':
                    skipped_not_in_use += 1
                    # Progress every 100,000 rows
                    if total_rows % 100000 == 0:
                        count = would_import if dry_run else imported
                        self.stdout.write(f"Processing row {total_rows}... (imported: {count}, skipped not in use: {skipped_not_in_use}, skipped existing: {skipped_existing})")
                    continue

                postcode = row.get('Postcode', '').strip()
                
                # Skip if postcode is empty
                if not postcode:
                    skipped_missing_data += 1
                    continue

                # Skip if postcode already exists (restartable support)
                if postcode in existing_postcodes:
                    skipped_existing += 1
                    if total_rows % 100000 == 0:
                        count = would_import if dry_run else imported
                        self.stdout.write(f"Processing row {total_rows}... (imported: {count}, skipped not in use: {skipped_not_in_use}, skipped existing: {skipped_existing})")
                    continue

                # Build lat_lng from Latitude and Longitude
                latitude = row.get('Latitude', '').strip()
                longitude = row.get('Longitude', '').strip()
                
                # Skip postcodes with missing coordinates
                if not latitude or not longitude:
                    skipped_missing_data += 1
                    continue
                
                lat_lng = f"{latitude},{longitude}"

                # Get and validate country (required field)
                country = row.get('Country', '').strip()
                if not country:
                    skipped_missing_data += 1
                    continue

                if dry_run:
                    would_import += 1
                else:
                    postcode_obj = Postcode(
                        postcode=postcode,
                        lat_lng=lat_lng,
                        county=row.get('County', '').strip() or None,
                        district=row.get('District', '').strip() or None,
                        ward=row.get('Ward', '').strip() or None,
                        country=country,
                        region=row.get('Region', '').strip() or None,
                        lsoa=row.get('LSOA Code', '').strip() or None,
                        msoa=row.get('MSOA Code', '').strip() or None,
                        police=row.get('Police force', '').strip() or None,
                    )
                    batch.append(postcode_obj)
                    existing_postcodes.add(postcode)  # Track newly imported

                    # Bulk create when batch is full
                    if len(batch) >= batch_size:
                        try:
                            Postcode.objects.bulk_create(batch, ignore_conflicts=True)
                            imported += len(batch)
                        except (IntegrityError, Exception) as e:
                            # Log the error and try to insert one by one
                            logging.warning(f"Batch insert failed, trying individual inserts: {e}")
                            for obj in batch:
                                try:
                                    obj.save()
                                    imported += 1
                                except Exception as obj_error:
                                    errors += 1
                                    logging.error(f"Failed to save postcode {obj.postcode}: {obj_error}")
                        batch = []

                # Progress every 10,000 imported postcodes
                count = would_import if dry_run else imported
                if count > 0 and count % 10000 == 0:
                    self.stdout.write(f"Imported {count} postcodes... (row {total_rows})")
                    logging.info(f"Imported {count} postcodes at row {total_rows}")

        # Save any remaining batch
        if batch and not dry_run:
            try:
                Postcode.objects.bulk_create(batch, ignore_conflicts=True)
                imported += len(batch)
            except (IntegrityError, Exception) as e:
                # Log the error and try to insert one by one
                logging.warning(f"Final batch insert failed, trying individual inserts: {e}")
                for obj in batch:
                    try:
                        obj.save()
                        imported += 1
                    except Exception as obj_error:
                        errors += 1
                        logging.error(f"Failed to save postcode {obj.postcode}: {obj_error}")

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import complete!"))
        self.stdout.write(f"  Total rows processed: {total_rows}")
        if dry_run:
            self.stdout.write(f"  Would import: {would_import}")
        else:
            self.stdout.write(f"  Imported: {imported}")
        self.stdout.write(f"  Skipped (not in use): {skipped_not_in_use}")
        self.stdout.write(f"  Skipped (already existing): {skipped_existing}")
        self.stdout.write(f"  Skipped (missing data): {skipped_missing_data}")
        self.stdout.write(f"  Errors: {errors}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes were made"))
