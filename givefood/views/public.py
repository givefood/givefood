from datetime import date
import operator
from collections import OrderedDict
import json

from google.appengine.api import memcache
from google.appengine.api import urlfetch

from django.shortcuts import render_to_response, get_object_or_404
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from givefood.models import Foodbank, Order, FoodbankChange, FoodbankLocation
from givefood.func import get_image, item_class_count, clean_foodbank_need_text, get_all_foodbanks, get_all_locations
from givefood.const.general import PACKAGING_WEIGHT_PC, CHECK_COUNT_PER_DAY, PAGE_SIZE_PER_COUNT
from givefood.const.general import FB_MC_KEY, LOC_MC_KEY
from givefood.const.item_classes import TOMATOES, RICE, PUDDINGS, SOUP, FRUIT, MILK, MINCE_PIES


@cache_page(60*20)
def public_index(request):

    total_weight = 0
    total_calories = 0
    total_items = 0

    orders = Order.objects.all()
    active_foodbanks = set()
    foodbanks = get_all_foodbanks()
    locations = get_all_locations()

    TOTAL_GLOVE_WEIGHT = 2.715

    for order in orders:
        total_weight = total_weight + order.weight
        total_calories = total_calories + order.calories
        total_items = total_items + order.no_items
        active_foodbanks.add(order.foodbank_name)

    total_weight = float(total_weight) / 1000000
    total_weight = (total_weight * PACKAGING_WEIGHT_PC) + TOTAL_GLOVE_WEIGHT
    total_calories = float(total_calories) / 1000000

    no_active_foodbanks = len(active_foodbanks)
    total_locations = len(locations) + len(foodbanks)

    template_vars = {
        "no_active_foodbanks":no_active_foodbanks,
        "total_locations":total_locations,
        "total_weight":total_weight,
        "total_calories":total_calories,
        "total_items":total_items,
    }
    return render_to_response("public/index.html", template_vars)


def public_article(request, slug):

    article_template = "public/articles/%s.html" % (slug)
    return render_to_response(article_template)


@cache_page(60*10)
def public_api(request):

    return render_to_response("public/api.html")


@cache_page(60*10)
def public_annual_report(request, year):
    article_template = "public/ar/%s.html" % (year)
    return render_to_response(article_template)


def public_gen_annual_report(request, year):

    year = int(year)
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    total_weight = float(0)
    total_calories = 0
    total_items = 0
    items = {}

    country_weights = {
        "England":0,
        "Scotland":0,
        "Northern Ireland":0,
        "Wales":0,
    }

    check_count = CHECK_COUNT_PER_DAY.get(year) * 365
    check_count_bytes = check_count * PAGE_SIZE_PER_COUNT

    foodbanks = []

    orders = Order.objects.filter(delivery_date__gte = year_start, delivery_date__lte = year_end)

    for order in orders:

        if order.foodbank not in foodbanks:
            foodbanks.append(order.foodbank)

        total_weight = total_weight + order.weight
        total_calories = total_calories + order.calories
        total_items = total_items + order.no_items

        for line in order.lines():
            if line.name in items:
                items[line.name] = items.get(line.name) + line.quantity
            else:
                items[line.name] = line.quantity

        country_weights[order.foodbank.country] = country_weights[order.foodbank.country] + order.weight

    total_weight = total_weight / 1000
    total_weight = total_weight * PACKAGING_WEIGHT_PC

    tinned_tom = item_class_count(items, TOMATOES)
    rice = item_class_count(items, RICE)
    rice = float(rice) / 1000
    tinned_pud = item_class_count(items, PUDDINGS)
    soup = item_class_count(items, SOUP)
    fruit = item_class_count(items, FRUIT)
    milk = item_class_count(items, MILK)
    mince_pies = item_class_count(items, MINCE_PIES) * 6

    calorie_days = total_calories / 2000
    calorie_meals = calorie_days / 3
    calorie_years = float(calorie_days / 365)

    no_foodbanks = len(foodbanks)

    template_vars = {
        "year":year,
        "total_weight":int(total_weight),
        "total_calories":total_calories,
        "total_items":total_items,
        "calorie_days":calorie_days,
        "calorie_meals":calorie_meals,
        "calorie_years":calorie_years,
        "tinned_tom":tinned_tom,
        "rice":rice,
        "tinned_pud":tinned_pud,
        "soup":soup,
        "fruit":fruit,
        "milk":milk,
        "mince_pies":mince_pies,
        "foodbanks":foodbanks,
        "no_foodbanks":no_foodbanks,
        "country_weights":country_weights,
        "check_count":check_count,
        "check_count_bytes":check_count_bytes,
    }
    return render_to_response("public/annual_report.html", template_vars)


