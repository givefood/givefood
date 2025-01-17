import unicodecsv as csv

from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.utils.timesince import timesince
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404
from django.urls import reverse

from givefood.func import find_foodbanks, get_all_foodbanks, geocode
from givefood.models import Foodbank, FoodbankChange
from givefood.const.general import API_DOMAIN
from givefood.const.cache_times import SECONDS_IN_HOUR, SECONDS_IN_DAY, SECONDS_IN_MONTH


@cache_page(SECONDS_IN_MONTH)
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
        return HttpResponseBadRequest()

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
            "parliamentary_constituency":foodbank.parliamentary_constituency_name,
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
            "self":"%s%s" % (API_DOMAIN, reverse("api_foodbank", kwargs={"slug":foodbank.slug})),
        })

    if format == "json":
        return JsonResponse(response_list, safe=False)

    if format == "csv":
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="foodbanks.csv"'
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
            "network",
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
                foodbank["network"],
            ])
        writer.writerows(writer_output)
        return response



@cache_page(SECONDS_IN_DAY)
def api_foodbank_search(request):

    latt_long = request.GET.get("lattlong")
    address = request.GET.get("address")

    if not latt_long and not address:
        return HttpResponseBadRequest()

    if address and not latt_long:
        latt_long = geocode(address)

    foodbanks = find_foodbanks(latt_long, 10)
    response_list = []

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
            "parliamentary_constituency":foodbank.parliamentary_constituency_name,
            "mp":foodbank.mp,
            "mp_party":foodbank.mp_party,
            "ward":foodbank.ward,
            "district":foodbank.district,
            "charity_number":foodbank.charity_number,
            "charity_register_url":foodbank.charity_register_url(),
            "needs":foodbank.latest_need.change_text,
            "number_needs":foodbank.latest_need.no_items(),
            "need_id":foodbank.latest_need.need_id,
            "updated":str(foodbank.latest_need.created),
            "updated_text":timesince(foodbank.latest_need.created),
            "latt_long":foodbank.latt_long,
            "self":"%s%s" % (API_DOMAIN, reverse("api_foodbank", kwargs={"slug":foodbank.slug})),
        })

    return JsonResponse(response_list, safe=False)


@cache_page(SECONDS_IN_MONTH)
def api_foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank.objects.select_related("latest_need"), slug = slug)
    locations = foodbank.locations()

    locations_list = []
    for location in locations:
        locations_list.append({
            "name":location.name,
            "address":location.address,
            "postcode":location.postcode,
            "latt_long":location.latt_long,
            "phone":location.phone_number,
            "parliamentary_constituency":location.parliamentary_constituency_name,
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
        "parliamentary_constituency":foodbank.parliamentary_constituency_name,
        "mp":foodbank.mp,
        "mp_party":foodbank.mp_party,
        "ward":foodbank.ward,
        "district":foodbank.district,
        "charity_number":foodbank.charity_number,
        "charity_register_url":foodbank.charity_register_url(),
        "closed":foodbank.is_closed,
        "latt_long":foodbank.latt_long,
        "network":foodbank.network,
        "needs":foodbank.latest_need.change_text,
        "number_needs":foodbank.latest_need.no_items(),
        "need_found":foodbank.last_need,
        "need_id":foodbank.latest_need.need_id,
        "need_self":"%s%s" % (API_DOMAIN, reverse("api_need", kwargs={"id":foodbank.latest_need.need_id})),
        "locations":locations_list,
        "updated":str(foodbank.latest_need_date()),
        "updated_text":timesince(foodbank.latest_need.created),
        "self":"%s%s" % (API_DOMAIN, reverse("api_foodbank", kwargs={"slug":foodbank.slug})),
    }

    return JsonResponse(foodbank_response, safe=False)

@cache_page(SECONDS_IN_HOUR)
def api_needs(request):

    allowed_limits = [100,1000]
    default_limit = 100
    limit = request.GET.get("limit", default_limit)
    limit = int(limit)
    if limit not in allowed_limits:
        return HttpResponseBadRequest()

    needs = FoodbankChange.objects.filter(published = True).order_by("-created")[:limit]

    response_list = []

    for need in needs:
        response_list.append({
            "id":need.need_id,
            "created":need.created,
            "foodbank_name":need.foodbank_name,
            "foodbank_slug":need.foodbank_name_slug(),
            "foodbank_self":"%s%s" % (API_DOMAIN, reverse("api_foodbank", kwargs={"slug":need.foodbank_name_slug()})),
            "needs":need.change_text,
            "url":need.uri,
            "self":"%s%s" % (API_DOMAIN, reverse("api_need", kwargs={"id":need.need_id})),
        })

    return JsonResponse(response_list, safe=False)


@cache_page(SECONDS_IN_DAY)
def api_need(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)

    need_response = {
        "id":need.need_id,
        "created":need.created,
        "foodbank_name":need.foodbank_name,
        "foodbank_slug":need.foodbank_name_slug(),
        "foodbank_self":"%s%s" % (API_DOMAIN, reverse("api_foodbank", kwargs={"slug":need.foodbank_name_slug()})),
        "needs":need.change_text,
        "url":need.uri,
        "self":"%s%s" % (API_DOMAIN, reverse("api_need", kwargs={"id":need.need_id})),
    }

    return JsonResponse(need_response, safe=False)
