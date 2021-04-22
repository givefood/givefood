import logging
from django.shortcuts import render
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

    # Empty items list we'll use
    items = []

    # Find most recent 250 Trussell Trust food banks by the date their last requested
    recent_foodbanks = Foodbank.objects.filter(network = "Trussell Trust").order_by("-last_need")[:250]

    # Loop the foodbanks
    for recent_foodbank in recent_foodbanks:

        # Put the items of the last request from the food bank into the list
        items.extend(recent_foodbank.latest_need().change_text.splitlines())

        # Keep tab on the last food bank we've found to allow us to show when the oldest data is from
        oldest_foodbank = recent_foodbank

    # Group the items by the item text
    items_freq = group_list(items)

    # Sort the items by their frequency count
    items_sorted = sorted(items_freq, reverse=True, key=lambda x: x[1])

    template_vars = {
        "items_sorted":items_sorted,
        "oldest_foodbank":oldest_foodbank,
    }

    return render(request, "dash_tt_most_requested_items.html", template_vars)

