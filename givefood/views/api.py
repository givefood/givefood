import json, urllib

from google.appengine.api import urlfetch
import unicodecsv as csv

from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.utils.timesince import timesince
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404

from givefood.func import find_foodbanks, get_all_foodbanks, geocode
from givefood.models import ApiFoodbankSearch, Foodbank


@cache_page(60*10)
def api_foodbanks(request):

    allowed_formats = [
        "json",
        "csv",
    ]
    default_format = "json"

    foodbanks = get_all_foodbanks()
    response_list = []

    format = request.GET.get("format", default_format)

    if format not in allowed_formats:
        return HttpResponseBadRequest

    for foodbank in foodbanks:
        response_list.append({
            "name":foodbank.name,
            "slug":foodbank.slug,
            "url":foodbank.url,
            "shopping_list_url":foodbank.shopping_list_url,
            "phone":foodbank.phone_number,
            "email":foodbank.contact_email,
            "address":foodbank.full_address(),
            "postcode":foodbank.postcode,
            "parliamentary_constituency":foodbank.parliamentary_constituency,
            "mp":foodbank.mp,
            "mp_party":foodbank.mp_party,
            "ward":foodbank.ward,
            "district":foodbank.district,
            "country":foodbank.country,
            "charity_number":foodbank.charity_number,
            "charity_register_url":foodbank.charity_register_url(),
            "closed":foodbank.is_closed,
            "latt_long":foodbank.latt_long,
            "network":foodbank.network,
        })

    if format == "json":
        return JsonResponse(response_list, safe=False)

    if format == "csv":
        response = HttpResponse(content_type='text/csv')
        writer = csv.writer(response)
        writer.writerow([
            "name",
            "slug",
            "url",
            "shopping_list_url",
            "phone",
            "email",
            "address",
            "postcode",
            "parliamentary_constituency",
            "mp",
            "mp_party",
            "ward",
            "district",
            "country",
            "charity_number",
            "charity_register_url",
            "closed",
            "latt_long",
        ])
        writer_output = []
        for foodbank in response_list:
            writer_output.append([
                foodbank["name"],
                foodbank["slug"],
                foodbank["url"],
                foodbank["shopping_list_url"],
                foodbank["phone"],
                foodbank["email"],
                foodbank["address"],
                foodbank["postcode"],
                foodbank["parliamentary_constituency"],
                foodbank["mp"],
                foodbank["mp_party"],
                foodbank["ward"],
                foodbank["district"],
                foodbank["country"],
                foodbank["charity_number"],
                foodbank["charity_register_url"],
                foodbank["closed"],
                foodbank["latt_long"],
            ])
        writer.writerows(writer_output)
        return response



@cache_page(60*10)
def api_foodbank_search(request):

    latt_long = request.GET.get("lattlong")
    address = request.GET.get("address")

    if not latt_long and not address:
        return HttpResponseBadRequest()

    if address and not latt_long:
        latt_long = geocode(address)

    foodbanks = find_foodbanks(latt_long, 10)
    response_list = []

    if address:
        query_type = "address"
        query = address
    else:
        query_type = "lattlong"
        query = latt_long

    api_hit = ApiFoodbankSearch(
        query_type = query_type,
        query = query,
        nearest_foodbank = foodbanks[0].distance_m,
        latt_long = latt_long,
    )
    api_hit.save()

    for foodbank in foodbanks:
        response_list.append({
            "name":foodbank.name,
            "slug":foodbank.slug,
            "distance_m":int(foodbank.distance_m),
            "distance_mi":round(foodbank.distance_mi,2),
            "url":foodbank.url,
            "shopping_list_url":foodbank.shopping_list_url,
            "phone":foodbank.phone_number,
            "email":foodbank.contact_email,
            "address":foodbank.full_address(),
            "postcode":foodbank.postcode,
            "country":foodbank.country,
            "parliamentary_constituency":foodbank.parliamentary_constituency,
            "mp":foodbank.mp,
            "mp_party":foodbank.mp_party,
            "ward":foodbank.ward,
            "district":foodbank.district,
            "charity_number":foodbank.charity_number,
            "charity_register_url":foodbank.charity_register_url(),
            "needs":foodbank.latest_need_text(),
            "number_needs":foodbank.latest_need_text().count('\n')+1,
            "need_id":foodbank.latest_need_id(),
            "updated":str(foodbank.latest_need_date()),
            "updated_text":timesince(foodbank.latest_need_date()),
        })

    return JsonResponse(response_list, safe=False)


@cache_page(60*10)
def api_foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    locations = foodbank.locations()

    locations_list = []
    for location in locations:
        locations_list.append({
            "name":location.name,
            "address":location.address,
            "postcode":location.postcode,
            "latt_long":location.latt_long,
            "phone":location.phone_number,
            "parliamentary_constituency":location.parliamentary_constituency,
            "mp":location.mp,
            "mp_party":location.mp_party,
            "ward":location.ward,
            "district":location.district,
        })

    foodbank_response = {
        "name":foodbank.name,
        "slug":foodbank.slug,
        "url":foodbank.url,
        "shopping_list_url":foodbank.shopping_list_url,
        "phone":foodbank.phone_number,
        "email":foodbank.contact_email,
        "address":foodbank.address,
        "postcode":foodbank.postcode,
        "country":foodbank.country,
        "parliamentary_constituency":foodbank.parliamentary_constituency,
        "mp":foodbank.mp,
        "mp_party":foodbank.mp_party,
        "ward":foodbank.ward,
        "district":foodbank.district,
        "charity_number":foodbank.charity_number,
        "charity_register_url":foodbank.charity_register_url(),
        "closed":foodbank.is_closed,
        "latt_long":foodbank.latt_long,
        "network":foodbank.network,
        "needs":foodbank.latest_need_text(),
        "number_needs":foodbank.latest_need_text().count('\n')+1,
        "need_found":foodbank.last_need,
        "need_id":foodbank.latest_need_id(),
        "locations":locations_list,
        "updated":str(foodbank.latest_need_date()),
        "updated_text":timesince(foodbank.latest_need_date()),
    }

    return JsonResponse(foodbank_response, safe=False)


@cache_page(60*10)
def api_foodbank_key(request):
    key = request.GET.get("key")
    foodbank = get_object_or_404(Foodbank, pk = key)
    return api_foodbank(request, foodbank.slug)
