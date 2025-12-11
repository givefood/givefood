from collections import OrderedDict
import csv
import json
import logging
from random import randrange
import re
import requests
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.utils.encoding import smart_str
from django.utils import timezone
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Sum, Q, Count

from givefood.const.general import BOT_USER_AGENT, PACKAGING_WEIGHT_PC
from givefood.func import find_locations, foodbank_article_crawl, gemini, get_all_foodbanks, get_all_locations, htmlbodytext, post_to_subscriber, send_email, get_cred, distance_meters, send_firebase_notification
from givefood.models import CrawlItem, Foodbank, FoodbankArticle, FoodbankChangeTranslation, FoodbankDonationPoint, FoodbankGroup, FoodbankHit, Order, OrderGroup, OrderItem, FoodbankChange, FoodbankLocation, ParliamentaryConstituency, GfCredential, FoodbankSubscriber, FoodbankGroup, Place, FoodbankChangeLine, FoodbankDiscrepancy, CrawlSet, SlugRedirect
from givefood.forms import FoodbankDonationPointForm, FoodbankForm, OrderForm, NeedForm, FoodbankPoliticsForm, FoodbankLocationForm, FoodbankLocationAreaForm, FoodbankLocationPoliticsForm, OrderGroupForm, ParliamentaryConstituencyForm, OrderItemForm, GfCredentialForm, FoodbankGroupForm, NeedLineForm, FoodbankUrlsForm, SlugRedirectForm


def index(request):

    # Needs
    unpublished_needs = FoodbankChange.objects.filter(published = False, nonpertinent = False).order_by("-created")
    published_needs = FoodbankChange.objects.filter(published = True).order_by("-created")[:20]

    # Discrepancies
    discrepancies = FoodbankDiscrepancy.objects.filter(status = 'New').order_by("-created")[:20]

    # Stats
    yesterday = datetime.now() - timedelta(days=1)
    week_ago = datetime.now() - timedelta(days=7)
    
    # Get latest need crawlset
    try:
        latest_need_crawlset = CrawlSet.objects.filter(crawl_type="need").order_by("-start")[:1][0]
    except IndexError:
        latest_need_crawlset = None
    
    # Get oldest edit and calculate days since
    oldest_edit = Foodbank.objects.all().exclude(is_closed = True).order_by("edited")[:1][0]
    oldest_edit_days = (timezone.now() - oldest_edit.edited).days
    
    stats = {
        "oldest_edit":oldest_edit,
        "oldest_edit_days":oldest_edit_days,
        "latest_edit":Foodbank.objects.all().exclude(is_closed = True).order_by("-edited")[:1][0],
        "sub_count_24h":FoodbankSubscriber.objects.filter(created__gte=yesterday).count(),
        "sub_count_7d":FoodbankSubscriber.objects.filter(created__gte=week_ago).count(),
        "need_count_24h":FoodbankChangeLine.objects.filter(created__gte=yesterday).count(),
        "need_check_24h":CrawlItem.objects.filter(crawl_set__crawl_type="need", finish__gte=yesterday).count(),
        "oldest_need_check":Foodbank.objects.exclude(is_closed = True).exclude(shopping_list_url__contains = "facebook.com").order_by("last_need_check")[:1][0],
        "latest_need_check":Foodbank.objects.all().exclude(is_closed = True).exclude(last_need_check__isnull=True).order_by("-last_need_check")[:1][0],
        "latest_need_crawlset":latest_need_crawlset,
        "article_check_24h":CrawlItem.objects.filter(crawl_set__crawl_type="article", finish__gte=yesterday).count(),
        "charity_check_24h":CrawlItem.objects.filter(crawl_set__crawl_type="charity", finish__gte=yesterday).count(),
    }

    # Articles
    articles = FoodbankArticle.objects.all().order_by("-published_date")[:20]

    template_vars = {
        "unpublished_needs":unpublished_needs,
        "published_needs":published_needs,
        "discrepancies":discrepancies,
        "stats":stats,
        "articles":articles,
        "section":"home",
    }
    return render(request, "admin/index.html", template_vars)


def search_results(request):

    query = request.GET.get("q")
    if query:
        query = query.strip()

    foodbanks = Foodbank.objects.filter(Q(slug__icontains=query) | Q(name__icontains=query) | Q(address__icontains=query) | Q(postcode__icontains=query) | Q(url__icontains=query) | Q(charity_name__icontains=query))[:100]
    locations = FoodbankLocation.objects.filter(Q(slug__icontains=query) | Q(name__icontains=query) | Q(address__icontains=query) | Q(postcode__icontains=query))[:100]
    donationpoints = FoodbankDonationPoint.objects.filter(Q(name__icontains=query) | Q(address__icontains=query) | Q(postcode__icontains=query))[:100]
    constituencies = ParliamentaryConstituency.objects.filter(Q(name__icontains=query) | Q(mp__icontains=query))[:100]
    needs = FoodbankChange.objects.filter(Q(change_text__icontains=query) | Q(excess_change_text__icontains=query)).order_by("-created")[:100]
    
    template_vars = {
        "query":query,
        "foodbanks":foodbanks,
        "locations":locations,
        "donationpoints":donationpoints,
        "constituencies":constituencies,
        "needs":needs,
        "section":"search",
    }
    return render(request, "admin/search.html", template_vars)


def foodbanks(request):

    sort_options = [
        "name",
        "-name",
        "last_order",
        "-last_order",
        "last_need",
        "-last_need",
        "created",
        "-created",
        "modified",
        "-modified",
        "edited",
        "-edited",
        "no_locations",
        "-no_locations",
        "no_donation_points",
        "-no_donation_points",
        "last_need_check",
        "-last_need_check",
        "hits_last_28_days",
        "-hits_last_28_days",
    ]
    sort = request.GET.get("sort", "edited")
    if sort not in sort_options:
        return HttpResponseForbidden()
    
    display_sort_options = {}
    for sort_option in sort_options:
        # Handle descending sort
        if sort_option.startswith("-"):
            label = sort_option[1:].replace("_", " ").title()  # Strip dash prefix, then format
            label = f"{label} (Desc)"
        else:
            label = sort_option.replace("_", " ").title()
        display_sort_options[sort_option] = label

    # Annotate foodbanks with hits from last 28 days
    # Note: Annotation is always included because the template displays the hits column
    cutoff_date = date.today() - timedelta(days=28)
    foodbanks = Foodbank.objects.all().exclude(is_closed = True).annotate(
        hits_last_28_days=Sum(
            'foodbankhit__hits',
            filter=Q(foodbankhit__day__gte=cutoff_date)
        )
    )
    
    # Apply sorting
    foodbanks = foodbanks.order_by(sort)

    template_vars = {
        "sort":sort,
        "display_sort_options":display_sort_options,
        "foodbanks":foodbanks,
        "section":"foodbanks",
    }
    return render(request, "admin/foodbanks.html", template_vars)


def foodbanks_csv(request):

    foodbanks = Foodbank.objects.all().order_by("-created")

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['name', 'postcode', 'charity_number', 'country', 'last_order', 'last_need', 'no_locations', 'network', 'closed', 'url', 'created', 'modified'])
    for foodbank in foodbanks:
        output.append([foodbank.name, foodbank.postcode, foodbank.charity_number, foodbank.country, foodbank.last_order, foodbank.last_need, foodbank.no_locations, foodbank.network, foodbank.is_closed, foodbank.url, foodbank.created, foodbank.modified])
    writer.writerows(output)
    return response


def foodbanks_dupe_postcodes(request):

    foodbanks = get_all_foodbanks()
    locations = get_all_locations()

    postcodes = []

    for foodbank in foodbanks:
        postcodes.append(foodbank.postcode)
    
    for location in locations:
        postcodes.append(location.postcode)

    dupes = set([x for x in postcodes if postcodes.count(x) > 1])

    template_vars = {
        "dupes":dupes,
    }
    return render(request, "admin/foodbanks_dupe_postcodes.html", template_vars)


def orders(request):

    sort_options = [
        "delivery_datetime",
        "created",
        "no_items",
        "weight",
        "calories",
        "cost",
    ]
    sort = request.GET.get("sort", "delivery_datetime")
    if sort not in sort_options:
        return HttpResponseForbidden()

    sort_string = sort
    sort = "-%s" % (sort)

    orders = Order.objects.select_related('foodbank').all().order_by(sort)

    template_vars = {
        "sort":sort_string,
        "orders":orders,
        "section":"orders",
    }
    return render(request, "admin/orders.html", template_vars)


