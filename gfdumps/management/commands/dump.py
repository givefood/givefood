from django.core.management.base import BaseCommand

import csv, io, json
from datetime import timedelta
import xml.etree.ElementTree as ET

from django.urls import reverse
from django.utils import timezone

from givefood.func import decache
from givefood.models import Dump, Foodbank, FoodbankChangeLine, FoodbankDonationPoint, FoodbankLocation


# Field names for foodbanks dump (used by both CSV and JSON)
FOODBANK_FIELDS = [
    "id",
    "organisation_name",
    "organisation_alt_name",
    "organisation_slug",
    "location_name",
    "location_slug",
    "url",
    "shopping_list_url",
    "rss_url",
    "donation_points_url",
    "locations_url",
    "contacts_url",
    "phone_number",
    "secondary_phone_number",
    "email",
    "address",
    "postcode",
    "country",
    "lat_lng",
    "place_id",
    "plus_code_compound",
    "plus_code_global",
    "lsoa",
    "msoa",
    "parliamentary_constituency",
    "mp_parliamentary_id",
    "mp",
    "mp_party",
    "ward",
    "district",
    "charity_number",
    "charity_register_url",
    "charity_name",
    "charity_type",
    "charity_reg_date",
    "charity_postcode",
    "charity_website",
    "charity_objectives",
    "charity_purpose",
    "food_standards_agency_id",
    "food_standards_agency_url",
    "network",
    "network_id",
    "is_school",
    "is_mobile",
    "is_area",
    "boundary",
    "created",
    "modified",
    "edited",
    "need_id",
    "needed_items",
    "excess_items",
    "need_found",
    "footprintsqm",
]

# Field names for items dump (used by both CSV and JSON)
ITEM_FIELDS = [
    "organisation_id",
    "organisation_name",
    "organisation_alt_name",
    "organisation_slug",
    "network",
    "country",
    "lat_lng",
    "type",
    "item",
    "category",
    "group",
    "created",
]

# Field names for donation points dump (used by both CSV and JSON)
DONATIONPOINT_FIELDS = [
    "id",
    "name",
    "slug",
    "address",
    "postcode",
    "lat_lng",
    "phone_number",
    "opening_hours",
    "wheelchair_accessible",
    "url",
    "in_store_only",
    "company",
    "store_id",
    "place_id",
    "plus_code_compound",
    "plus_code_global",
    "lsoa",
    "msoa",
    "parliamentary_constituency_name",
    "mp_parl_id",
    "mp",
    "mp_party",
    "ward",
    "district",
    "organisation_id",
    "organisation_name",
    "organisation_alt_name",
    "organisation_slug",
    "organisation_network",
    "organisation_country",
    "organisation_lat_lng",
]


def serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def rows_to_xml(rows, root_name, item_name):
    """Convert a list of row dictionaries to XML string using ElementTree for better performance."""
    root = ET.Element(root_name)
    for row in rows:
        item = ET.SubElement(root, item_name)
        for key, value in row.items():
            child = ET.SubElement(item, key)
            if value is None:
                child.text = None
            elif hasattr(value, 'isoformat'):
                child.text = value.isoformat()
            else:
                child.text = str(value) if value is not None else None
    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def build_foodbank_row(foodbank, location=None):
    """Build a row of data for a foodbank or location."""
    # Get latest_need values, handling None case
    if foodbank.latest_need:
        need_id = str(foodbank.latest_need.need_id)
        needed_items = foodbank.latest_need.change_text
        excess_items = foodbank.latest_need.excess_change_text
        need_found = foodbank.latest_need.created
    else:
        need_id = None
        needed_items = None
        excess_items = None
        need_found = None

    if location:
        return {
            "id": str(location.uuid),
            "organisation_name": foodbank.name,
            "organisation_alt_name": foodbank.alt_name,
            "organisation_slug": foodbank.slug,
            "location_name": location.name,
            "location_slug": location.slug,
            "url": foodbank.url,
            "shopping_list_url": foodbank.shopping_list_url,
            "rss_url": foodbank.rss_url,
            "donation_points_url": foodbank.donation_points_url,
            "locations_url": foodbank.locations_url,
            "contacts_url": foodbank.contacts_url,
            "phone_number": location.phone_or_foodbank_phone(),
            "secondary_phone_number": "",
            "email": location.email_or_foodbank_email(),
            "address": location.address,
            "postcode": location.postcode,
            "country": foodbank.country,
            "lat_lng": location.lat_lng,
            "place_id": location.place_id,
            "plus_code_compound": location.plus_code_compound,
            "plus_code_global": location.plus_code_global,
            "lsoa": location.lsoa,
            "msoa": location.msoa,
            "parliamentary_constituency": location.parliamentary_constituency_name,
            "mp_parliamentary_id": location.mp_parl_id,
            "mp": location.mp,
            "mp_party": location.mp_party,
            "ward": location.ward,
            "district": location.district,
            "charity_number": foodbank.charity_number,
            "charity_register_url": foodbank.charity_register_url(),
            "charity_name": foodbank.charity_name,
            "charity_type": foodbank.charity_type,
            "charity_reg_date": foodbank.charity_reg_date,
            "charity_postcode": foodbank.charity_postcode,
            "charity_website": foodbank.charity_website,
            "charity_objectives": foodbank.charity_objectives,
            "charity_purpose": foodbank.charity_purpose,
            "food_standards_agency_id": None,
            "food_standards_agency_url": None,
            "network": foodbank.network,
            "network_id": foodbank.network_id,
            "is_school": foodbank.is_school,
            "is_mobile": location.is_mobile,
            "is_area": bool(location.boundary_geojson),
            "boundary": location.boundary_geojson,
            "created": foodbank.created,
            "modified": location.modified,
            "edited": location.edited,
            "need_id": need_id,
            "needed_items": needed_items,
            "excess_items": excess_items,
            "need_found": need_found,
            "footprintsqm": foodbank.footprint,
        }
    else:
        return {
            "id": str(foodbank.uuid),
            "organisation_name": foodbank.name,
            "organisation_alt_name": foodbank.alt_name,
            "organisation_slug": foodbank.slug,
            "location_name": "",
            "location_slug": "",
            "url": foodbank.url,
            "shopping_list_url": foodbank.shopping_list_url,
            "rss_url": foodbank.rss_url,
            "donation_points_url": foodbank.donation_points_url,
            "locations_url": foodbank.locations_url,
            "contacts_url": foodbank.contacts_url,
            "phone_number": foodbank.phone_number,
            "secondary_phone_number": foodbank.secondary_phone_number,
            "email": foodbank.contact_email,
            "address": foodbank.address,
            "postcode": foodbank.postcode,
            "country": foodbank.country,
            "lat_lng": foodbank.lat_lng,
            "place_id": foodbank.place_id,
            "plus_code_compound": foodbank.plus_code_compound,
            "plus_code_global": foodbank.plus_code_global,
            "lsoa": foodbank.lsoa,
            "msoa": foodbank.msoa,
            "parliamentary_constituency": foodbank.parliamentary_constituency_name,
            "mp_parliamentary_id": foodbank.mp_parl_id,
            "mp": foodbank.mp,
            "mp_party": foodbank.mp_party,
            "ward": foodbank.ward,
            "district": foodbank.district,
            "charity_number": foodbank.charity_number,
            "charity_register_url": foodbank.charity_register_url(),
            "charity_name": foodbank.charity_name,
            "charity_type": foodbank.charity_type,
            "charity_reg_date": foodbank.charity_reg_date,
            "charity_postcode": foodbank.charity_postcode,
            "charity_website": foodbank.charity_website,
            "charity_objectives": foodbank.charity_objectives,
            "charity_purpose": foodbank.charity_purpose,
            "food_standards_agency_id": foodbank.fsa_id,
            "food_standards_agency_url": foodbank.fsa_url(),
            "network": foodbank.network,
            "network_id": foodbank.network_id,
            "is_school": foodbank.is_school,
            "is_mobile": None,
            "is_area": None,
            "boundary": None,
            "created": foodbank.created,
            "modified": foodbank.modified,
            "edited": foodbank.edited,
            "need_id": need_id,
            "needed_items": needed_items,
            "excess_items": excess_items,
            "need_found": need_found,
            "footprintsqm": foodbank.footprint,
        }


def build_item_row(item):
    """Build a row of data for an item."""
    return {
        "organisation_id": str(item.foodbank.uuid),
        "organisation_name": item.foodbank.name,
        "organisation_alt_name": item.foodbank.alt_name,
        "organisation_slug": item.foodbank.slug,
        "network": item.foodbank.network,
        "country": item.foodbank.country,
        "lat_lng": item.foodbank.lat_lng,
        "type": item.type,
        "item": item.item,
        "category": item.category,
        "group": item.group,
        "created": item.created,
    }


