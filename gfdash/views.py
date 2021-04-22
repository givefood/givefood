import logging

from datetime import datetime, timedelta

from django.shortcuts import render
from django.http import HttpResponseForbidden

from givefood.models import Foodbank
from givefood.func import group_list


def dash_index(request):
    return render(request, "dash_index.html")


def dash_tt_old_data(request):

    recent = Foodbank.objects.filter(network = "Trussell Trust").order_by("-last_need")[:100]
    old = Foodbank.objects.filter(network = "Trussell Trust").order_by("last_need")[:100]

    template_vars = {
        "recent":recent,
        "old":old,
    }
    return render(request, "dash_tt_old_data.html", template_vars)


def dash_tt_most_requested_items(request):

    # Handle allowed day parameters
    default_days = 30
    allowed_days = [30, 60, 90, 120, 365]
    days = int(request.GET.get("days", default_days))
    if days not in allowed_days:
        return HttpResponseForbidden()
    day_threshold = datetime.now() - timedelta(days=days)

    # Empty vars we'll use
    items = []
    number_foodbanks = 0
    number_items = 0

    # Find the food banks that are in the Trussell Trust and have updated their needs within the day threshold
    recent_foodbanks = Foodbank.objects.filter(network = "Trussell Trust", last_need__gt = day_threshold).order_by("-last_need")

    # Keywords we use in need text that we'll exclude
    invalid_text = ["Nothing", "Unknown"]

    # Loop the foodbanks
    for recent_foodbank in recent_foodbanks:

        # Find need text
        need_text = recent_foodbank.latest_need().change_text

        # Don't count the need if it's a keyword
        if not need_text in invalid_text:

            # Make list of items in this need
            need_items = need_text.splitlines()

            # Put the items of the last request from the food bank into the list
            items.extend(need_items)

        # Increment the food bank count
        number_foodbanks += 1

    # Group the items by the item text
    items_freq = group_list(items)
    number_items = len(items_freq)

    # Sort the items by their frequency count
    items_sorted = sorted(items_freq, reverse=True, key=lambda x: x[1])

    template_vars = {
        "items_sorted": items_sorted,
        "allowed_days": allowed_days,
        "days": days,
        "number_foodbanks": number_foodbanks,
        "number_items": number_items,
    }

    return render(request, "dash_tt_most_requested_items.html", template_vars)