def orders_unassigned(request):

    sort_options = [
        "delivery_datetime",
        "created",
        "no_items",
        "weight",
        "calories",
        "cost",
    ]
    sort = request.GET.get("sort", "delivery_datetime")
    if sort not in sort_options:
        return HttpResponseForbidden()

    sort_string = sort
    sort = "-%s" % (sort)

    orders = Order.objects.filter(foodbank__isnull=True).order_by(sort)

    template_vars = {
        "sort":sort_string,
        "orders":orders,
        "section":"orders",
    }
    return render(request, "admin/orders_unassigned.html", template_vars)


def orders_csv(request):

    orders = Order.objects.select_related('foodbank').all().order_by("-created")

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['id', 'created', 'delivery', 'delivery_provider', 'foodbank', 'country', 'weight', 'calories', 'items', 'cost', 'delivered_cost'])
    for order in orders:
        foodbank_name = order.foodbank.name if order.foodbank else "Unassigned"
        output.append([order.order_id, order.created, order.delivery_datetime, order.delivery_provider, foodbank_name, order.country, order.weight, order.calories, order.no_items, order.cost, order.actual_cost])
    writer.writerows(output)
    return response


def needs(request):

    uncategorised = request.GET.get("uncategorised", None)
    if uncategorised:
        needs = FoodbankChange.objects.filter(is_categorised = False).order_by("-created").exclude(change_text = "Facebook").exclude(change_text = "Unknown").exclude(change_text = "Nothing")[:200]
    else:
        needs = FoodbankChange.objects.all().order_by("-created")[:200]

    template_vars = {
        "needs":needs,
        "section":"needs",
        "uncategorised":uncategorised,
    }
    return render(request, "admin/needs.html", template_vars)


def needs_otherlines(request):

    needlines = FoodbankChangeLine.objects.filter(category = "Other").order_by("-created")[:500]

    template_vars = {
        "needlines":needlines,
    }
    return render(request, "admin/needlines.html", template_vars)


def needline_form(request, id, line_id):

    needline = get_object_or_404(FoodbankChangeLine, id = line_id)

    if request.POST:
        form = NeedLineForm(request.POST, instance=needline)
        if form.is_valid():
            order = form.save()
            return redirect("admin:needs_otherlines")
    else:
        form = NeedLineForm(instance=needline)

    page_title = "Edit %s" % str(needline)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)
    

@require_POST
def needs_deleteall(request):

    need_ids = request.POST.getlist("need")
    needs = FoodbankChange.objects.filter(id__in = need_ids)
    needs.delete()
    return redirect(reverse("admin:index"))


def needs_csv(request):

    needs = FoodbankChange.objects.all().order_by("-created")

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['id', 'created', 'foodbank', 'needs', 'excess', 'input_method'])
    for need in needs:
        output.append([need.need_id, need.created, need.foodbank_name, smart_str(need.change_text), smart_str(need.excess_change_text), need.input_method])
    writer.writerows(output)
    return response


def order(request, id):

    order = get_object_or_404(Order, order_id = id)

    template_vars = {
        "order":order,
    }
    return render(request, "admin/order.html", template_vars)


def order_form(request, id = None):

    foodbank = None
    page_title = None
    foodbank_slug = request.GET.get("foodbank")
    if foodbank_slug:
        foodbank = Foodbank.objects.get(slug=foodbank_slug)

    if id:
        order = get_object_or_404(Order, order_id = id)
    else:
        order = None

    if request.POST:
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            return redirect("admin:order", id = order.order_id)
    else:
        if foodbank:
            form = OrderForm(instance=order, initial={"foodbank":foodbank})
        else:
            form = OrderForm(instance=order)

    if id:
        page_title = "Edit %s" % str(order.order_id)
    else:
        if foodbank:
            page_title = "New Order for %s" % foodbank
        else:
            page_title = "New Order"

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


@require_POST
def order_send_notification(request, id = None):

    order = get_object_or_404(Order, order_id = id)
    
    # Cannot send notification for unassigned orders
    if not order.foodbank:
        return redirect("admin:order", id = order.order_id)

    text_body = render_to_string("admin/emails/order.txt",{"order":order})
    html_body = render_to_string("admin/emails/order.html",{"order":order})

    to_email = order.foodbank.contact_email
    if order.foodbank.notification_email:
        to_email = order.foodbank.notification_email

    send_email(
        to = to_email,
        cc = "deliveries@givefood.org.uk",
        subject = "Food donation from Give Food (%s)" % (order.order_id),
        body = text_body,
        html_body = html_body,
    )

    order.notification_email_sent = datetime.now()
    order.save()
    redir_url = "%s?donenotification=true" % (reverse("admin:order", kwargs={'id': order.order_id}))
    return redirect(redir_url)


def order_delete(request, id):

    order = get_object_or_404(Order, order_id = id)
    order.delete()
    return redirect(reverse("admin:index"))


def foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    counts = {
        "locations":FoodbankLocation.objects.filter(foodbank = foodbank).count(),
        "needs":FoodbankChange.objects.filter(foodbank = foodbank).count(),
        "orders":Order.objects.filter(foodbank = foodbank).count(),
        "donation_points":FoodbankDonationPoint.objects.filter(foodbank = foodbank).count(),
        "articles":FoodbankArticle.objects.filter(foodbank = foodbank).count(),
        "subscribers":FoodbankSubscriber.objects.filter(foodbank = foodbank).count(),
        "crawls":CrawlItem.objects.filter(foodbank = foodbank).count(),
    }

    template_vars = {
        "foodbank":foodbank,
        "counts":counts,
    }
    return render(request, "admin/foodbank.html", template_vars)


def foodbank_form(request, slug = None):

    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)
        page_title = "Edit %s" % (foodbank.full_name())
    else:
        foodbank = None
        page_title = "New Food Bank"

    if request.POST:
        form = FoodbankForm(request.POST, instance=foodbank)
        if form.is_valid():
            foodbank = form.save()

            discrepancy_id = request.GET.get("discrepancy")
            if discrepancy_id:
                discrepancy = FoodbankDiscrepancy.objects.get(id = discrepancy_id)
                discrepancy.status = "Done"
                discrepancy.save()
                return redirect("admin:index")
            else:
                return redirect("admin:foodbank", slug = foodbank.slug)

            
    else:
        if foodbank:
            form = FoodbankForm(instance=foodbank)
        else:
            form = FoodbankForm(
                initial={
                    "name": request.GET.get("name", None),
                    "address": request.GET.get("address", None),
                    "postcode": request.GET.get("postcode", None),
                }
            )        

    template_vars = {
        "form":form,
        "page_title":page_title,
        "foodbank":foodbank,
    }
    return render(request, "admin/form.html", template_vars)


