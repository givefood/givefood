import json

from django.http import HttpResponseForbidden, JsonResponse
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
            "needs":foodbank.latest_need_text(),
            "updated":str(foodbank.latest_need_date())
        })

    return JsonResponse(response_list, safe=False)
