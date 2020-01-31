from datetime import date
import operator
from collections import OrderedDict
import json

from django.shortcuts import render_to_response, get_object_or_404
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from givefood.models import Foodbank, Order, FoodbankChange
from givefood.func import get_image, item_class_count, clean_foodbank_need_text
from givefood.const.general import PACKAGING_WEIGHT_PC, CHECK_COUNT_PER_DAY, PAGE_SIZE_PER_COUNT
from givefood.const.item_classes import TOMATOES, RICE, PUDDINGS, SOUP, FRUIT, MILK, MINCE_PIES


@cache_page(60*30)
def public_index(request):

    total_weight = 0
    total_calories = 0
    total_items = 0

    orders = Order.objects.all()
    foodbanks = set()

    for order in orders:
        total_weight = total_weight + order.weight
        total_calories = total_calories + order.calories
        total_items = total_items + order.no_items
        foodbanks.add(order.foodbank_name)

    total_weight = float(total_weight) / 1000000
    total_weight = total_weight * PACKAGING_WEIGHT_PC
    total_calories = float(total_calories) / 1000000

    no_foodbanks = len(foodbanks)

    template_vars = {
        "no_foodbanks":no_foodbanks,
        "total_weight":total_weight,
        "total_calories":total_calories,
        "total_items":total_items,
    }
    return render_to_response("public/index.html", template_vars)


def public_article(request, slug):

    article_template = "public/articles/%s.html" % (slug)
    return render_to_response(article_template)


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


@cache_page(60*2)
def public_what_food_banks_need(request):

    version = "472694a0"

    foodbanks = Foodbank.objects.all()
    no_foodbanks = len(foodbanks)

    template_vars = {
        "no_foodbanks":no_foodbanks,
        "version":version,
    }
    return render_to_response("public/wfbn.html", template_vars)


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
