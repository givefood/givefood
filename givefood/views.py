from datetime import date
import json
import requests

from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect, render
from django.urls import reverse
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Sum
from django.utils.timesince import timesince
from session_csrf import anonymous_csrf

from givefood.models import Foodbank, FoodbankChangeLine, FoodbankLocation, Order, FoodbankChange
from givefood.forms import FoodbankRegistrationForm
from givefood.func import get_all_constituencies, get_image, item_class_count, get_all_open_foodbanks, get_all_open_locations, get_cred, validate_turnstile
from givefood.func import send_email
from givefood.const.general import PACKAGING_WEIGHT_PC, CHECK_COUNT_PER_DAY, PAGE_SIZE_PER_COUNT, SITE_DOMAIN
from givefood.const.item_classes import TOMATOES, RICE, PUDDINGS, SOUP, FRUIT, MILK, MINCE_PIES
from givefood.const.cache_times import SECONDS_IN_MINUTE, SECONDS_IN_HOUR, SECONDS_IN_WEEK


@cache_page(SECONDS_IN_HOUR)
def index(request):
    logos = [
        {
            "name":"Trussell Trust",
            "slug":"trusselltrust",
            "url":"https://www.trusselltrust.org",
            "format":"svg",
        },
        {
            "name":"The Times",
            "slug":"thetimes",
            "url":"https://www.thetimes.co.uk",
            "format":"png",
        },
        {
            "name":"NHS",
            "slug":"nhs",
            "url":"https://www.nhs.uk",
            "format":"svg",
        },
        {
            "name":"Scottish Government Riaghaltas na h-Alba",
            "slug":"scottishgov",
            "url":"https://www.gov.scot",
            "format":"svg",
        },
        {
            "name":"Consumer Data Research Centre",
            "slug":"cdrc",
            "url":"https://www.cdrc.ac.uk",
            "format":"png",
        },
        {
            "name":"Reach plc",
            "slug":"reach",
            "url":"https://www.reachplc.com",
            "format":"svg",
        },
        {
            "name":"Independent Food Aid Network",
            "slug":"ifan",
            "url":"https://www.foodaidnetwork.org.uk",
            "format":"png",
        }
    ]

    stats = {
        "organisations":Foodbank.objects.count(),
        "locations":Foodbank.objects.count() + Foodbank.objects.exclude(delivery_address = "").count() + FoodbankLocation.objects.count(),
        "items":FoodbankChangeLine.objects.count(),
        "meals":int(Order.objects.aggregate(Sum("calories"))["calories__sum"]/500),
    }
    gmap_key = get_cred("gmap_key")

    template_vars = {
        "gmap_key":gmap_key,
        "logos":logos,
        "stats":stats,
    }
    return render(request, "public/index.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def annual_report_index(request):
    return render(request, "public/ar/index.html")


@cache_page(SECONDS_IN_WEEK)
def annual_report(request, year):
    article_template = "public/ar/%s.html" % (year)
    return render(request, article_template)


@anonymous_csrf
def register_foodbank(request):

    done = request.GET.get("thanks", False)

    if request.POST:
        form = FoodbankRegistrationForm(request.POST)

        turnstile_is_valid = validate_turnstile(request.POST.get("cf-turnstile-response"))

        if form.is_valid() and turnstile_is_valid:
            email_body = render_to_string("public/registration_email.txt",{"form":request.POST.items()})
            send_email(
                to = "mail@givefood.org.uk",
                subject = "New Food Bank Registration - %s" % (request.POST.get("name")),
                body = email_body,
            )
            completed_url = "%s%s" % (reverse("register_foodbank"),"?thanks=1")
            return redirect(completed_url)
    else:
        form = FoodbankRegistrationForm()

    template_vars = {
        "form":form,
        "done":done,
    }
    return render(request, "public/register_foodbank.html", template_vars)


@cache_page(SECONDS_IN_WEEK)
def donate(request):
    return render(request, "public/donate.html")


@cache_page(SECONDS_IN_WEEK)
def donate(request):
    return render(request, "public/about_us.html")


@cache_page(SECONDS_IN_WEEK)
def api(request):
    return render(request, "public/api.html")


@cache_page(SECONDS_IN_WEEK)
def sitemap(request):

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


@cache_page(SECONDS_IN_WEEK)
def sitemap_external(request):

    foodbanks = get_all_open_foodbanks()

    template_vars = {
        "domain":SITE_DOMAIN,
        "foodbanks":foodbanks,
    }
    return render(request, "public/sitemap_external.xml", template_vars, content_type='text/xml')


@cache_page(SECONDS_IN_WEEK)
def privacy(request):
    return render(request, "public/privacy.html")


@cache_page(SECONDS_IN_MINUTE)
def frag(request, frag):

    if frag == "lastupdated":
        timesince_text = timesince(Foodbank.objects.latest("modified").modified)
        if timesince_text == "0 minutes":
            frag_text = "Under a minute ago"
        else:
            frag_text = "%s ago" % (timesince_text)
    return HttpResponse(frag_text)
        

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