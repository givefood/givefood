import json

from django.http import HttpResponseForbidden, JsonResponse
from django.utils.timesince import timesince
from givefood.func import find_foodbanks


def api_foodbanks(request):

    lattlong = request.GET.get("lattlong")
    postcode = request.GET.get("postcode")

    if not lattlong and not postcode:
        return HttpResponseForbidden()

    if postcode and not lattlong:
        pass

    foodbanks = find_foodbanks(lattlong, 10)
    response_list = []

    for foodbank in foodbanks:
        response_list.append({
            "name":foodbank.name,
            "distance_m":int(foodbank.distance_m),
            "distance_mi":round(foodbank.distance_mi,2),
            "url":foodbank.url,
            "phone":foodbank.phone_number,
            "address":foodbank.full_address(),
            "needs":foodbank.latest_need_text(),
            "updated":str(foodbank.latest_need_date()),
            "updated_text":timesince(foodbank.latest_need_date()),
        })

    return JsonResponse(response_list, safe=False)