def build_donationpoint_row(donationpoint, is_location=False):
    """Build a row of data for a donation point."""
    if is_location:
        return {
            "id": str(donationpoint.uuid),
            "name": donationpoint.name,
            "slug": donationpoint.slug,
            "address": donationpoint.address,
            "postcode": donationpoint.postcode,
            "lat_lng": donationpoint.lat_lng,
            "phone_number": donationpoint.phone_number,
            "opening_hours": None,
            "wheelchair_accessible": None,
            "url": None,
            "in_store_only": None,
            "company": None,
            "store_id": None,
            "place_id": donationpoint.place_id,
            "plus_code_compound": donationpoint.plus_code_compound,
            "plus_code_global": donationpoint.plus_code_global,
            "lsoa": donationpoint.lsoa,
            "msoa": donationpoint.msoa,
            "parliamentary_constituency_name": donationpoint.parliamentary_constituency_name,
            "mp_parl_id": donationpoint.mp_parl_id,
            "mp": donationpoint.mp,
            "mp_party": donationpoint.mp_party,
            "ward": donationpoint.ward,
            "district": donationpoint.district,
            "organisation_id": str(donationpoint.foodbank.uuid),
            "organisation_name": donationpoint.foodbank.name,
            "organisation_alt_name": donationpoint.foodbank.alt_name,
            "organisation_slug": donationpoint.foodbank.slug,
            "organisation_network": donationpoint.foodbank.network,
            "organisation_country": donationpoint.foodbank.country,
            "organisation_lat_lng": donationpoint.foodbank.lat_lng,
        }
    else:
        return {
            "id": str(donationpoint.uuid),
            "name": donationpoint.name,
            "slug": donationpoint.slug,
            "address": donationpoint.address,
            "postcode": donationpoint.postcode,
            "lat_lng": donationpoint.lat_lng,
            "phone_number": donationpoint.phone_number,
            "opening_hours": donationpoint.opening_hours,
            "wheelchair_accessible": donationpoint.wheelchair_accessible,
            "url": donationpoint.url,
            "in_store_only": donationpoint.in_store_only,
            "company": donationpoint.company,
            "store_id": donationpoint.store_id,
            "place_id": donationpoint.place_id,
            "plus_code_compound": donationpoint.plus_code_compound,
            "plus_code_global": donationpoint.plus_code_global,
            "lsoa": donationpoint.lsoa,
            "msoa": donationpoint.msoa,
            "parliamentary_constituency_name": donationpoint.parliamentary_constituency_name,
            "mp_parl_id": donationpoint.mp_parl_id,
            "mp": donationpoint.mp,
            "mp_party": donationpoint.mp_party,
            "ward": donationpoint.ward,
            "district": donationpoint.district,
            "organisation_id": str(donationpoint.foodbank.uuid),
            "organisation_name": donationpoint.foodbank.name,
            "organisation_alt_name": donationpoint.foodbank.alt_name,
            "organisation_slug": donationpoint.foodbank.slug,
            "organisation_network": donationpoint.foodbank.network,
            "organisation_country": donationpoint.foodbank.country,
            "organisation_lat_lng": donationpoint.foodbank.lat_lng,
        }


def row_to_csv_values(row, fields):
    """Convert a row dict to a list of values in the order of fields."""
    return [row[field] for field in fields]


