import logging

from datetime import datetime, timedelta, date
from collections import OrderedDict

from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.views.decorators.cache import cache_page

from givefood.models import Foodbank, FoodbankChange, FoodbankArticle
from givefood.func import group_list

@cache_page(60*10)
def dash_index(request):
    return render(request, "dash_index.html")


@cache_page(60*10)
def dash_weekly_itemcount(request):

    week_needs = OrderedDict()

    start_date = date(2020,1,1)
    needs = FoodbankChange.objects.filter(created__gt = start_date).order_by("created")

    for need in needs:
        week_number = need.created.isocalendar()[1]
        year = need.created.year
        week_key = "%s-%s" % (year, week_number)
        week_needs[week_key] = week_needs.get(week_key, 0) + need.no_items()

    template_vars = {
        "week_needs":week_needs,
    }
    return render(request, "dash_weekly_itemcount.html", template_vars)


@cache_page(60*10)
def dash_most_requested_items(request):

    # Handle allowed day parameters
    default_days = 30
    allowed_days = [7, 30, 60, 90, 120, 365]
    days = int(request.GET.get("days", default_days))
    if days not in allowed_days:
        return HttpResponseForbidden()
    day_threshold = datetime.now() - timedelta(days=days)

    trusselltrust = ("trusselltrust" in request.path)

    # Empty vars we'll use
    items = []
    number_foodbanks = 0
    number_items = 0

    # Find the food banks that have updated their needs within the day threshold
    if trusselltrust:
        recent_foodbanks = Foodbank.objects.filter(network = "Trussell Trust", last_need__gt = day_threshold).order_by("-last_need")
    else:
        recent_foodbanks = Foodbank.objects.filter(last_need__gt = day_threshold).order_by("-last_need")

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
        "trusselltrust":trusselltrust,
    }

    return render(request, "dash_most_requested_items.html", template_vars)


@cache_page(60*10)
def dash_tt_old_data(request):

    recent = Foodbank.objects.filter(network = "Trussell Trust").order_by("-last_need")[:100]
    old = Foodbank.objects.filter(network = "Trussell Trust").order_by("last_need")[:100]

    template_vars = {
        "recent":recent,
        "old":old,
    }
    return render(request, "dash_tt_old_data.html", template_vars)


@cache_page(60*10)
def dash_articles(request):

    articles = FoodbankArticle.objects.all().order_by("-published_date")[:200]

    template_vars = {
        "articles":articles,
    }
    return render(request, "dash_articles.html", template_vars)