def foodbank_check(request, slug):
    
    foodbank = get_object_or_404(Foodbank, slug = slug)

    # Prepare foodbank JSON
    foodbank_json = {
        "details":{
            "name": foodbank.name,
            "address": foodbank.address,
            "postcode": foodbank.postcode,
            "country": foodbank.country,
            "phone_number": foodbank.phone_number,
            "contact_email": foodbank.contact_email,
            "network": foodbank.network,
        }
    }
    foodbank_locations = []
    for location in FoodbankLocation.objects.filter(foodbank = foodbank).order_by("name"):
        foodbank_locations.append({
            "name": location.name,
            "slug": location.slug,
            "address": location.address,
            "postcode": location.postcode,
        })
    foodbank_json["locations"] = foodbank_locations
    foodbank_donation_points = []
    for donation_point in FoodbankDonationPoint.objects.filter(foodbank = foodbank).order_by("name"):
        foodbank_donation_points.append({
            "name": donation_point.name,
            "slug": donation_point.slug,
            "address": donation_point.address,
            "postcode": donation_point.postcode,
        })
    foodbank_json["donation_points"] = foodbank_donation_points

    foodbank_urls = {}

    # Get HTML
    timeout_sec = 20
    homepage = shopping_list = locations = contacts = donation_points = None
    url_blacklist = [
        "facebook.com",
        "bankthefood.org",
    ]

    # Fetch homepage
    crawl_item = CrawlItem(
        foodbank = foodbank,
        crawl_type = "check",
        url = foodbank.url,
    )
    crawl_item.save()
    homepage = requests.get(foodbank.url, headers={"User-Agent": BOT_USER_AGENT}, timeout=timeout_sec).text
    crawl_item.finish = datetime.now()
    crawl_item.save()
    foodbank_urls["Home"] = foodbank.url
    
    if foodbank.shopping_list_url and all(x not in foodbank.shopping_list_url for x in url_blacklist):
        crawl_item = CrawlItem(
            foodbank = foodbank,
            crawl_type = "check",
            url = foodbank.shopping_list_url,
        )
        crawl_item.save()
        shopping_list = htmlbodytext(requests.get(foodbank.shopping_list_url, headers={"User-Agent": BOT_USER_AGENT}, timeout=timeout_sec).text)
        crawl_item.finish = datetime.now()
        crawl_item.save()
        foodbank_urls["Shopping List"] = foodbank.shopping_list_url
        
    if foodbank.locations_url:
        crawl_item = CrawlItem(
            foodbank = foodbank,
            crawl_type = "check",
            url = foodbank.locations_url,
        )
        crawl_item.save()
        locations = htmlbodytext(requests.get(foodbank.locations_url, headers={"User-Agent": BOT_USER_AGENT}, timeout=timeout_sec).text)
        crawl_item.finish = datetime.now()
        crawl_item.save()
        foodbank_urls["Locations"] = foodbank.locations_url
        
    if foodbank.contacts_url:
        crawl_item = CrawlItem(
            foodbank = foodbank,
            crawl_type = "check",
            url = foodbank.contacts_url,
        )
        crawl_item.save()
        contacts = htmlbodytext(requests.get(foodbank.contacts_url, headers={"User-Agent": BOT_USER_AGENT}, timeout=timeout_sec).text)
        crawl_item.finish = datetime.now()
        crawl_item.save()
        foodbank_urls["Contacts"] = foodbank.contacts_url
        
    if foodbank.donation_points_url:
        if "foodbank.org.uk/support-us/donate-food" in foodbank.donation_points_url:
            if not foodbank.network_id:
                homepage_text = requests.get(foodbank.shopping_list_url).text
                network_id_search = re.search(r'\\"foodBank\\":\{\\"id\\":\\"([a-f0-9\-]{36})\\"\}', homepage_text)
                foodbank.network_id = network_id_search.group(1)
                foodbank.save()
            url = "%s?lat=%s&lng=%s&address=%s"  % (foodbank.donation_points_url, foodbank.latt(), foodbank.long(), foodbank.postcode)
            headers = {
                "User-Agent": BOT_USER_AGENT,
                "Next-Action": "b8d1dab7508947f9e5f96fd1d7ebdbeb402a31ac",
            }
            payload = [
                foodbank.network_id,
                foodbank.latt(),
                foodbank.long(),
            ]
            crawl_item = CrawlItem(
                foodbank = foodbank,
                crawl_type = "check",
                url = url,
            )
            crawl_item.save()
            donation_points = requests.post(url, headers=headers, timeout=timeout_sec, json=payload).text
            crawl_item.finish = datetime.now()
            crawl_item.save()
        else:
            crawl_item = CrawlItem(
                foodbank = foodbank,
                crawl_type = "check",
                url = foodbank.donation_points_url,
            )
            crawl_item.save()
            donation_points = htmlbodytext(requests.get(foodbank.donation_points_url, headers={"User-Agent": BOT_USER_AGENT}, timeout=timeout_sec).text)
            crawl_item.finish = datetime.now()
            crawl_item.save()
            foodbank_urls["Donation Points"] = foodbank.donation_points_url

    foodbank_pages = {
        "homepage": homepage,
        "shopping_list": shopping_list,
        "locations": locations,
        "contacts": contacts,
        "donation_points": donation_points,
    }
    prompt = render_to_string(
        "admin/prompts/check.txt",
        {
            "foodbank":foodbank,
            "foodbank_json":json.dumps(foodbank_json, indent=2),
            "foodbank_pages":foodbank_pages,
        }
    )
    check_result = gemini(
        prompt,
        0,
        response_mime_type = "application/json",
        model = "gemini-2.5-flash",
        response_schema = {
            "type": "object",
            "properties": {
                "details": {
                "type": "object",
                "properties": {
                    "name": {
                    "type": "string"
                    },
                    "address": {
                    "type": "string"
                    },
                    "postcode": {
                    "type": "string"
                    },
                    "country": {
                    "type": "string"
                    },
                    "phone_number": {
                    "type": "string"
                    },
                    "contact_email": {
                    "type": "string"
                    },
                    "network": {
                    "type": "string"
                    }
                },
                "required": [
                    "name",
                    "address",
                    "postcode",
                    "country",
                    "phone_number",
                    "contact_email",
                    "network"
                ]
                },
                "locations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                    "name": {
                        "type": "string"
                    },
                    "address": {
                        "type": "string"
                    },
                    "postcode": {
                        "type": "string"
                    }
                    },
                    "required": [
                    "name",
                    "address",
                    "postcode"
                    ]
                }
                },
                "donation_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                    "name": {
                        "type": "string"
                    },
                    "address": {
                        "type": "string"
                    },
                    "postcode": {
                        "type": "string"
                    }
                    },
                    "required": [
                    "name",
                    "address",
                    "postcode"
                    ]
                }
                }
            },
            "required": [
                "details",
                "locations",
                "donation_points"
            ]
        }
    )

    for location in foodbank_json["locations"]:
        if location["postcode"] not in [x["postcode"] for x in check_result["locations"]]:
            location["discrepancy"] = True
    for donation_point in foodbank_json["donation_points"]:
        if donation_point["postcode"] not in [x["postcode"] for x in check_result["donation_points"]]:
            donation_point["discrepancy"] = True

    for location in check_result["locations"]:
        if location["postcode"] not in [x["postcode"] for x in foodbank_json["locations"]]:
            if location["postcode"] != foodbank_json["details"]["postcode"]:
                location["discrepancy"] = True
    for donation_point in check_result["donation_points"]:
        if donation_point["postcode"] not in [x["postcode"] for x in foodbank_json["donation_points"]]:
            if donation_point["postcode"] not in [x["postcode"] for x in foodbank_json["locations"]]:
                donation_point["discrepancy"] = True

    template_vars = {
        "foodbank":foodbank,
        "foodbank_json":foodbank_json,
        "check_result":check_result,
        "foodbank_urls":foodbank_urls,
    }

    return render(request, "admin/check.html", template_vars)


