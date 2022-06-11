import csv
import logging
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

from givefood.const.general import PACKAGING_WEIGHT_PC
from givefood.func import get_all_foodbanks, get_all_locations, get_cred, post_to_facebook, post_to_twitter, post_to_subscriber, send_email
from givefood.models import Foodbank, Order, OrderGroup, OrderLine, OrderItem, FoodbankChange, FoodbankLocation, ApiFoodbankSearch, ParliamentaryConstituency, GfCredential, FoodbankSubscriber
from givefood.forms import FoodbankForm, OrderForm, NeedForm, FoodbankPoliticsForm, FoodbankLocationForm, FoodbankLocationPoliticsForm, OrderGroupForm, ParliamentaryConstituencyForm, OrderItemForm, GfCredentialForm


def index(request):

    foodbanks = Foodbank.objects.all().order_by("-last_order")[:20]

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


def searches(request):

    searches = ApiFoodbankSearch.objects.all().order_by("-created")[:1000]

    template_vars = {
        "searches":searches,
        "section":"searches",
    }

    return render(request, "admin/searches.html", template_vars)


def searches_csv(request):

    searches = ApiFoodbankSearch.objects.all().order_by("-created")[:50000]

    output = []
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['created', 'query_type', 'query', 'nearest_foodbank', 'latt', 'long'])
    for search in searches:
        output.append([search.created, search.query_type, unicode(search.query).encode("utf-8"), search.nearest_foodbank, search.latt(), search.long()])
    writer.writerows(output)
    return response


def search_results(request):

    query = request.GET.get("q")
    foodbank = get_object_or_404(Foodbank, name=query)

    return redirect("admin:foodbank", slug = foodbank.slug)


def foodbanks(request):

    sort_options = [
        "name",
        "last_order",
        "last_need",
        "created",
    ]
    sort = request.GET.get("sort", "name")
    if sort not in sort_options:
        return HttpResponseForbidden()

    sort_string = sort
    if sort != "name":
        sort = "-%s" % (sort)

    foodbanks = Foodbank.objects.all().order_by(sort)

    # for foodbank in foodbanks:
    #     deferred.defer(foodbank.save)

    template_vars = {
        "sort":sort_string,
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
    writer.writerow(['id', 'created', 'delivery', 'delivery_provider', 'foodbank', 'country', 'weight', 'calories', 'items', 'cost'])
    for order in orders:
        output.append([order.order_id, order.created, order.delivery_datetime, order.delivery_provider, order.foodbank_name, order.country, order.weight, order.calories, order.no_items, order.cost])
    writer.writerows(output)
    return response


def needs(request):

    needs = FoodbankChange.objects.all().order_by("-created")[:1000]

    template_vars = {
        "needs":needs,
        "section":"needs",
    }
    return render(request, "admin/needs.html", template_vars)


def needs_csv(request):

    needs = FoodbankChange.objects.all().order_by("-created")

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['id', 'created', 'foodbank', 'needs', 'input_method'])
    for need in needs:
        output.append([need.need_id, need.created, need.foodbank_name, smart_str(need.change_text), need.input_method])
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
    email_body = render_to_string("notification_email.txt",{"order":order})
    send_email(
        to = order.foodbank.notification_email,
        cc = "deliveries@givefood.org.uk",
        subject = "Food donation from Give Food (%s)" % (order.order_id),
        body = email_body,
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
        form = FoodbankForm(instance=foodbank)

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render(request, "admin/form.html", template_vars)


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
    number_subscribers = len(FoodbankSubscriber.objects.filter(foodbank = need.foodbank))
    
    template_vars = {
        "need":need,
        "number_subscribers":number_subscribers,
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

    # Social media
    post_to_facebook(need)
    post_to_twitter(need)

    # Update tweet time
    need.tweet_sent = datetime.now()
    need.save()

    # Email subscriptions
    subscribers = FoodbankSubscriber.objects.filter(foodbank = need.foodbank, confirmed = True)
    for subscriber in subscribers:
        post_to_subscriber(need, subscriber)

    return redirect("admin:index")


def locations(request):

    sort_options = [
        "foodbank_name",
        "name",
        "parliamentary_constituency",
    ]
    sort = request.GET.get("sort", "foodbank_name")
    if sort not in sort_options:
        return HttpResponseForbidden()

    locations = FoodbankLocation.objects.all().order_by(sort)

    # for location in locations:
    #     deferred.defer(location.save)

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


def map(request):

    filter = request.GET.get("filter", "all")

    all_foodbanks = get_all_foodbanks()

    if filter == "all":
        foodbanks = all_foodbanks
    elif filter == "active":
        foodbanks = set()
        all_orders = Order.objects.all()
        for order in all_orders:
            foodbanks.add(order.foodbank)
    else:
        foodbank = get_object_or_404(Foodbank, slug=filter)
        foodbanks = []
        foodbanks.append(foodbank)
        for location in foodbank.locations():
            foodbanks.append(location)

    template_vars = {
        "foodbanks":foodbanks,
        "all_foodbanks":all_foodbanks,
        "filter":filter,
        "section":"map",
    }
    return render(request, "admin/map.html", template_vars)


def stats(request):

    all_foodbanks = get_all_foodbanks()
    total_foodbanks = len(all_foodbanks)
    active_foodbanks = set()

    needs = FoodbankChange.objects.all()
    total_needs = len(needs)
    total_need_items = 0
    for need in needs:
        total_need_items = total_need_items + need.no_items()

    locations = get_all_locations()
    total_locations = len(locations) + total_foodbanks

    total_weight = 0
    total_calories = 0
    total_items = 0
    total_cost = 0

    all_orders = Order.objects.all()
    total_orders = len(all_orders)
    for order in all_orders:
        total_weight = total_weight + order.weight
        total_calories = total_calories + order.calories
        total_items = total_items + order.no_items
        total_cost = total_cost + order.cost
        active_foodbanks.add(order.foodbank_name)

    total_weight = total_weight / 1000
    total_weight_pkg = total_weight * PACKAGING_WEIGHT_PC
    total_cost = float(total_cost) / 100

    total_active_foodbanks = len(active_foodbanks)

    subscriptions = FoodbankSubscriber.objects.filter(confirmed = True)
    total_subscriptions = len(subscriptions)

    template_vars = {
        "total_foodbanks":total_foodbanks,
        "total_active_foodbanks":total_active_foodbanks,
        "total_weight":total_weight,
        "total_calories":total_calories,
        "total_items":total_items,
        "total_orders":total_orders,
        "total_cost":total_cost,
        "total_needs":total_needs,
        "total_need_items":total_need_items,
        "total_weight_pkg":total_weight_pkg,
        "total_locations":total_locations,
        "total_subscriptions":total_subscriptions,
        "section":"stats",
    }
    return render(request, "admin/stats.html", template_vars)


def test_order_email(request, id):

    order = get_object_or_404(Order, order_id = id)

    template_vars = {
        "order":order,
    }
    return render(request, "notification_email.txt", template_vars, content_type='text/plain')


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


@require_POST
def delete_subscription(request):

    email = request.POST.get("email")
    foodbank_slug = request.POST.get("foodbank")
    foodbank = get_object_or_404(Foodbank, slug = foodbank_slug)
    subscriber = get_object_or_404(FoodbankSubscriber, email = email, foodbank = foodbank)
    subscriber.delete()

    return redirect("admin:subscriptions")


def clearcache(request):

    cache.clear()
    return redirect("admin:index")


def proxy(request):

    url = request.GET.get("url")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
    }
    request = requests.get(url, headers=headers)
    return HttpResponse(request.text)