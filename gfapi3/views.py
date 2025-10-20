import json
import unicodecsv as csv

from django.http import HttpResponse

from givefood.models import Foodbank, FoodbankChangeLine, FoodbankDonationPoint

DEFAULT_FORMAT = "json"


def index(request):
    return HttpResponse("Give Food API 3")


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