@require_POST
def foodbank_crawl(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    if foodbank.rss_url:
        foodbank_article_crawl(foodbank)
    return redirect("admin:foodbank", slug = foodbank.slug)
    

@require_POST
def foodbank_rfi(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    send_email(
        to = foodbank.contact_email,
        subject = "%s listing on Give Food" % (foodbank.full_name()),
        cc = "mail@givefood.org.uk",
        body = render_to_string("admin/emails/rfi.txt",{"foodbank":foodbank}),
        html_body = render_to_string("admin/emails/rfi.html",{"foodbank":foodbank}),
    )

    foodbank.last_rfi = datetime.now()
    foodbank.save()

    return redirect("admin:foodbank", slug = foodbank.slug)


@require_POST
def foodbank_resave(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    for location in FoodbankLocation.objects.filter(foodbank = foodbank):
        location.save(do_geoupdate=False, do_foodbank_resave=False)
    for donationpoint in FoodbankDonationPoint.objects.filter(foodbank = foodbank):
        donationpoint.save(do_geoupdate=False, do_foodbank_resave=False, do_photo_update=False)
    for need in FoodbankChange.objects.filter(foodbank = foodbank):
        need.save(do_translate=False, do_foodbank_save=False)
    # for order in Order.objects.filter(foodbank = foodbank):
    #     order.save(do_foodbank_save=False)
    for subscriber in FoodbankSubscriber.objects.filter(foodbank = foodbank):
        subscriber.save()
    
    foodbank.save(do_geoupdate=False)
    
    return redirect("admin:foodbank", slug = foodbank.slug)


@require_POST
def foodbank_touch(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    foodbank.edited = datetime.now()
    foodbank.save(do_geoupdate=False)
    return redirect("admin:foodbanks")


@require_POST
def foodbank_delete(request, slug):
    
    foodbank = get_object_or_404(Foodbank, slug = slug)
    foodbank.delete()
    return redirect(reverse("admin:index"))


def foodbank_politics_form(request, slug = None):

    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)
        page_title = "Edit %s Food Bank Politics" % (foodbank.name)
    else:
        foodbank = None

    if request.POST:
        form = FoodbankPoliticsForm(request.POST, instance=foodbank)
        if form.is_valid():
            foodbank = form.save()
            return redirect("admin:foodbank", slug = foodbank.slug)
    else:
        form = FoodbankPoliticsForm(instance=foodbank)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def foodbank_urls_form(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    page_title = "Edit %s Food Bank URLs" % (foodbank.name)

    if request.POST:
        form = FoodbankUrlsForm(request.POST, instance=foodbank)
        if form.is_valid():
            foodbank = form.save()
            return redirect("admin:foodbank", slug = foodbank.slug)
    else:
        # Check which URL fields are empty and need suggestions
        initial_data = {}
        suggested_fields = []
        
        url_fields = ['shopping_list_url', 'rss_url', 'donation_points_url', 'locations_url', 'contacts_url']
        empty_fields = [field for field in url_fields if not getattr(foodbank, field)]
        
        if empty_fields and foodbank.url:
            try:
                # Create a CrawlItem to track this URL fetch
                crawl_item = CrawlItem(
                    foodbank = foodbank,
                    crawl_type = "urls",
                    url = foodbank.url,
                )
                crawl_item.save()
                
                # Fetch the foodbank's main page
                response = requests.get(foodbank.url, headers={"User-Agent": BOT_USER_AGENT}, timeout=20)
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Extract all URLs from the page using both BeautifulSoup and regex
                    all_links = set()
                    
                    # Method 1: BeautifulSoup (handles standard HTML links)
                    soup = BeautifulSoup(html_content, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        # Make URL fully qualified
                        full_url = urljoin(foodbank.url, href)
                        all_links.add(full_url)
                    
                    # Method 2: Regex (handles URLs in JavaScript, data attributes, etc.)
                    # Look for any http/https URLs
                    url_pattern = r'https?://[^\s"\'<>)]+[^\s"\'<>).,;]'
                    regex_urls = re.findall(url_pattern, html_content)
                    for url in regex_urls:
                        all_links.add(url)
                    
                    # Convert to list, remove duplicates and limit to reasonable number
                    all_links = list(all_links)[:100]
                    
                    if all_links:
                        # Use Gemini to suggest appropriate URLs for each empty field
                        prompt = f"""Given a food bank's website at {foodbank.url} and the following URLs found on their website:

{chr(10).join(all_links)}

Please analyze these URLs and suggest the best match for each of these fields (return empty string if no good match):
- shopping_list_url: URL for the shopping list or what items they need
- rss_url: URL for RSS feed
- donation_points_url: URL for donation/drop-off points or locations
- locations_url: URL for locations/where to find them
- contacts_url: URL for contact information

Only suggest URLs from the list provided. Return as JSON with these exact field names."""

                        response_schema = {
                            "type": "object",
                            "properties": {
                                "shopping_list_url": {"type": "string"},
                                "rss_url": {"type": "string"},
                                "donation_points_url": {"type": "string"},
                                "locations_url": {"type": "string"},
                                "contacts_url": {"type": "string"},
                            },
                            "required": ["shopping_list_url", "rss_url", "donation_points_url", "locations_url", "contacts_url"]
                        }
                        
                        suggestions = gemini(prompt, temperature=0, response_mime_type="application/json", response_schema=response_schema)
                        
                        # Apply suggestions to empty fields only
                        for field in empty_fields:
                            if field in suggestions and suggestions[field]:
                                initial_data[field] = suggestions[field]
                                suggested_fields.append(field)

                # Record finish time
                crawl_item.finish = datetime.now()
                crawl_item.save()
            except Exception as e:
                logging.warning(f"Failed to fetch URL suggestions for {foodbank.slug}: {e}")
                # Record finish time even on error
                if 'crawl_item' in locals():
                    crawl_item.finish = datetime.now()
                    crawl_item.save()
        
        form = FoodbankUrlsForm(instance=foodbank, initial=initial_data)
        
        # Add CSS class to suggested fields
        for field in suggested_fields:
            if field in form.fields:
                form.fields[field].widget.attrs['class'] = 'is-success'

    template_vars = {
        "form":form,
        "page_title":page_title,
        "foodbank":foodbank,
    }
    return render(request, "admin/form.html", template_vars)


def foodbank_addsub(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    page_title = "Add Subscriber to %s Food Bank" % (foodbank.name)

    if request.POST:
        emails = request.POST.get("emails")
        emails = emails.splitlines()
        for email in emails:
            new_sub = FoodbankSubscriber(
                foodbank = foodbank,
                email = email,
                confirmed = True,
            )
            new_sub.save()
        return redirect("admin:foodbank", slug = foodbank.slug)

    template_vars = {}
    return render(request, "admin/addsub.html", template_vars)

def fblocation_form(request, slug = None, loc_slug = None):

    name = request.GET.get("name", None)

    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)
        page_title = "Edit %s Food Bank Location" % (foodbank.name)
    else:
        foodbank = None

    if loc_slug:
        foodbank_location = get_object_or_404(FoodbankLocation, foodbank = foodbank, slug = loc_slug)
    else:
        foodbank_location = None

    if request.POST:
        form = FoodbankLocationForm(request.POST, instance=foodbank_location)
        if form.is_valid():
            foodbank_location = form.save()
            return redirect("admin:foodbank", slug = foodbank_location.foodbank_slug)
    else:
        initial_data = {"foodbank": foodbank}
        if name is not None:
            initial_data["name"] = name
        form = FoodbankLocationForm(instance=foodbank_location, initial=initial_data)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def fblocation_area_form(request, slug):
    
    foodbank = get_object_or_404(Foodbank, slug = slug)
    page_title = "New %s Food Bank Location from MapIt Area" % (foodbank.name)
    
    if request.POST:
        form = FoodbankLocationAreaForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            mapit_id = form.cleaned_data['mapit_id']
            
            # Get MapIt API key
            mapit_key = get_cred("mapit_key")
            
            try:
                # Fetch geometry data
                geometry_url = f"https://mapit.mysociety.org/area/{mapit_id}/geometry"
                geometry_response = requests.get(
                    geometry_url,
                    params={"api_key": mapit_key},
                    timeout=20
                )
                
                if geometry_response.status_code != 200:
                    form.add_error('mapit_id', f'Failed to fetch geometry from MapIt API (status {geometry_response.status_code})')
                else:
                    try:
                        geometry_data = geometry_response.json()
                    except ValueError:
                        form.add_error('mapit_id', 'MapIt API returned invalid JSON for geometry')
                        geometry_data = None
                    
                    if geometry_data:
                        # Fetch geojson data
                        geojson_url = f"https://mapit.mysociety.org/area/{mapit_id}.geojson"
                        geojson_response = requests.get(
                            geojson_url,
                            params={"api_key": mapit_key},
                            timeout=20
                        )
                        
                        if geojson_response.status_code != 200:
                            form.add_error('mapit_id', f'Failed to fetch geojson from MapIt API (status {geojson_response.status_code})')
                        else:
                            try:
                                geojson_data = geojson_response.json()
                            except ValueError:
                                form.add_error('mapit_id', 'MapIt API returned invalid JSON for geojson')
                                geojson_data = None
                            
                            if geojson_data:
                                # Extract centre coordinates
                                centre_lat = geometry_data.get('centre_lat')
                                centre_lon = geometry_data.get('centre_lon')
                                
                                if centre_lat is None or centre_lon is None:
                                    form.add_error('mapit_id', 'MapIt API did not return centre coordinates')
                                else:
                                    # Create lat_lng string
                                    lat_lng = f"{centre_lat},{centre_lon}"
                                    
                                    # Create boundary_geojson by wrapping the geometry
                                    boundary_geojson = json.dumps({
                                        "type": "Feature",
                                        "geometry": geojson_data
                                    })
                                    
                                    # Create new FoodbankLocation
                                    # Note: We skip do_geoupdate=False because we don't have a postcode
                                    # and Plus Codes aren't needed for area-based locations
                                    foodbank_location = FoodbankLocation(
                                        foodbank=foodbank,
                                        name=name,
                                        lat_lng=lat_lng,
                                        boundary_geojson=boundary_geojson
                                    )
                                    foodbank_location.save(do_geoupdate=False)
                                    
                                    return redirect("admin:foodbank", slug=foodbank.slug)
            except requests.exceptions.Timeout:
                form.add_error('mapit_id', 'Request to MapIt API timed out')
            except requests.exceptions.RequestException as e:
                form.add_error('mapit_id', f'Error calling MapIt API: {e}')
    else:
        form = FoodbankLocationAreaForm()
    
    template_vars = {
        "form": form,
        "page_title": page_title,
    }
    return render(request, "admin/fblocation_area_form.html", template_vars)


def fblocation_politics_edit(request, slug, loc_slug):

    if slug:
        foodbank_location = get_object_or_404(FoodbankLocation, foodbank_slug = slug, slug = loc_slug)
        page_title = "Edit %s Food Bank Location Politics" % (FoodbankLocation.foodbank.name)
    else:
        foodbank_location = None

    if request.POST:
        form = FoodbankLocationPoliticsForm(request.POST, instance=foodbank_location)
        if form.is_valid():
            foodbank_location = form.save()
            return redirect("admin:foodbank", slug = foodbank_location.foodbank.slug)
    else:
        form = FoodbankLocationPoliticsForm(instance=foodbank_location)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


@require_POST
def fblocation_delete(request, slug, loc_slug):

    foodbank = Foodbank.objects.get(slug=slug)
    foodbank_location = get_object_or_404(FoodbankLocation, foodbank = foodbank, slug = loc_slug)
    foodbank_location.delete()

    return redirect("admin:foodbank", slug = foodbank.slug)


def need(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    if need.foodbank:
        try:
            prev_published = FoodbankChange.objects.filter(foodbank = need.foodbank, created__lt = need.created, published = True).latest("created")
        except FoodbankChange.DoesNotExist:
            prev_published = None
        try:
            prev_nonpert = FoodbankChange.objects.filter(foodbank = need.foodbank, created__lt = need.created, nonpertinent = True).latest("created")
        except FoodbankChange.DoesNotExist:
            prev_nonpert = None
    else:
        prev_published = None
        prev_nonpert = None
    
    template_vars = {
        "need":need,
        "prev_published":prev_published,
        "prev_nonpert":prev_nonpert,
    }
    return render(request, "admin/need.html", template_vars)


def donationpoint_form(request, slug = None, dp_slug = None):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    name = request.GET.get("name", None)

    if dp_slug:
        donation_point = get_object_or_404(FoodbankDonationPoint, foodbank = foodbank, slug = dp_slug)
        page_title = "Edit Donation Point"
    else:
        donation_point = None
        page_title = "New Donation Point"

    if request.POST:
        form = FoodbankDonationPointForm(request.POST, instance=donation_point)
        if form.is_valid():
            donation_point = form.save()
            redir_url = "%s#donationpoints" % (reverse("admin:foodbank", kwargs={'slug': foodbank.slug}))
            return redirect(redir_url)
    else:
        initial_data = {"foodbank": foodbank}
        if name is not None:
            initial_data["name"] = name
        form = FoodbankDonationPointForm(instance=donation_point, initial=initial_data)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def donationpoint_delete(request, slug, dp_slug):
    
    foodbank = Foodbank.objects.get(slug=slug)
    donation_point = get_object_or_404(FoodbankDonationPoint, foodbank = foodbank, slug = dp_slug)
    donation_point.delete()

    return redirect("admin:foodbank", slug = foodbank.slug)


def need_form(request, id = None):

    if id:
        need = get_object_or_404(FoodbankChange, need_id = id)
        page_title = "Edit Need"
    else:
        need = None
        page_title = "New Need"

    foodbank = None
    foodbank_slug = request.GET.get("foodbank")
    if foodbank_slug:
        foodbank = Foodbank.objects.get(slug=foodbank_slug)

    if request.POST:
        form = NeedForm(request.POST, instance=need)
        if form.is_valid():
            need = form.save()
            return redirect("admin:need", id = need.need_id)
    else:
        if foodbank:
            form = NeedForm(instance=need, initial={"foodbank":foodbank})
        else:
            form = NeedForm(instance=need)

    template_vars = {
        "form":form,
        "page_title":page_title,
        "need":need,
    }
    return render(request, "admin/form.html", template_vars)


@require_POST
def need_nonpertinent(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    need.nonpertinent = True
    need.save()
    return redirect("admin:index")


@require_POST
def need_delete(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    need.delete()
    return redirect("admin:index")


@require_POST
def need_publish(request, id, action):

    need = get_object_or_404(FoodbankChange, need_id = id)
    if action == "publish":
        need.published = True
    if action == "unpublish":
        need.published = False
    need.save(do_translate = True)
    need.save()
    return redirect("admin:need", id = need.need_id)


@require_POST
def need_notifications(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    
    foodbank = need.foodbank

    # Check for foodbank articles
    if foodbank.rss_url:
        foodbank_article_crawl(foodbank)

    # Update tweet time
    need.tweet_sent = datetime.now()
    need.save(do_foodbank_save=False, do_translate=False)

    # Email subscriptions
    subscribers = FoodbankSubscriber.objects.filter(foodbank = foodbank, confirmed = True)
    for subscriber in subscribers:
        post_to_subscriber(need, subscriber)
    
    # Send Firebase notification
    send_firebase_notification(need)

    return redirect("admin:need", id = need.need_id)


def need_translations(request, id):
    
    need = get_object_or_404(FoodbankChange, need_id = id)
    translations = FoodbankChangeTranslation.objects.filter(need = need)

    template_vars = {
        "need":need,
        "translations":translations,
    }
    return render(request, "admin/need_translations.html", template_vars)


def need_email(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    format = request.GET.get("format")

    if format == "html":
        extension = "html"
        content_type = "text/html"
    else:
        extension = "txt"
        content_type = "text/plain"

    template_vars = {
        "need":need,
    }
    return render(request, "wfbn/emails/notification.%s" % (extension), template_vars, content_type = content_type)


def need_categorise(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    forms = []
    
    if request.POST:
        for line in need.change_text.split("\n"):
            try:
                need_line = FoodbankChangeLine.objects.get(need = need, item = line)
                form = NeedLineForm(request.POST, prefix=line, instance=need_line)
            except FoodbankChangeLine.DoesNotExist:
                form = NeedLineForm(request.POST, prefix=line)

            if form.is_valid():
                need_line = form.save(commit=False)
                need_line.need = need
                need_line.save()

        if need.excess_change_text:
            for line in need.excess_change_text.split("\n"):
                try:
                    need_line = FoodbankChangeLine.objects.get(need = need, item = line)
                    form = NeedLineForm(request.POST, prefix=line, instance=need_line)
                except FoodbankChangeLine.DoesNotExist:
                    form = NeedLineForm(request.POST, prefix=line)

                if form.is_valid():
                    need_line = form.save(commit=False)
                    need_line.need = need
                    need_line.save()

        need.is_categorised = True
        need.save(do_foodbank_save = False)

        return redirect("admin:need", id = need.need_id)
    
    # Needs
    for line in need.change_text.split("\n"):
        try:
            need_line = FoodbankChangeLine.objects.get(need = need, item = line)
            form = NeedLineForm(instance=need_line, prefix=line)
        except FoodbankChangeLine.DoesNotExist:
            try:
                prev_need_line = FoodbankChangeLine.objects.filter(item = line).latest("created")
                form = NeedLineForm(initial={"item":line, "type":"need", "category":prev_need_line.category}, prefix=line)
            except FoodbankChangeLine.DoesNotExist:
                form = NeedLineForm(initial={"item":line, "type":"need"}, prefix=line)
            
        forms.append(form)
    # Excess
    if need.excess_change_text:
        for line in need.excess_change_text.split("\n"):
            try:
                need_line = FoodbankChangeLine.objects.get(need = need, item = line)
                form = NeedLineForm(instance=need_line, prefix=line)
            except FoodbankChangeLine.DoesNotExist:
                try:
                    prev_need_line = FoodbankChangeLine.objects.filter(item = line).latest("created")
                    form = NeedLineForm(initial={"item":line, "type":"excess", "category":prev_need_line.category}, prefix=line)
                except FoodbankChangeLine.DoesNotExist:
                    form = NeedLineForm(initial={"item":line, "type":"excess"}, prefix=line)
            forms.append(form)

    template_vars = {
        "need":need,
        "forms":forms,
    }
    
    return render(request, "admin/need_categorise.html", template_vars)


def locations(request):

    sort_options = [
        "foodbank_name",
        "name",
        "parliamentary_constituency",
        "edited",
    ]
    sort = request.GET.get("sort", "foodbank_name")
    if sort not in sort_options:
        return HttpResponseForbidden()

    locations = FoodbankLocation.objects.all().order_by(sort)

    template_vars = {
        "sort":sort,
        "locations":locations,
        "section":"locations",
    }
    return render(request, "admin/locations.html", template_vars)


def locations_loader_sa(request):

    sa_foodbank = Foodbank.objects.get(slug="salvation-army")

    with open('./givefood/data/sa_locations.csv') as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        for row in readCSV:

            logging.info(row)
            name = row[0]
            address = row[1]
            postcode = row[2]
            email = row[3]
            phone = row[4]
            lat_lng = row[5]

            try:
                foodbank_location = FoodbankLocation.objects.get(name=name,foodbank=sa_foodbank)
            except FoodbankLocation.DoesNotExist:
                foodbank_location = FoodbankLocation(
                    foodbank = sa_foodbank,
                    name = name,
                    address = address,
                    postcode = postcode,
                    email = email,
                    phone_number = phone,
                    lat_lng = lat_lng,
                )
                foodbank_location.save()


    return HttpResponse("OK")


def discrepancy(request, id):
    
    discrepancy = get_object_or_404(FoodbankDiscrepancy, id = id)
    foodbank_form = FoodbankForm(instance=discrepancy.foodbank)
    
    template_vars = {
        "discrepancy":discrepancy,
        "foodbank_form":foodbank_form,
    }
    return render(request, "admin/discrepancy.html", template_vars)


def discrepancy_action(request, id):

    action = request.POST.get("action")
    discrepancy = get_object_or_404(FoodbankDiscrepancy, id = id)
    if action == "invalid":
        discrepancy.status = "Invalid"
    if action == "done":
        discrepancy.status = "Done"
    
    discrepancy.save()

    return redirect("admin:index")


def donationpoints(request):
    
    sort_options = [
        "name",
        "foodbank_name",
        "edited",
    ]
    sort = request.GET.get("sort", "name")
    if sort not in sort_options:
        return HttpResponseForbidden()

    donation_points = FoodbankDonationPoint.objects.all().order_by(sort)

    template_vars = {
        "sort":sort,
        "donation_points":donation_points,
        "section":"donationpoints",
    }
    return render(request, "admin/donationpoints.html", template_vars)


def items(request):

    items = OrderItem.objects.all()

    template_vars = {
        "items":items,
        "section":"items",
    }
    return render(request, "admin/items.html", template_vars)


def item_form(request, slug = None):

    if slug:
        item = get_object_or_404(OrderItem, slug = slug)
        page_title = "Edit Item"
    else:
        item = None
        page_title = "New Item"

    if request.POST:
        form = OrderItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            return redirect("admin:items")
    else:
        form = OrderItemForm(instance=item)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def slug_redirects(request):

    slug_redirects = SlugRedirect.objects.all().order_by("-created")

    template_vars = {
        "slug_redirects":slug_redirects,
        "section":"settings",
    }
    return render(request, "admin/slug_redirects.html", template_vars)


def slug_redirect_form(request, id = None):

    if id:
        slug_redirect = get_object_or_404(SlugRedirect, id = id)
        page_title = "Edit Slug Redirect"
    else:
        slug_redirect = None
        page_title = "New Slug Redirect"

    if request.POST:
        form = SlugRedirectForm(request.POST, instance=slug_redirect)
        if form.is_valid():
            slug_redirect = form.save()
            return redirect("admin:slug_redirects")
    else:
        form = SlugRedirectForm(instance=slug_redirect)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def politics(request):

    parlcons = ParliamentaryConstituency.objects.all().order_by("name")

    template_vars = {
        "parlcons":parlcons,
        "section":"politics",
    }
    return render(request, "admin/politics.html", template_vars)


def politics_csv(request):

    foodbanks = get_all_foodbanks()
    locations = FoodbankLocation.objects.all()

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['constituency', 'mp', 'mp_party', 'mp_parl_id'])
    for foodbank in foodbanks:
        output.append([foodbank.parliamentary_constituency_name, foodbank.mp, foodbank.mp_party, foodbank.mp_parl_id])
    for location in locations:
        output.append([location.parliamentary_constituency_name, location.mp, location.mp_party, location.mp_parl_id])
    writer.writerows(output)
    return response


def quarter_stats(request):

    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    orders = Order.objects.filter(created__gte=start_date, created__lte=end_date)
    order_count = orders.count()

    weight = 0
    items = 0
    calories = 0
    cost = 0
    
    for order in orders:
        weight += order.weight
        items += order.no_items
        calories += order.calories
        cost += order.cost

    weight = "%s kg" % (round(weight / 1000,2))
    cost = "£%s" % (round(cost / 100,2))

    edits = Foodbank.objects.filter(edited__gte=start_date, edited__lte=end_date).count()
    new_subscribers = FoodbankSubscriber.objects.filter(created__gte=start_date, created__lte=end_date).count()
    items_found = FoodbankChangeLine.objects.filter(created__gte=start_date, created__lte=end_date).count()

    stats = {
        "Start Date":start_date,
        "End Date":end_date,
        "Deliveries":order_count,
        "Items":items,
        "Weight":weight,
        "Calories":calories,
        "Cost":cost,
        "Edits":edits,
        "Subscriptions":new_subscribers,
        "Items Found":items_found,
    }

    template_vars = {
        "stats":stats,
        "title":"Quarter",
        "section":"stats",
    }

    return render(request, "admin/stats.html", template_vars)
    

def edit_stats(request):

    foodbanks = Foodbank.objects.count()
    locations = FoodbankLocation.objects.count()
    headline_locations = locations + foodbanks

    donation_points = FoodbankDonationPoint.objects.all().count()
    headline_donation_points = donation_points + Foodbank.objects.exclude(address_is_administrative = True).count() + Foodbank.objects.exclude(delivery_address = "").count() + FoodbankLocation.objects.filter(is_donation_point = True).count()

    newest_edit = Foodbank.objects.all().order_by("-edited")[:1][0].edited
    oldest_edit = Foodbank.objects.all().order_by("edited")[:1][0].edited

    stats = {
        "Total Food Banks":foodbanks,
        "Total Locations":locations,
        "Headline Locations":headline_locations,
        "Donation Points":donation_points,
        "Headline DP":headline_donation_points,
        "FB With DP":Foodbank.objects.exclude(no_donation_points = 0).count(),
        "Newest Edit":newest_edit,
        "Oldest Edit":oldest_edit,
        "Total Discrepancies":FoodbankDiscrepancy.objects.count(),
        "Discrepancies Outstanding":FoodbankDiscrepancy.objects.filter(status = "New").count(),
        "Discrepancies Invalid":FoodbankDiscrepancy.objects.filter(status = "Invalid").count(),
        "Discrepancies Done":FoodbankDiscrepancy.objects.filter(status = "Done").count(),
    }

    template_vars = {
        "stats":stats,
        "title":"Edit",
        "section":"stats",
    }

    return render(request, "admin/stats.html", template_vars)


def order_stats(request):

    total_weight = Order.objects.aggregate(Sum("weight"))["weight__sum"]
    total_calories = Order.objects.aggregate(Sum("calories"))["calories__sum"]
    total_items = Order.objects.aggregate(Sum("no_items"))["no_items__sum"]
    total_cost = Order.objects.aggregate(Sum("cost"))["cost__sum"]
    total_orders = Order.objects.all().count()

    total_weight = total_weight / 1000
    total_weight_pkg = total_weight * PACKAGING_WEIGHT_PC
    total_weight_pkg = round(total_weight_pkg, 2)

    total_cost = float(total_cost) / 100

    stats = {
        "Total Weight":total_weight,
        "Total Calories":total_calories,
        "Total Items":total_items,
        "Total Orders":total_orders,
        "Total Cost":total_cost,
        "Total Weight (inc. packaging)":total_weight_pkg,
    }

    template_vars = {
        "stats":stats,
        "title":"Order",
        "section":"stats",
    }

    return render(request, "admin/stats.html", template_vars)


def subscriber_stats(request):

    stats = {
        "Confirmed":FoodbankSubscriber.objects.filter(confirmed = True).count(),
        "Unconfirmed":FoodbankSubscriber.objects.filter(confirmed = False).count(),
    }

    template_vars = {
        "stats":stats,
        "title":"Subscriber",
        "section":"stats",
    }

    return render(request, "admin/stats.html", template_vars)


def subscriber_graph(request):

    week_subs = OrderedDict()

    subs = FoodbankSubscriber.objects.filter(confirmed = True).order_by("created")

    for sub in subs:
        week_number = sub.created.isocalendar()[1]
        year = sub.created.year
        week_key = "%s-%s" % (year, week_number)
        week_subs[week_key] = week_subs.get(week_key, 0) + 1

    template_vars = {
        "week_subs":week_subs,
    }
    return render(request, "admin/sub_graph.html", template_vars)


def finder_stats(request):

    stats = {
        "Places":Place.objects.count(),
        "Checked Places":Place.objects.filter(checked__isnull=False).count(),
    }

    template_vars = {
        "stats":stats,
        "title":"Finder",
        "section":"stats",
    }

    return render(request, "admin/stats.html", template_vars)


def need_stats(request):

    stats = {
        "Needs": FoodbankChange.objects.count(),
        "Items": FoodbankChangeLine.objects.all().count(),
        "Needed Items": FoodbankChangeLine.objects.filter(type = "need").count(),
        "Excess Items": FoodbankChangeLine.objects.filter(type = "excess").count(),
    }

    template_vars = {
        "stats":stats,
        "title":"Need",
        "section":"stats",
    }

    return render(request, "admin/stats.html", template_vars)

def order_email(request, id):

    order = get_object_or_404(Order, order_id = id)
    format = request.GET.get("format")

    if format == "html":
        extension = "html"
        content_type = "text/html"
    else:
        extension = "txt"
        content_type = "text/plain"

    template_vars = {
        "order":order,
    }
    return render(request, "emails/order.%s" % (extension), template_vars, content_type = content_type)


def parlcon_form(request, slug = None):

    if slug:
        parlcon = get_object_or_404(ParliamentaryConstituency, slug = slug)
        page_title = "Edit Parlimentary Constituency"
    else:
        parlcon = None
        page_title = "New Parlimentary Constituency"

    if request.POST:
        form = ParliamentaryConstituencyForm(request.POST, instance=parlcon)
        if form.is_valid():
            foodbank = form.save()
            return redirect("admin:politics")
    else:
        form = ParliamentaryConstituencyForm(instance=parlcon)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def parlcon_loader(request):

    foodbanks = Foodbank.objects.all()
    locations = FoodbankLocation.objects.all()
    donation_points = FoodbankDonationPoint.objects.all()

    for foodbank in foodbanks:
        try:
            logging.info("trying fb parlcon %s" % foodbank.parliamentary_constituency_slug)
            parlcon = ParliamentaryConstituency.objects.get(slug = foodbank.parliamentary_constituency_slug)
        except ParliamentaryConstituency.DoesNotExist:
            logging.info("adding %s" % foodbank.parliamentary_constituency_slug)
            newparlcon = ParliamentaryConstituency(
                name = foodbank.parliamentary_constituency,
                # mp = foodbank.mp,
                # mp_party = foodbank.mp_party,
                # mp_parl_id = foodbank.mp_parl_id,
            )
            newparlcon.save()


    for location in locations:
        try:
            logging.info("trying loc parlcon %s" % location.parliamentary_constituency_slug)
            parlcon = ParliamentaryConstituency.objects.get(slug = location.parliamentary_constituency_slug)
        except ParliamentaryConstituency.DoesNotExist:
            logging.info("adding %s" % location.parliamentary_constituency_slug)
            newparlcon = ParliamentaryConstituency(
                name = location.parliamentary_constituency,
                # mp = location.mp,
                # mp_party = location.mp_party,
                # mp_parl_id = location.mp_parl_id,
            )
            newparlcon.save()

    for donation_point in donation_points:
        try:
            logging.info("trying dp parlcon %s" % donation_point.parliamentary_constituency_slug)
            parlcon = ParliamentaryConstituency.objects.get(slug = donation_point.parliamentary_constituency_slug)
        except ParliamentaryConstituency.DoesNotExist:
            logging.info("adding %s" % donation_point.parliamentary_constituency_slug)
            newparlcon = ParliamentaryConstituency(
                name = donation_point.parliamentary_constituency,
                # mp = donation_point.mp,
                # mp_party = donation_point.mp_party,
                # mp_parl_id = donation_point.mp_parl_id,
            )
            newparlcon.save()

    return HttpResponse("OK")


def parlcon_loader_geojson(request):

    parlcons = ParliamentaryConstituency.objects.all()

    files = [
        "gb",
    ]

    for file in files:
        geojson_file = open('./givefood/data/parlcon/%s.geojson' % (file), 'r')
        lines = geojson_file.readlines()

        for line in lines:
            # logging.info(line)
            for parlcon in parlcons:
                # if not parlcon.boundary_geojson:
                if parlcon.name in line:
                    logging.info("Found " + parlcon.name)
                    parlcon.boundary_geojson = line
                    parlcon.save()

    return HttpResponse("OK")


def parlcon_loader_centre(request):

    parlcons = ParliamentaryConstituency.objects.all()

    with open('./givefood/data/parlcon/centres.csv') as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        for row in readCSV:
            parl_con_name = row[0]

            try:
                parl_con = ParliamentaryConstituency.objects.get(name=parl_con_name)
                if not parl_con.centroid:
                    logging.info("Got %s" % parl_con_name)
                    parl_con.centroid = row[1]
                    parl_con.save()
                    logging.info("Saved %s" % parl_con_name)
                else:
                    logging.info("Already got %s" % parl_con_name)
            except ParliamentaryConstituency.DoesNotExist:
                logging.info("Couldn't find %s" % parl_con_name)

    return HttpResponse("OK")


def parlcon_loader_twitter_handle(request):

    with open('./givefood/data/mp_twitter.csv') as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        for row in readCSV:

            logging.info(row)

            parl_con_name = row[3]
            handle = row[1].replace("@","")

            try:
                parl_con = ParliamentaryConstituency.objects.get(name=parl_con_name)
                parl_con.mp_twitter_handle = handle
                parl_con.save()
            except ParliamentaryConstituency.DoesNotExist:
                logging.info("Couldn't find %s" % parl_con_name)
            

    return HttpResponse("OK")


def places_loader(request):

    with open('./givefood/data/places.csv') as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')

        for row in readCSV:

            try:
                new_place = Place(
                    gbpnid = row[0],
                    name = row[1],
                    lat_lng = "%s,%s" % (row[2], row[3]),
                    histcounty = row[4],
                    adcounty = row[5],
                    district = row[6],
                    uniauth = row[7],
                    police = row[8],
                    region = row[9],
                    type = row[10],
                )
                new_place.save()
            except IntegrityError:
                # Skip duplicate places (unique constraint on gbpnid)
                # This allows re-running the loader without errors
                pass

    return HttpResponse("OK")


def finder(request):

    place = Place.objects.filter(checked__isnull=True).order_by('?').first()
        
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json?query=food bank&location=%s&radius=5000&region=uk&key=%s" % (place.lat_lng, get_cred("gmap_places_key"))
    response = requests.get(search_url)
    if response.status_code == 200:
        search_results = response.json()["results"]

    for result in search_results:
        result["distance"] = distance_meters(place.lat(), place.lng(), result["geometry"]["location"]["lat"], result["geometry"]["location"]["lng"])/1000

        try:
            result["postcode"] = re.findall("[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][ABD-HJLNP-UW-Z]{2}", result["formatted_address"])[0]
        except IndexError:
            result["postcode"] = None

        try:
            matched_foodbank = Foodbank.objects.get(postcode=result["postcode"])
        except Foodbank.DoesNotExist:
            try:
                matched_location = FoodbankLocation.objects.get(postcode=result["postcode"])
                matched_foodbank = matched_location.foodbank
                result["closest_foodbank"] = None
            except FoodbankLocation.DoesNotExist:
                matched_foodbank = None
                closest_foodbank = find_locations("%s,%s" % (result["geometry"]["location"]["lat"], result["geometry"]["location"]["lng"]),1)[0]
                result["closest_foodbank"] = closest_foodbank

        result["matched_foodbank"] = matched_foodbank

    template_vars = {
        "section":"finder",
        'gmap_static_key':get_cred("gmap_static_key"),
        "place":place,
        "search_url":search_url,
        "search_results":search_results,
    }
    return render(request, "admin/finder.html", template_vars)


@require_POST
def finder_check(request):

    place = Place.objects.get(gbpnid = request.POST["place"])
    place.checked = datetime.now()
    place.save()

    return redirect("admin:finder")


def finder_trussell(request):

    url = "https://www.trussell.org.uk/food-donation?lat=51.07167399999999&lng=-1.8121246&address=SP2%207HL&page="
    page = 1
    trussell_urls = []
    at_the_end = False

    while at_the_end == False:
        page_url = "%s%s&randomthing=%s" % (url, page, randrange(1000))
        headers = {
            "User-Agent": BOT_USER_AGENT,
        }
        response = requests.get(page_url, headers = headers)
        page_text = response.text
        if "Sorry, there are no results which match your location." in page_text:
            at_the_end = True
        trussell_urls.extend(re.findall(r"https://(\w+)\.foodbank\.org\.uk/", page_text))
        page = page + 1
    trussell_urls = list(set(trussell_urls))
    trussell_urls.sort()

    our_slugs = []
    foodbanks = Foodbank.objects.filter(network = "Trussell").exclude(is_closed = True)
    for foodbank in foodbanks:
        our_slugs.append(foodbank.url.replace("https://","").replace(".foodbank.org.uk","").replace("/",""))
    our_slugs.sort()

    missing = []
    for trussell_url in trussell_urls:
        if trussell_url not in our_slugs:
            missing.append(trussell_url)


    template_vars = {
        "section":"finder",
        "trussell_urls":trussell_urls,
        "our_slugs":our_slugs,
        "missing":missing,
    }
    return render(request, "admin/finder_trussell.html", template_vars)



def finder_fsa(request):

    with open('./givefood/data/fsa/establishments.json') as jsonfile:
        data = json.load(jsonfile)
        establishments = data["EstablishmentCollection"]["EstablishmentDetail"]

    foodbank_postcodes = []
    foodbanks = Foodbank.objects.filter(is_closed = False)
    locations = FoodbankLocation.objects.filter(is_closed = False)
    for foodbank in foodbanks:
        foodbank_postcodes.append(foodbank.postcode)
    for location in locations:
        foodbank_postcodes.append(location.postcode)

    unmatched_foodbanks = []

    for establishment in establishments:
        if establishment["PostCode"] not in foodbank_postcodes:
            unmatched_foodbanks.append(establishment)

    template_vars = {
        "section":"finder",
        "unmatched_foodbanks":unmatched_foodbanks,
    }
    return render(request, "admin/finder_fsa.html", template_vars)


def settings(request):

    template_vars = {
        "section":"settings",
    }
    return render(request, "admin/settings.html", template_vars)


def order_groups(request):

    order_groups = OrderGroup.objects.all().order_by("-created")

    template_vars = {
        "section":"settings",
        "order_groups":order_groups,
    }
    return render(request, "admin/order_groups.html", template_vars)


def order_group(request, slug):

    order_group = get_object_or_404(OrderGroup, slug = slug)

    orders = order_group.orders()

    no_orders = 0
    items = 0
    weight = 0
    calories = 0
    cost = 0

    for order in orders:
        no_orders += 1
        items += order.no_items
        weight += order.weight_kg_pkg()
        calories += order.calories
        cost += order.cost

    template_vars = {
        "section":"settings",
        "order_group":order_group,
        "orders":orders,
        "no_orders":no_orders,
        "items":items,
        "weight":weight,
        "calories":calories,
        "cost":cost/100,
    }
    return render(request, "admin/order_group.html", template_vars)


def order_group_form(request, slug=None):

    if slug:
        item = get_object_or_404(OrderGroup, slug = slug)
        page_title = "Edit Order Group"
    else:
        item = None
        page_title = "New Order Group"

    if request.POST:
        form = OrderGroupForm(request.POST, instance=item)
        if form.is_valid():
            order_group = form.save()
            return redirect("admin:order_groups")
    else:
        form = OrderGroupForm(instance=item)
        page_title = "New Order Group"

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def foodbank_groups(request):

    foodbank_groups = FoodbankGroup.objects.all().order_by("name")

    template_vars = {
        "section":"settings",
        "foodbank_groups":foodbank_groups,
    }
    return render(request, "admin/foodbank_groups.html", template_vars)


def foodbank_group(request, slug):


    foodbank_group = get_object_or_404(FoodbankGroup, slug = slug)

    template_vars = {
        "section":"settings",
        "foodbank_group":foodbank_group,
    }
    return render(request, "admin/foodbank_group.html", template_vars)


def foodbank_group_form(request, slug=None):

    if slug:
        item = get_object_or_404(FoodbankGroup, slug = slug)
        page_title = "Edit Foodbank Group"
    else:
        item = None
        page_title = "New Foodbank Group"

    if request.POST:
        form = FoodbankGroupForm(request.POST, instance=item)
        if form.is_valid():
            foodbank_group = form.save()
            return redirect("admin:foodbank_groups")
    else:
        form = FoodbankGroupForm(instance=item)
        page_title = "New Foodbank Group"

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def credentials(request):

    credentials = GfCredential.objects.all().order_by("-created")

    template_vars = {
        "section":"settings",
        "credentials":credentials,
    }
    return render(request, "admin/credentials.html", template_vars)


def credentials_form(request):

    if request.POST:
        form = GfCredentialForm(request.POST)
        if form.is_valid():
            cred = form.save()
            return redirect("admin:credentials")
    else:
        form = GfCredentialForm()
        page_title = "New Credential"

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def subscriptions(request):

    filter = request.GET.get("filter", "all")

    if filter == "all":
        subscriptions = FoodbankSubscriber.objects.all().order_by("-created")
    else:
        subscriptions = FoodbankSubscriber.objects.filter(confirmed = False).order_by("-created")

    template_vars = {
        "section":"settings",
        "filter":filter,
        "subscriptions":subscriptions,
    }
    return render(request, "admin/subscriptions.html", template_vars)


def subscriptions_csv(request):
    
    subscriptions = FoodbankSubscriber.objects.all().order_by("-created")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="subscriptions.csv"'

    writer = csv.writer(response)
    writer.writerow(["Email", "Foodbank","Created"])

    for subscription in subscriptions:
        writer.writerow([subscription.email, subscription.foodbank_name, subscription.created.date()])

    return response


@require_POST
def delete_subscription(request):

    email = request.POST.get("email")
    foodbank_slug = request.POST.get("foodbank")
    foodbank = get_object_or_404(Foodbank, slug = foodbank_slug)
    subscriber = get_object_or_404(FoodbankSubscriber, email = email, foodbank = foodbank)
    subscriber.delete()

    return redirect("admin:subscriptions")


def places(request):
    
    places = Place.objects.all().order_by("-checked")[:1000]

    template_vars = {
        "section":"settings",
        "places":places,
    }
    return render(request, "admin/places.html", template_vars)


def foodbanks_without_need(request):

    foodbanks = Foodbank.objects.all()
    for foodbank in foodbanks:
        try:
            foodbank.need = FoodbankChange.objects.filter(foodbank_name=foodbank.name, published=True).latest("created")
        except FoodbankChange.DoesNotExist:
            foodbank.need = None

    template_vars = {
        "section":"settings",
        "foodbanks":foodbanks,
    }
    return render(request, "admin/foodbanks_without_need.html", template_vars)


def clearcache(request):

    cache.clear()
    return redirect("admin:index")


def email_tester(request):

    return render(request, "admin/email_tester.html")


def email_tester_test(request):

    email = request.GET.get("email", "confirm.html")

    foodbank = Foodbank.objects.all().latest("modified")
    need = FoodbankChange.objects.filter(published = True).latest("created")
    order = Order.objects.all().latest("created")

    if email[0:3] == "rfi" or email[0:5] == "order":
        template_file = "admin/emails/%s" % (email)
    else:
        template_file = "wfbn/emails/%s" % (email)

    template_vars = {
        "foodbank":foodbank,
        "need":need,
        "order":order,
        "sub_key":"SUBKEY123456789",
        "subscriber":{
            "created":datetime.now(),
            "unsub_key":"UNSUBKEY123456789",
        }
    }

    rendered_template = render_to_string(template_file, template_vars)
    
    if email[-4:] == ".txt":
        rendered_template = "<pre>%s</pre>" % (rendered_template)
    
    return HttpResponse(rendered_template)


def crawl_sets(request):

    crawl_sets = CrawlSet.objects.annotate(
        item_count=Count('crawlitem'),
        object_count=Count('crawlitem', filter=Q(crawlitem__object_id__isnull=False))
    ).order_by("-start")[:50]

    # Get CrawlItems without CrawlSets
    orphaned_crawl_items = CrawlItem.objects.filter(crawl_set__isnull=True).select_related('foodbank').order_by("-start")[:50]

    template_vars = {
        "section":"settings",
        "crawl_sets":crawl_sets,
        "orphaned_crawl_items":orphaned_crawl_items,
    }

    return render(request, "admin/crawl_sets.html", template_vars)


def crawl_set(request, crawl_set_id):

    crawl_set = get_object_or_404(CrawlSet, pk=crawl_set_id)
    crawl_items = CrawlItem.objects.filter(crawl_set=crawl_set).select_related('foodbank').order_by("object_id", "-start")

    template_vars = {
        "section":"settings",
        "crawl_set":crawl_set,
        "crawl_items":crawl_items
    }
    return render(request, "admin/crawl_set.html", template_vars)


def proxy(request):

    url = request.GET.get("url")
    headers = {
        "User-Agent": BOT_USER_AGENT,
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Rewrite all anchor links to go through the proxy
        for a_tag in soup.find_all('a', href=True):
            original_href = a_tag['href']
            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(url, original_href)
            # Rewrite the href to go through the proxy
            proxy_url = reverse('admin:proxy') + '?url=' + quote(absolute_url, safe='')
            a_tag['href'] = proxy_url
            
            # Remove target attribute to keep navigation inside iframe
            if a_tag.has_attr('target'):
                del a_tag['target']
        
        return HttpResponse(str(soup))
    else:
        return HttpResponse("%s returned %s. You should check the URL" % (url, response.status_code))


def gmap_proxy(request, type):

    if type == "textsearch":
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    if type == "placedetails":
        url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = request.GET.dict()
    response = requests.get(url, params=params)
    return JsonResponse(response.json())