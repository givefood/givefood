import csv
import logging
import re
import requests
from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.utils.encoding import smart_str
from django.core.cache import cache
from django.db import IntegrityError, connection
from django.db.models import Sum

from givefood.const.general import PACKAGING_WEIGHT_PC
from givefood.func import foodbank_article_crawl, get_all_foodbanks, get_all_locations, post_to_subscriber, send_email, get_all_constituencies, get_cred, distance_meters
from givefood.models import Foodbank, FoodbankGroup, Order, OrderGroup, OrderItem, FoodbankChange, FoodbankLocation, ParliamentaryConstituency, GfCredential, FoodbankSubscriber, FoodbankGroup, Place
from givefood.forms import FoodbankForm, OrderForm, NeedForm, FoodbankPoliticsForm, FoodbankLocationForm, FoodbankLocationPoliticsForm, OrderGroupForm, ParliamentaryConstituencyForm, OrderItemForm, GfCredentialForm, FoodbankGroupForm


def index(request):

    foodbanks = Foodbank.objects.filter(last_order__isnull=False).order_by("-edited")[:30]

    today = datetime.today()
    today_orders = Order.objects.filter(delivery_date = today).order_by("delivery_hour")

    upcoming_orders = Order.objects.filter(delivery_date__gt = today).order_by("delivery_date")

    prev_order_threshold = datetime.now() - timedelta(days=1)
    prev_orders = Order.objects.filter(delivery_datetime__lt = prev_order_threshold).order_by("-delivery_datetime")[:20]

    unpublished_needs = FoodbankChange.objects.filter(published = False).order_by("-created")
    published_needs = FoodbankChange.objects.filter(published = True).order_by("-created")[:20]

    template_vars = {
        "foodbanks":foodbanks,
        "today_orders":today_orders,
        "upcoming_orders":upcoming_orders,
        "prev_orders":prev_orders,
        "unpublished_needs":unpublished_needs,
        "published_needs":published_needs,
        "section":"home",
    }
    return render(request, "admin/index.html", template_vars)


def search_results(request):

    query = request.GET.get("q")
    all_foodbanks = get_all_foodbanks()
    all_locations = get_all_locations()
    all_constituencies = get_all_constituencies()

    foodbanks = []
    locations = []
    constituencies = []

    for foodbank in all_foodbanks:
        if query.lower() in foodbank.name.lower():
            foodbanks.append(foodbank)
        if query.lower() in foodbank.address.lower():
            foodbanks.append(foodbank)
        if query.lower() in foodbank.postcode.lower():
            foodbanks.append(foodbank)
    
    for location in all_locations:
        if query.lower() in location.name.lower():
            locations.append(location)
        if query.lower() in location.address.lower():
            locations.append(location)

    for constituency in all_constituencies:
        if query.lower() in constituency.name.lower():
            constituencies.append(constituency)

    foodbanks = list(set(foodbanks))
    locations = list(set(locations))
    constituencies = list(set(constituencies))

    if not constituencies and not locations and len(foodbanks) == 1:
        return redirect(reverse("admin:foodbank", args=(foodbanks[0].slug,)))
    
    template_vars = {
        "query":query,
        "foodbanks":foodbanks,
        "locations":locations,
        "constituencies":constituencies,
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
    ]
    sort = request.GET.get("sort", "edited")
    if sort not in sort_options:
        return HttpResponseForbidden()
    
    display_sort_options = {}
    for sort_option in sort_options:
        display_sort_options[sort_option] = sort_option.replace("_", " ").title()

    foodbanks = Foodbank.objects.all().order_by(sort)

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


def foodbanks_christmascards(request):

    foodbanks = Foodbank.objects.filter(is_closed = False).order_by("name")

    template_vars = {
        "foodbanks":foodbanks,
    }
    return render(request, "admin/foodbanks_christmascards.html", template_vars)


def foodbanks_delivery_addresses(request):

    foodbanks = Foodbank.objects.all().order_by("name")

    template_vars = {
        "foodbanks":foodbanks,
    }
    return render(request, "admin/foodbanks_deliveryaddresses.html", template_vars)


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

    orders = Order.objects.all().order_by(sort)

    template_vars = {
        "sort":sort_string,
        "orders":orders,
        "section":"orders",
    }
    return render(request, "admin/orders.html", template_vars)


def orders_csv(request):

    orders = Order.objects.all().order_by("-created")

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['id', 'created', 'delivery', 'delivery_provider', 'foodbank', 'country', 'weight', 'calories', 'items', 'cost', 'delivered_cost'])
    for order in orders:
        output.append([order.order_id, order.created, order.delivery_datetime, order.delivery_provider, order.foodbank_name, order.country, order.weight, order.calories, order.no_items, order.cost, order.actual_cost])
    writer.writerows(output)
    return response


