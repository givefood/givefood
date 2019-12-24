import json

from django.http import HttpResponse, HttpResponseForbidden
from givefood.func import find_foodbanks


def api_foodbanks(request):

    lattlong = request.GET.get("lattlong")

    if not lattlong:
        return HttpResponseForbidden()

    foodbanks = find_foodbanks(lattlong, 10)
    response_list = []

    for foodbank in foodbanks:
        response_list.append({
            "name":foodbank.name,
            "distance":int(foodbank.distance),
        })

    response_json = json.dumps(response_list)

    return HttpResponse(response_json)