class Command(BaseCommand):

    help = 'Create dumps'
    
    def handle(self, *args, **options):

        # ==================== FOODBANKS ====================
        self.stdout.write("Creating foodbank dumps...")

        foodbanks = Foodbank.objects.select_related("latest_need").filter(is_closed=False).order_by("name")

        # Build rows for both CSV and JSON
        foodbank_rows = []
        for foodbank in foodbanks:
            foodbank_rows.append(build_foodbank_row(foodbank))
            for location in foodbank.locations():
                foodbank_rows.append(build_foodbank_row(foodbank, location))

        row_count = len(foodbank_rows)

        # CSV dump
        foodbank_csv = io.StringIO()
        writer = csv.writer(foodbank_csv, quoting=csv.QUOTE_ALL)
        writer.writerow(FOODBANK_FIELDS)
        for row in foodbank_rows:
            writer.writerow(row_to_csv_values(row, FOODBANK_FIELDS))

        dump_instance = Dump(
            dump_type="foodbanks",
            dump_format="csv",
            the_dump=foodbank_csv.getvalue(),
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created CSV dump {dump_instance.id} with {row_count} foodbanks")

        # JSON dump
        foodbank_json = json.dumps(foodbank_rows, default=serialize_datetime, indent=2)
        dump_instance = Dump(
            dump_type="foodbanks",
            dump_format="json",
            the_dump=foodbank_json,
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created JSON dump {dump_instance.id} with {row_count} foodbanks")

        # XML dump
        foodbank_xml = rows_to_xml(foodbank_rows, 'foodbanks', 'foodbank')
        dump_instance = Dump(
            dump_type="foodbanks",
            dump_format="xml",
            the_dump=foodbank_xml,
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created XML dump {dump_instance.id} with {row_count} foodbanks")

        del foodbank_rows, foodbank_csv, foodbank_json, foodbank_xml

        # ==================== ITEMS ====================
        self.stdout.write("Creating items dumps...")

        items = FoodbankChangeLine.objects.select_related("foodbank").all().order_by("created").iterator()

        # Build rows for both CSV and JSON
        item_rows = []
        for item in items:
            item_rows.append(build_item_row(item))

        row_count = len(item_rows)

        # CSV dump
        item_csv = io.StringIO()
        writer = csv.writer(item_csv, quoting=csv.QUOTE_ALL)
        writer.writerow(ITEM_FIELDS)
        for row in item_rows:
            writer.writerow(row_to_csv_values(row, ITEM_FIELDS))

        dump_instance = Dump(
            dump_type="items",
            dump_format="csv",
            the_dump=item_csv.getvalue(),
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created CSV dump {dump_instance.id} with {row_count} items")

        # JSON dump
        item_json = json.dumps(item_rows, default=serialize_datetime, indent=2)
        dump_instance = Dump(
            dump_type="items",
            dump_format="json",
            the_dump=item_json,
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created JSON dump {dump_instance.id} with {row_count} items")

        # XML dump
        item_xml = rows_to_xml(item_rows, 'items', 'item')
        dump_instance = Dump(
            dump_type="items",
            dump_format="xml",
            the_dump=item_xml,
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created XML dump {dump_instance.id} with {row_count} items")

        del item_rows, item_csv, item_json, item_xml

        # ==================== DONATION POINTS ====================
        self.stdout.write("Creating donationpoints dumps...")

        # Build rows for both CSV and JSON
        donationpoint_rows = []

        # Include FoodbankDonationPoint objects
        donationpoints = FoodbankDonationPoint.objects.select_related("foodbank").filter(is_closed=False).order_by("name").iterator()
        for donationpoint in donationpoints:
            donationpoint_rows.append(build_donationpoint_row(donationpoint, is_location=False))

        # Include FoodbankLocation objects with is_donation_point=True
        locations = FoodbankLocation.objects.select_related("foodbank").filter(is_closed=False, is_donation_point=True).order_by("name").iterator()
        for location in locations:
            donationpoint_rows.append(build_donationpoint_row(location, is_location=True))

        row_count = len(donationpoint_rows)

        # CSV dump
        donationpoint_csv = io.StringIO()
        writer = csv.writer(donationpoint_csv, quoting=csv.QUOTE_ALL)
        writer.writerow(DONATIONPOINT_FIELDS)
        for row in donationpoint_rows:
            writer.writerow(row_to_csv_values(row, DONATIONPOINT_FIELDS))

        dump_instance = Dump(
            dump_type="donationpoints",
            dump_format="csv",
            the_dump=donationpoint_csv.getvalue(),
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created CSV dump {dump_instance.id} with {row_count} donationpoints")

        # JSON dump
        donationpoint_json = json.dumps(donationpoint_rows, default=serialize_datetime, indent=2)
        dump_instance = Dump(
            dump_type="donationpoints",
            dump_format="json",
            the_dump=donationpoint_json,
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created JSON dump {dump_instance.id} with {row_count} donationpoints")

        # XML dump
        donationpoint_xml = rows_to_xml(donationpoint_rows, 'donationpoints', 'donationpoint')
        dump_instance = Dump(
            dump_type="donationpoints",
            dump_format="xml",
            the_dump=donationpoint_xml,
            row_count=row_count,
        )
        dump_instance.save()
        self.stdout.write(f"Created XML dump {dump_instance.id} with {row_count} donationpoints")

        del donationpoint_rows, donationpoint_csv, donationpoint_json, donationpoint_xml

        # ==================== CLEANUP ====================
        self.stdout.write("Deleting old dumps...")

        cutoff_date = timezone.now() - timedelta(days=28)
        old_dumps = Dump.objects.filter(created__lt=cutoff_date).exclude(created__day=1)
        deleted_count = old_dumps.count()
        old_dumps.delete()

        self.stdout.write(f"Deleted {deleted_count} old dumps")

        decache(prefixes=[reverse("dumps:dump_index")])
        decache(urls=[reverse("gfapi2:index")])
