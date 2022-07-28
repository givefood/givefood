import logging

from datetime import datetime, timedelta, date
from collections import OrderedDict

from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.views.decorators.cache import cache_page

from givefood.models import Foodbank, FoodbankChange, FoodbankArticle
from givefood.func import group_list

@cache_page(60*60*2)
def index(request):
    return render(request, "dash/index.html")


@cache_page(60*60*4)
def weekly_itemcount(request):

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
    return render(request, "dash/weekly_itemcount.html", template_vars)


@cache_page(60*60*4)
def weekly_itemcount_year(request):

    week_needs = OrderedDict()
    week_year_needs = OrderedDict()

    start_date = date(2020,1,1)
    start_year = start_date.year
    current_year = date.today().year
    years = range(start_year, current_year+1)
    weeks = range(1,54)

    needs = FoodbankChange.objects.filter(created__gt = start_date).order_by("created")

    for need in needs:
        week_number = need.created.isocalendar()[1]
        year = need.created.year
        week_key = "%s-%s" % (year, week_number)
        week_needs[week_key] = week_needs.get(week_key, 0) + need.no_items()

    for week in weeks:
        years_in_week = {}
        for year in years:
            week_key = "%s-%s" % (year, week)
            years_in_week[year] = week_needs.get(week_key, 0)
        week_year_needs[week] = years_in_week
        

    template_vars = {
        "weeks":weeks,
        "years":years,
        "week_year_needs":week_year_needs,
        "week_needs":week_needs,
    }
    return render(request, "dash/weekly_itemcount_year.html", template_vars)

@cache_page(60*60*4)
def most_requested_items(request):

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
    invalid_text = ["Nothing", "Unknown", "Facebook"]

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

    return render(request, "dash/most_requested_items.html", template_vars)


@cache_page(60*60*4)
def most_excess_items(request):

    # Handle allowed day parameters
    default_days = 30
    allowed_days = [7, 30, 60, 90,]
    days = int(request.GET.get("days", default_days))
    if days not in allowed_days:
        return HttpResponseForbidden()
    day_threshold = datetime.now() - timedelta(days=days)

    # Empty vars we'll use
    items = []
    number_foodbanks = 0
    number_items = 0

    recent_foodbanks = Foodbank.objects.filter(last_need__gt = day_threshold).order_by("-last_need")

    # Loop the foodbanks
    for recent_foodbank in recent_foodbanks:

        # Find need text
        excess_text = recent_foodbank.latest_need().excess_change_text

        # Make list of items in this need
        if excess_text:
            excess_items = excess_text.splitlines()

            # Put the items of the last request from the food bank into the list
            items.extend(excess_items)

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

    return render(request, "dash/most_excess_items.html", template_vars)

@cache_page(60*60*2)
def tt_old_data(request):

    recent = Foodbank.objects.filter(network = "Trussell Trust").order_by("-last_need")[:100]
    old = Foodbank.objects.filter(network = "Trussell Trust").order_by("last_need")[:100]

    template_vars = {
        "recent":recent,
        "old":old,
    }
    return render(request, "dash/tt_old_data.html", template_vars)


@cache_page(60*60*1)
def articles(request):

    articles = FoodbankArticle.objects.all().order_by("-published_date")[:200]

    template_vars = {
        "articles":articles,
    }
    return render(request, "dash/articles.html", template_vars)


@cache_page(60*60*1)
def beautybanks(request):

    products = [
        "Soap",
        "Shampoo",
        "Shower Gel",
        "Toothpaste",
        "Toothbrush",
        "Tooth brush",
        "Deodorant",
        "Razor",
        "Shaving Gel",
        "Shaving Foam",
        "Conditioner",
        "Sanitary Pad",
        "Sanitary Towel"
        "Tampon",
        "Toiletries",
        "Toiletry",
    ]

    needs = FoodbankChange.objects.filter(published = True).order_by("-created")[:200]
    bbneeds = []

    for need in needs:
        if any(product in need.change_text for product in products):
            bbneeds.append(need)

    template_vars = {
        "bbneeds":bbneeds,
    }
    return render(request, "dash/beautybanks.html", template_vars)


@cache_page(60*60*1)
def excess(request):
    excesses = FoodbankChange.objects.filter(published = True).order_by("-created")[:200]
    template_vars = {
        "excesses":excesses,
    }
    return render(request, "dash/excess.html", template_vars)