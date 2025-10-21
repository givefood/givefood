from django.core.management.base import BaseCommand

import csv, io

from givefood.models import Dump, Foodbank, FoodbankChangeLine


class Command(BaseCommand):

    help = 'Create dumps'
    
    def handle(self, *args, **options):


        self.stdout.write("Creating foodbank dump...")

        foodbanks = Foodbank.objects.select_related("latest_need").filter(is_closed=False).order_by("name")

        foodbank_dump = io.StringIO()
        writer = csv.writer(foodbank_dump, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "id",
            "organisation_name",
            "organisation_alt_name",
            "organisation_slug",
            "location_name",
            "location_slug",
            "url",
            "shopping_list_url",
            "rss_url",
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
            "food_standards_agency_id",
            "food_standards_agency_url",
            "network",
            "created",
            "modified",
            "edited",
            "need_id",
            "needed_items",
            "excess_items",
            "need_found",
            "footprintsqm",
        ])

        for foodbank in foodbanks:

            writer.writerow([
                str(foodbank.uuid),
                foodbank.name,
                foodbank.alt_name,
                foodbank.slug,
                "", 
                "",
                foodbank.url,
                foodbank.shopping_list_url,
                foodbank.rss_url,
                foodbank.phone_number,
                foodbank.secondary_phone_number,
                foodbank.contact_email,
                foodbank.address,
                foodbank.postcode,
                foodbank.country,
                foodbank.lat_lng,
                foodbank.place_id,
                foodbank.plus_code_compound,
                foodbank.plus_code_global,
                foodbank.lsoa,
                foodbank.msoa,
                foodbank.parliamentary_constituency_name,
                foodbank.mp_parl_id,
                foodbank.mp,
                foodbank.mp_party,
                foodbank.ward,
                foodbank.district,
                foodbank.charity_number,
                foodbank.charity_register_url(),
                foodbank.charity_name,
                foodbank.charity_type,
                foodbank.charity_reg_date,
                foodbank.charity_postcode,
                foodbank.charity_website,
                foodbank.fsa_id,
                foodbank.fsa_url(),
                foodbank.network,
                foodbank.created,
                foodbank.modified,
                foodbank.edited,
                foodbank.latest_need.need_id,
                foodbank.latest_need.change_text,
                foodbank.latest_need.excess_change_text,
                foodbank.latest_need.created,
                foodbank.footprint,
            ])

            for location in foodbank.locations():
                writer.writerow([
                    str(location.uuid),
                    foodbank.name,
                    foodbank.alt_name,
                    foodbank.slug,
                    location.name, 
                    location.slug,
                    foodbank.url,
                    foodbank.shopping_list_url,
                    foodbank.rss_url,
                    location.phone_or_foodbank_phone(),
                    "",
                    location.email_or_foodbank_email(),
                    location.address,
                    location.postcode,
                    foodbank.country,
                    location.lat_lng,
                    location.place_id,
                    location.plus_code_compound,
                    location.plus_code_global,
                    location.lsoa,
                    location.msoa,
                    location.parliamentary_constituency_name,
                    location.mp_parl_id,
                    location.mp,
                    location.mp_party,
                    location.ward,
                    location.district,
                    foodbank.charity_number,
                    foodbank.charity_register_url(),
                    foodbank.charity_name,
                    foodbank.charity_type,
                    foodbank.charity_reg_date,
                    foodbank.charity_postcode,
                    foodbank.charity_website,
                    None,
                    None,
                    foodbank.network,
                    foodbank.created,
                    location.modified,
                    location.edited,
                    foodbank.latest_need.need_id,
                    foodbank.latest_need.change_text,
                    foodbank.latest_need.excess_change_text,
                    foodbank.latest_need.created,
                    foodbank.footprint,
                ])

        foodbank_dump = foodbank_dump.getvalue()
        dump_instance = Dump(
            dump_type="foodbanks",
            dump_format="csv",
            the_dump=foodbank_dump,
            row_count=len(foodbanks),
        )
        dump_instance.save()

        del foodbank_dump

        self.stdout.write(f"Created dump {dump_instance.id} with {len(foodbanks)} foodbanks")

        self.stdout.write("Creating items dump...")

        items = FoodbankChangeLine.objects.select_related("foodbank").all().order_by("created").iterator()

        item_dump = io.StringIO()
        writer = csv.writer(item_dump, quoting=csv.QUOTE_ALL)
        writer.writerow([
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
        ])

        row_count = 0
        for item in items:
            writer.writerow([
                item.foodbank.uuid,
                item.foodbank.name,
                item.foodbank.alt_name,
                item.foodbank.slug,
                item.foodbank.network,
                item.foodbank.country,
                item.foodbank.lat_lng,
                item.type,
                item.item,
                item.category,
                item.group,
                item.created,
            ])
            row_count += 1
        
        item_dump = item_dump.getvalue()
        dump_instance = Dump(
            dump_type="items",
            dump_format="csv",
            the_dump=item_dump,
            row_count=row_count,
        )
        dump_instance.save()

        del item_dump

        self.stdout.write(f"Created dump {dump_instance.id} with {row_count} items")