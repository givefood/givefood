import json
import unicodecsv as csv

from django.http import HttpResponse

from givefood.models import Foodbank, FoodbankChangeLine, FoodbankDonationPoint

DEFAULT_FORMAT = "json"


def index(request):
    return HttpResponse("Give Food API 3")


def items(request):

    items = FoodbankChangeLine.objects.select_related("foodbank").all().order_by("created")

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="givefood_items.csv"'

    writer = csv.writer(response, quoting=csv.QUOTE_ALL)
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

    return response


def foodbanks(request):

    foodbanks = Foodbank.objects.select_related("latest_need").filter(is_closed=False).order_by("name")

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="givefood_foodbanks.csv"'

    writer = csv.writer(response, quoting=csv.QUOTE_ALL)
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

    return response


def company(request, slug):

    allowed_slugs = [dp.company_slug for dp in FoodbankDonationPoint.objects.all().distinct("company_slug")]
    if slug not in allowed_slugs:
        return HttpResponse(json.dumps({"error": "Company not found"}), content_type="application/json", status=404)
    
    donationpoints = FoodbankDonationPoint.objects.select_related("foodbank").select_related("foodbank__latest_need").filter(company_slug=slug).order_by("name")

    response_list = []
    
    for dp in donationpoints:
        response_list.append({
            "id": str(dp.uuid),
            "name": dp.name,
            "foodbank": {
                "id": str(dp.foodbank.uuid),
                "name": dp.foodbank.name,
                "alt_name": dp.foodbank.alt_name,
                "slug": dp.foodbank.slug,
                "url": dp.foodbank.url,
                "shopping_list_url": dp.foodbank.shopping_list_url,
                "phone_number": dp.foodbank.phone_number,
                "secondary_phone_number": dp.foodbank.secondary_phone_number,
                "email": dp.foodbank.contact_email,
                "address": dp.foodbank.address,
                "postcode": dp.foodbank.postcode,
                "country": dp.foodbank.country,
                "lat_lng": dp.foodbank.lat_lng,
                "charity_number": dp.foodbank.charity_number,
                "charity_register_url": dp.foodbank.charity_register_url(),
                "network": dp.foodbank.network,
                "need": {
                    "id": dp.foodbank.latest_need.need_id_str,
                    "items": dp.foodbank.latest_need.change_list(),
                    "excess": dp.foodbank.latest_need.excess_list(),
                    "found": str(dp.foodbank.latest_need.created),
                },
            },
            "address": dp.address,
            "postcode": dp.postcode,
            "country": dp.country,
            "lat_lng": dp.lat_lng,
            "place_id": dp.place_id,
            "store_id": dp.store_id,
        })

    return HttpResponse(json.dumps(response_list), content_type="application/json")