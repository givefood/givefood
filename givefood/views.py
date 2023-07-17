from datetime import date
import json
import requests

from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect, render
from django.urls import reverse
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden
from session_csrf import anonymous_csrf

from givefood.models import Foodbank, Order, FoodbankChange
from givefood.forms import FoodbankRegistrationForm
from givefood.func import get_all_constituencies, get_image, item_class_count, get_all_foodbanks, get_all_open_foodbanks, get_all_locations, get_all_open_locations, get_cred
from givefood.func import send_email
from givefood.const.general import PACKAGING_WEIGHT_PC, CHECK_COUNT_PER_DAY, PAGE_SIZE_PER_COUNT, SITE_DOMAIN
from givefood.const.item_classes import TOMATOES, RICE, PUDDINGS, SOUP, FRUIT, MILK, MINCE_PIES


@cache_page(60*60*12)
def public_index(request):
    gmap_key = get_cred("gmap_key")
    template_vars = {
        "gmap_key":gmap_key,
    }
    return render(request, "public/index.html", template_vars)


def public_about_us(request):
    return render(request, "public/about_us.html")


@anonymous_csrf
def public_reg_foodbank(request):

    done = request.GET.get("thanks", False)

    if request.POST:
        form = FoodbankRegistrationForm(request.POST)

        # Validate turnstile
        turnstile_secret = get_cred("turnstile_secret")
        turnstile_response = request.POST.get("cf-turnstile-response")
        turnstile_fields = {
            "secret":turnstile_secret,
            "response":turnstile_response,
        }

        turnstile_result = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", turnstile_fields)
        turnstile_is_valid = turnstile_result.json()["success"]

        if form.is_valid() and turnstile_is_valid:
            email_body = render_to_string("public/registration_email.txt",{"form":request.POST.items()})
            send_email(
                to = "mail@givefood.org.uk",
                subject = "New Food Bank Registration - %s" % (request.POST.get("name")),
                body = email_body,
            )
            return redirect(reverse('public_reg_foodbank') + '?thanks=yes')
    else:
        form = FoodbankRegistrationForm()

    template_vars = {
        "form":form,
        "done":done,
    }
    return render(request, "public/register_foodbank.html", template_vars)


@cache_page(60*120)
def public_api(request):
    return render(request, "public/api.html")


@cache_page(60*60*12)
def public_annual_report(request, year):
    article_template = "public/ar/%s.html" % (year)
    return render(request, article_template)


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
    return render(request, "public/annual_report.html", template_vars)


@cache_page(60*60*12)
def public_sitemap(request):

    foodbanks = get_all_open_foodbanks()
    constituencies = get_all_constituencies()
    locations = get_all_open_locations()

    template_vars = {
        "domain":SITE_DOMAIN,
        "foodbanks":foodbanks,
        "constituencies":constituencies,
        "locations":locations,
    }
    return render(request, "public/sitemap.xml", template_vars, content_type='text/xml')


@cache_page(60*60*12)
def public_sitemap_external(request):

    foodbanks = get_all_open_foodbanks()

    template_vars = {
        "domain":SITE_DOMAIN,
        "foodbanks":foodbanks,
    }
    return render(request, "public/sitemap_external.xml", template_vars, content_type='text/xml')


@cache_page(60*60*12)
def public_privacy(request):
    return render(request, "public/privacy.html")


@cache_page(60*60*12)
def public_product_image(request):

    delivery_provider = request.GET.get("delivery_provider")
    product_name = request.GET.get("product_name")

    url = get_image(delivery_provider,product_name)

    return redirect(url)


@csrf_exempt
def distill_webhook(request):

    distill_key = get_cred("distill_key")
    given_key = request.GET.get("key", None)

    if distill_key != given_key:
        return HttpResponseForbidden()

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
        change_text_original = change_details.get("text"),
        foodbank = foodbank,
    )
    new_foodbank_change.save()

    return HttpResponse("OK")


def proxy(request, item):

    if item == "trusselltrust":
        url = "https://www.trusselltrust.org/get-help/find-a-foodbank/foodbank-search/?foodbank_s=all&callback=REMOVEME"
    if item == "ifan":
        url = "https://www.google.com/maps/d/u/0/kml?mid=15mnlXFpd8-x0j4O6Ck6U90chPn4bkbWz&forcekml=1"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
    }

    request = requests.get(url, headers=headers)
    if request.status_code == 200:

        content = request.text

        if item == "trusselltrust":
            content = content.replace("REMOVEME(","")
            content = content.replace(");","")
            content = json.loads(content)
            content = json.dumps(content, indent=4)

        return HttpResponse(content)