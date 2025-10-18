import json

from datetime import datetime, timedelta, date
from collections import OrderedDict
from operator import or_
from functools import reduce

from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.views.decorators.cache import cache_page
from django.db.models import Q, Count, Sum

from givefood.models import CharityYear, Foodbank, FoodbankChange, FoodbankArticle, FoodbankChangeLine, FoodbankDonationPoint, Order, OrderLine
from givefood.func import group_list, get_all_foodbanks, filter_change_text
from givefood.const.cache_times import SECONDS_IN_DAY, SECONDS_IN_HOUR
from django.db.models.functions import TruncMonth, TruncYear


@cache_page(SECONDS_IN_DAY)
def index(request):
    return render(request, "dash/index.html")


@cache_page(SECONDS_IN_DAY)
def weekly_itemcount(request):

    week_needs = OrderedDict()

    start_date = date(2020,1,1)
    needs = FoodbankChange.objects.filter(created__gt = start_date, published=True).order_by("created")

    for need in needs:
        week_number = need.created.isocalendar()[1]
        year = need.created.year
        week_key = "%s-%s" % (year, week_number)
        week_needs[week_key] = week_needs.get(week_key, 0) + need.no_items()

    template_vars = {
        "week_needs":week_needs,
    }
    return render(request, "dash/weekly_itemcount.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def weekly_itemcount_year(request):

    week_needs = OrderedDict()
    week_year_needs = OrderedDict()

    start_date = date(2020,1,1)
    start_year = start_date.year
    current_year = date.today().year
    years = range(start_year, current_year+1)
    weeks = range(1,54)

    needs = FoodbankChange.objects.filter(created__gt = start_date, published=True).order_by("created")

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

@cache_page(SECONDS_IN_DAY)
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
        recent_foodbanks = Foodbank.objects.select_related("latest_need").filter(network = "Trussell", last_need__gt = day_threshold).order_by("-last_need")
    else:
        recent_foodbanks = Foodbank.objects.select_related("latest_need").filter(last_need__gt = day_threshold).order_by("-last_need")

    # Keywords we use in need text that we'll exclude
    invalid_text = ["Nothing", "Unknown", "Facebook"]

    # Loop the foodbanks
    for recent_foodbank in recent_foodbanks:

        # Find need text
        need_text = recent_foodbank.latest_need.change_text

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


@cache_page(SECONDS_IN_DAY)
def most_excess_items(request):

    # Handle allowed day parameters
    default_days = 30
    allowed_days = [7, 30, 60, 90, 120, 365]
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
        excess_text = recent_foodbank.latest_need.excess_change_text

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


@cache_page(SECONDS_IN_DAY)
def item_categories(request):

    categories = FoodbankChangeLine.objects.filter(type = "need").values("category").annotate(count=Count("category")).order_by("-count")
    template_vars = {
        "categories":categories,
    }

    return render(request, "dash/item_categories.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def item_groups(request):

    groups = FoodbankChangeLine.objects.filter(type = "need").values("group").annotate(count=Count("group")).order_by("-count")
    template_vars = {
        "groups":groups,
    }

    return render(request, "dash/item_groups.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def tt_old_data(request):

    recent = Foodbank.objects.filter(network = "Trussell", is_closed = False).order_by("-last_need")[:100]
    old = Foodbank.objects.filter(network = "Trussell", is_closed = False).order_by("last_need")[:100]

    template_vars = {
        "recent":recent,
        "old":old,
    }
    return render(request, "dash/tt_old_data.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def articles(request):

    articles = FoodbankArticle.objects.all().order_by("-published_date")[:200]

    template_vars = {
        "articles":articles,
    }
    return render(request, "dash/articles.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
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
        "Sanitary Towel",
        "Tampon",
        "Toiletries",
        "Toiletry",
        "Bubble Bath",
        "Face Wash",
        "Facewash",
        "Moisturiser",
        "SPF",
        "Lip Balm",
        "Lipbalm",
        "Hand Cream",
        "Handcream",
        "Body Wash",
        "Bodywash",
        "Body Lotion",
        "Baby wash",
        "Babywash",
        "Baby lotion",
        "Baby soap",
        "Baby shampoo",
        "Baby oil",
        "Baby powder",
        "Baby cream",
        "Baby wipes",
        "Skin Care",
        "Make Up",
        "Makeup",
    ]

    london_postcode_file = open("./givefood/data/london_postcodes.txt", "r")
    london_postcode_data = london_postcode_file.read()
    london_postcodes = london_postcode_data.splitlines()

    london_query = reduce(or_, (Q(postcode__startswith=london_postcode) for london_postcode in london_postcodes))
    london_foodbanks = Foodbank.objects.filter(london_query)

    all_needs_query = reduce(or_, (Q(change_text__contains=product) for product in products))
    all_needs = FoodbankChange.objects.filter(all_needs_query).filter(published = True).order_by("-created")[:50]

    all_needs_query = reduce(or_, (Q(change_text__contains=product) for product in products))
    time_since = datetime.today() - timedelta(days=28)
    time_since_needs = FoodbankChange.objects.filter(all_needs_query).filter(published = True).filter(created__gt = time_since).order_by("-created")

    london_needs_query = reduce(or_, (Q(foodbank=london_foodbank) for london_foodbank in london_foodbanks))
    london_needs = FoodbankChange.objects.filter(all_needs_query).filter(london_needs_query).filter(published = True).order_by("-created")[:50]

    for need in all_needs:
        need.filtered_change_text = filter_change_text(need.change_text, products)

    for need in london_needs:
        need.filtered_change_text = filter_change_text(need.change_text, products)
    
    for need in time_since_needs:
        need.filtered_change_text = filter_change_text(need.change_text, products)

    time_since_json = []
    for need in time_since_needs:
        time_since_json.append({
            "foodbank":need.foodbank.name,
            "slug":need.foodbank.slug,
            "lat":need.foodbank.latt(),
            "lng":need.foodbank.long(),
            "change_text":need.filtered_change_text,
        })
    time_since_json = json.dumps(time_since_json)

    template_vars = {
        "time_since_json":time_since_json,
        "all_needs":all_needs,
        "london_needs":london_needs,
        "london_foodbanks":london_foodbanks,
        "london_postcodes":london_postcodes,
        "products":products,
    }
    return render(request, "dash/beautybanks.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def excess(request):
    excesses = FoodbankChange.objects.filter(published = True).order_by("-created")[:200]
    template_vars = {
        "excesses":excesses,
    }
    return render(request, "dash/excess.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def foodbanks_found(request):
    
    foodbanks = get_all_foodbanks()
    created_dates = [foodbank.created for foodbank in foodbanks]
    created_dates.sort()
    created_months = {}

    for created_date in created_dates:
        created_months[created_date.strftime("%Y-%m")] = created_dates.index(created_date) + 1

    template_vars = {
        "created_months":created_months,
    }

    return render(request, "dash/foodbanks_found.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def foodbank_locations_found(request):
    
    foodbanks = get_all_foodbanks()
    created_dates = [foodbank.created for foodbank in foodbanks]
    created_dates.sort()
    created_months = {}

    for created_date in created_dates:
        created_months[created_date.strftime("%Y-%m")] = created_dates.index(created_date) + 1

    template_vars = {
        "created_months":created_months,
    }

    return render(request, "dash/foodbanks_found.html", template_vars)

@cache_page(SECONDS_IN_DAY)
def bean_pasta_index(request):

    months = FoodbankChange.objects.raw("select 1 as id, count(*) as count, to_char(created, 'YYYY-MM') as the_month from givefood_foodbankchange where published = True and (change_text ~* 'beans' or change_text ~* 'pasta') group by the_month order by the_month")

    template_vars = {
        "months":months,
    }

    return render(request, "dash/bean_pasta_index.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def deliveries(request, metric):

    if metric == "count":
        metric_text = "Number of deliveries"
        metric_sql = "count(*)"
    elif metric == "items":
        metric_text = "Items"
        metric_sql = "sum(no_items)"
    elif metric == "weight":
        metric_text = "Weight kg"
        metric_sql = "sum(weight)/1000"
    elif metric == "calories":
        metric_text = "Calories"
        metric_sql = "sum(calories)"

    sql = "select 1 as id, %s as count, to_char(delivery_datetime, 'YYYY-MM') as the_month from givefood_order group by the_month order by the_month" % (metric_sql)

    months = Order.objects.raw(sql)

    template_vars = {
        "sql":sql,
        "metric":metric,
        "metric_text":metric_text,
        "months":months,
    }

    return render(request, "dash/deliveries.html", template_vars)


@cache_page(SECONDS_IN_DAY)
def supermarkets(request):

    supermarkets = FoodbankDonationPoint.objects.filter(company__isnull = False).values("company").annotate(count=Count("company")).order_by("-count")
    supermarket_total = FoodbankDonationPoint.objects.filter(company__isnull = False).count()
    template_vars = {
        "supermarkets":supermarkets,
        "supermarket_total":supermarket_total,
    }

    return render(request, "dash/supermarkets.html", template_vars)


def charity_income_expenditure(request):

    five_years_ago = date.today().year - 5
    years = CharityYear.objects.filter(foodbank__charity_just_foodbank = True, date__year__gte=five_years_ago).values("date__year").annotate(income=Sum("income"), expenditure=Sum("expenditure")).order_by("-date__year")

    template_vars = {
        "years":years,
    }
    return render(request, "dash/charity_income_expenditure.html", template_vars)


def price_per_kg(request):

    months = Order.objects.annotate(month = TruncMonth('delivery_datetime'), year = TruncYear('delivery_datetime')).values('month', 'year').annotate(total_weight = Sum('weight'),total_cost = Sum('cost')/100,price_per_kg = Sum('cost')*1000/Sum('weight')).order_by('month')

    items = Order.objects.aggregate(Sum("no_items"))["no_items__sum"]
    weight = Order.objects.aggregate(Sum("weight"))["weight__sum"]/1000000
    number_foodbanks = Order.objects.values('foodbank_name').distinct().count()

    template_vars = {
        "months": months,
        "items": items,
        "weight": weight,
        "number_foodbanks": number_foodbanks,
    }
    return render(request, "dash/price_per_kg.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def price_per_calorie(request):

    months = Order.objects.filter(
        calories__gt=0
    ).annotate(
        month=TruncMonth('delivery_datetime'),
        year=TruncYear('delivery_datetime')
    ).values(
        'month',
        'year'
    ).annotate(
        total_calories=Sum('calories'),
        total_cost=Sum('cost') / 100,
        price_per_calorie=Sum('cost') * 2000 / Sum('calories')
    ).order_by('month')
    
    items = Order.objects.aggregate(Sum("no_items"))["no_items__sum"]
    calories = Order.objects.aggregate(Sum("calories"))["calories__sum"]
    number_foodbanks = Order.objects.values('foodbank_name').distinct().count()

    template_vars = {
        "months": months,
        "items": items,
        "calories": calories,
        "number_foodbanks": number_foodbanks,
    }
    return render(request, "dash/price_per_calorie.html", template_vars)