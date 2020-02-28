import json, urllib

from google.appengine.api import urlfetch

from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.timesince import timesince
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404

from givefood.func import find_foodbanks, get_all_foodbanks
from givefood.models import ApiFoodbankSearch, Foodbank


@cache_page(60*10)
def api_foodbanks(request):

    foodbanks = get_all_foodbanks()
    response_list = []

    for foodbank in foodbanks:
        response_list.append({
            "name":foodbank.name,
            "slug":foodbank.slug,
            "url":foodbank.url,
            "shopping_list_url":foodbank.shopping_list_url,
            "phone":foodbank.phone_number,
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

    return JsonResponse(response_list, safe=False)


@cache_page(60*10)
def api_foodbank_search(request):

    lattlong = request.GET.get("lattlong")
    address = request.GET.get("address")

    if not lattlong and not address:
        return HttpResponseBadRequest()

    if address and not lattlong:
        address_api_url = "https://maps.googleapis.com/maps/api/geocode/json?key=AIzaSyCgc052pX0gMcxOF1PKexrTGTu8qQIIuRk&address=%s" % (urllib.quote(address))
        address_api_result = urlfetch.fetch(address_api_url)
        if address_api_result.status_code == 200:
            address_result_json = json.loads(address_api_result.content)
            lattlong = "%s,%s" % (
                address_result_json["results"][0]["geometry"]["location"]["lat"],
                address_result_json["results"][0]["geometry"]["location"]["lng"]
            )

    foodbanks = find_foodbanks(lattlong, 10)
    response_list = []

    if address:
        query_type = "address"
        query = address
    else:
        query_type = "lattlong"
        query = lattlong

    api_hit = ApiFoodbankSearch(
        query_type = query_type,
        query = query,
        nearest_foodbank = foodbanks[0].distance_m,
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
        })

    foodbank_response = {
        "name":foodbank.name,
        "slug":foodbank.slug,
        "url":foodbank.url,
        "shopping_list_url":foodbank.shopping_list_url,
        "phone":foodbank.phone_number,
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
        "closed":foodbank.is_closed,
        "latt_long":foodbank.latt_long,
        "network":foodbank.network,
        "needs":foodbank.latest_need_text(),
        "number_needs":foodbank.latest_need_text().count('\n')+1,
        "need_found":foodbank.last_need,
        "locations":locations_list,
        "updated":str(foodbank.latest_need_date()),
        "updated_text":timesince(foodbank.latest_need_date()),
    }

    return JsonResponse(foodbank_response, safe=False)