def needs(request):

    needs = FoodbankChange.objects.all().order_by("-created")[:1000]

    template_vars = {
        "needs":needs,
        "section":"needs",
    }
    return render(request, "admin/needs.html", template_vars)

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

    text_body = render_to_string("admin/emails/order.txt",{"order":order})
    html_body = render_to_string("admin/emails/order.html",{"order":order})

    send_email(
        to = order.foodbank.notification_email,
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

    template_vars = {
        "foodbank":foodbank,
    }
    return render(request, "admin/foodbank.html", template_vars)


def foodbank_form(request, slug = None):

    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)
        page_title = "Edit %s Food Bank" % (foodbank.name)
    else:
        foodbank = None
        page_title = "New Food Bank"

    if request.POST:
        form = FoodbankForm(request.POST, instance=foodbank)
        if form.is_valid():
            foodbank = form.save()
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
    }
    return render(request, "admin/form.html", template_vars)


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


def fblocation_form(request, slug = None, loc_slug = None):

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
        form = FoodbankLocationForm(instance=foodbank_location, initial={"foodbank":foodbank})

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


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
    
    template_vars = {
        "need":need,
    }
    return render(request, "admin/need.html", template_vars)


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
    need.save()
    return redirect("admin:index")


@require_POST
def need_notifications(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    
    foodbank = need.foodbank

    # Check for foodbank articles
    if foodbank.rss_url:
        foodbank_article_crawl(foodbank)

    # Update tweet time
    need.tweet_sent = datetime.now()
    need.save()

    # Email subscriptions
    subscribers = FoodbankSubscriber.objects.filter(foodbank = foodbank, confirmed = True)
    for subscriber in subscribers:
        post_to_subscriber(need, subscriber)

    return redirect("admin:index")


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
                    latt_long = lat_lng,
                )
                foodbank_location.save()


    return HttpResponse("OK")


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
            need = form.save()
            return redirect("admin:items")
    else:
        form = OrderItemForm(instance=item)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


def politics(request):

    parlcons = ParliamentaryConstituency.objects.all().order_by("name")

    # for parlcon in parlcons:
    #     deferred.defer(parlcon.save)

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


def edit_stats(request):

    all_foodbanks = get_all_foodbanks()
    total_foodbanks = len(all_foodbanks)

    locations = get_all_locations()
    total_locations = len(locations) + total_foodbanks

    newest_edit = Foodbank.objects.all().order_by("-edited")[:1][0].edited
    oldest_edit = Foodbank.objects.all().order_by("edited")[:1][0].edited

    stats = {
        "Total Food Banks":total_foodbanks,
        "Total Locations":total_locations,
        "Newest Edit":newest_edit,
        "Oldest Edit":oldest_edit,
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

    cursor = connection.cursor()
    cursor.execute("SELECT sum(length(regexp_replace(change_text, E'[^\\n]', '', 'g'))) from givefood_foodbankchange")
    need_items = cursor.fetchone()[0]
    cursor.execute("SELECT sum(length(regexp_replace(excess_change_text, E'[^\\n]', '', 'g'))) from givefood_foodbankchange")
    excess_items = cursor.fetchone()[0]

    stats = {
        "Needs":FoodbankChange.objects.count(),
        "Need Items":need_items,
        "Excess Items":excess_items,
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


def resave_orders(request):

    orders = Order.objects.all().order_by("created")
    for order in orders:
        order.save()

    return HttpResponse("OK")


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

    foodbanks = get_all_foodbanks()
    locations = get_all_locations()

    for foodbank in foodbanks:
        try:
            logging.info("trying fb parlcon %s" % foodbank.parliamentary_constituency_slug)
            parlcon = ParliamentaryConstituency.objects.get(slug = foodbank.parliamentary_constituency_slug)
        except ParliamentaryConstituency.DoesNotExist:
            logging.info("adding %s" % foodbank.parliamentary_constituency_slug)
            newparlcon = ParliamentaryConstituency(
                name = foodbank.parliamentary_constituency,
                mp = foodbank.mp,
                mp_party = foodbank.mp_party,
                mp_parl_id = foodbank.mp_parl_id,
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
                mp = location.mp,
                mp_party = location.mp_party,
                mp_parl_id = location.mp_parl_id,
            )
            newparlcon.save()

    return HttpResponse("OK")


def parlcon_loader_geojson(request):

    parlcons = ParliamentaryConstituency.objects.all()

    files = [
        "gb",
        "northernireland",
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
                    latt_long = "%s,%s" % (row[2], row[3]),
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
                pass

    return HttpResponse("OK")


def finder(request):

    place = Place.objects.filter(checked__isnull=True).order_by('?').first()
        
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json?query=food bank&location=%s&radius=5000&region=uk&key=%s" % (place.latt_long, get_cred("gmap_places_key"))
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
            except FoodbankLocation.DoesNotExist:
                matched_foodbank = None

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
            "unsub_key":"UNSUBKEY123456789",
        }
    }

    rendered_template = render_to_string(template_file, template_vars)
    
    if email[-4:] == ".txt":
        rendered_template = "<pre>%s</pre>" % (rendered_template)
    
    return HttpResponse(rendered_template)


def proxy(request):

    url = request.GET.get("url")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
    }
    request = requests.get(url, headers=headers)
    return HttpResponse(request.text)