@cache_page(60*10)
def public_sitemap(request):

    foodbanks = get_all_foodbanks()
    template_vars = {
        "foodbanks":foodbanks,
    }
    return render_to_response("public/sitemap.xml", template_vars, content_type='text/xml')


@cache_page(60*10)
def public_what_food_banks_need(request):

    version = "222f3b10"
    headless = request.GET.get("headless", False)
    where_from = request.GET.get("from", False)
    address = request.GET.get("address", "")
    lattlong = request.GET.get("lattlong", "")
    foodbanks = get_all_foodbanks()

    template_vars = {
        "version":version,
        "headless":headless,
        "where_from":where_from,
        "address":address,
        "lattlong":lattlong,
        "foodbanks":foodbanks,
    }
    return render_to_response("public/wfbn.html", template_vars)


def public_what_food_banks_need_click(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    utm_querystring = "?utm_source=givefood_org_uk&utm_medium=search&utm_campaign=needs"
    redirect_url = "%s%s" % (
        foodbank.shopping_list_url,
        utm_querystring,
    )
    return redirect(redirect_url)


@cache_page(60*2)
def public_wfbn_foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    map_url = "https://maps.googleapis.com/maps/api/staticmap?center=%s&size=350x700&scale=2&maptype=roadmap&format=png&key=AIzaSyAyeRIfEOZenxIew6fSIQjl0AF0q1qIXoQ&markers=%s&markers=size:small|" % (foodbank.latt_long,foodbank.latt_long)
    for location in foodbank.locations():
        map_url += "|%s" % (location.latt_long)

    template_vars = {
        "foodbank":foodbank,
        "map_url":map_url,
    }

    return render_to_response("public/wfbn_foodbank.html", template_vars)


def public_wfbn_foodbank_map(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    result = urlfetch.fetch("https://maps.googleapis.com/maps/api/staticmap?center=%s&zoom=15&size=300x300&maptype=roadmap&format=png&visual_refresh=true&key=AIzaSyAyeRIfEOZenxIew6fSIQjl0AF0q1qIXoQ" % (foodbank.latt_long))
    return HttpResponse(result.content, content_type='image/png')


@cache_page(60*60)
def public_product_image(request):

    delivery_provider = request.GET.get("delivery_provider")
    product_name = request.GET.get("product_name")

    url = get_image(delivery_provider,product_name)

    return redirect(url)


@csrf_exempt
def distill_webhook(request):

    post_text = request.body
    change_details = json.loads(post_text)

    try:
        foodbank = Foodbank.objects.get(shopping_list_url=change_details.get("uri"))
    except Foodbank.DoesNotExist:
        foodbank = None

    new_foodbank_change = FoodbankChange(
        distill_id = change_details.get("id"),
        uri = change_details.get("uri"),
        name = change_details.get("name"),
        change_text = change_details.get("text"),
        foodbank = foodbank,
    )
    new_foodbank_change.save()

    return HttpResponse("OK")


def precacher(request):

    all_locations = FoodbankLocation.objects.all()
    memcache.add(LOC_MC_KEY, all_locations, 3600)

    all_foodbanks = Foodbank.objects.all()
    memcache.add(FB_MC_KEY, all_foodbanks, 3600)

    return HttpResponse("OK")
