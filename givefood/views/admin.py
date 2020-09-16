import csv
import twitter
import logging
from datetime import datetime, timedelta

from libs.beautifulsoup import BeautifulSoup
from djangae.environment import is_production_environment

from google.appengine.api import mail
from google.appengine.api import urlfetch

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.template.loader import render_to_string
from django.template.defaultfilters import truncatechars
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.utils.encoding import smart_str

from givefood.const.general import PACKAGING_WEIGHT_PC
from givefood.func import get_all_foodbanks, get_all_locations
from givefood.models import Foodbank, Order, OrderLine, FoodbankChange, FoodbankLocation, ApiFoodbankSearch, ParliamentaryConstituency
from givefood.forms import FoodbankForm, OrderForm, NeedForm, FoodbankPoliticsForm, FoodbankLocationForm, FoodbankLocationPoliticsForm, ParliamentaryConstituencyForm


def admin_index(request):

    foodbanks = Foodbank.objects.all().order_by("-last_order")[:50]

    today = datetime.today()
    today_orders = Order.objects.filter(delivery_date = today).order_by("delivery_date")

    upcoming_orders = Order.objects.filter(delivery_date__gt = today).order_by("delivery_date")

    prev_order_threshold = datetime.now() - timedelta(days=1)
    prev_orders = Order.objects.filter(delivery_datetime__lt = prev_order_threshold).order_by("-delivery_datetime")[:40]

    needs = FoodbankChange.objects.all().order_by("-created")[:50]

    template_vars = {
        "foodbanks":foodbanks,
        "today_orders":today_orders,
        "upcoming_orders":upcoming_orders,
        "prev_orders":prev_orders,
        "needs":needs,
        "section":"home",
    }
    return render_to_response("admin/index.html", template_vars, context_instance=RequestContext(request))


def admin_searches(request):

    searches = ApiFoodbankSearch.objects.all().order_by("-created")[:1000]

    template_vars = {
        "searches":searches,
        "section":"searches",
    }

    return render_to_response("admin/searches.html", template_vars, context_instance=RequestContext(request))


def admin_searches_csv(request):

    searches = ApiFoodbankSearch.objects.all().order_by("-created")[:20000]

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['created', 'query_type', 'query', 'nearest_foodbank', 'latt', 'long'])
    for search in searches:
        output.append([search.created, search.query_type, search.query, search.nearest_foodbank, search.latt(), search.long()])
    writer.writerows(output)
    return response


def admin_search(request):

    query = request.GET.get("q")
    foodbank = get_object_or_404(Foodbank, name=query)

    return redirect("admin_foodbank", slug = foodbank.slug)


def admin_foodbanks(request):

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

    template_vars = {
        "sort":sort_string,
        "foodbanks":foodbanks,
        "section":"foodbanks",
    }
    return render_to_response("admin/foodbanks.html", template_vars, context_instance=RequestContext(request))


def admin_foodbanks_csv(request):

    foodbanks = Foodbank.objects.all().order_by("-created")

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['name', 'postcode', 'charity_number', 'country', 'last_order', 'last_need', 'no_locations', 'network', 'closed', 'url', 'created', 'modified', 'email'])
    for foodbank in foodbanks:
        output.append([foodbank.name, foodbank.postcode, foodbank.charity_number, foodbank.country, foodbank.last_order, foodbank.last_need, foodbank.no_locations, foodbank.network, foodbank.is_closed, foodbank.url, foodbank.created, foodbank.modified, foodbank.contact_email])
    writer.writerows(output)
    return response


def admin_foodbanks_christmascards(request):

    foodbanks = Foodbank.objects.filter(is_closed = False).order_by("name")

    template_vars = {
        "foodbanks":foodbanks,
    }
    return render_to_response("admin/foodbanks_christmascards.html", template_vars, context_instance=RequestContext(request))


def admin_orders(request):

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
    return render_to_response("admin/orders.html", template_vars, context_instance=RequestContext(request))


def admin_orders_csv(request):

    orders = Order.objects.all().order_by("-created")

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['id', 'created', 'foodbank', 'weight', 'calories', 'items', 'cost'])
    for order in orders:
        output.append([order.order_id, order.created, order.foodbank_name, order.weight, order.calories, order.no_items, order.cost])
    writer.writerows(output)
    return response


def admin_needs(request):

    needs = FoodbankChange.objects.all().order_by("-created")[:100]

    template_vars = {
        "needs":needs,
        "section":"needs",
    }
    return render_to_response("admin/needs.html", template_vars, context_instance=RequestContext(request))


def admin_needs_csv(request):

    needs = FoodbankChange.objects.all().order_by("-created")

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['id', 'created', 'foodbank', 'needs', 'input_method'])
    for need in needs:
        output.append([need.need_id, need.created, need.foodbank_name, smart_str(need.change_text), need.input_method()])
    writer.writerows(output)
    return response


def admin_order(request, id):

    order = get_object_or_404(Order, order_id = id)

    template_vars = {
        "order":order,
    }
    return render_to_response("admin/order.html", template_vars, context_instance=RequestContext(request))


def admin_order_form(request, id = None):

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
            return redirect("admin_order", id = order.order_id)
    else:
        if foodbank:
            form = OrderForm(instance=order, initial={"foodbank":foodbank})
        else:
            form = OrderForm(instance=order)

    if id:
        page_title = "Edit %s - " % str(order.order_id)
    else:
        if foodbank:
            page_title = "New Order for %s - " % foodbank
        else:
            page_title = "New Order - "

    template_vars = {
        "form":form,
        "page_title":page_title,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))


@require_POST
def admin_order_send_notification(request, id = None):

    order = get_object_or_404(Order, order_id = id)
    email_body = render_to_string("admin/notification_email.txt",{"order":order})
    mail.send_mail(
        sender="mail@givefood.org.uk",
        to=order.foodbank.notification_email,
        cc="deliveries@givefood.org.uk",
        subject="Food donation from Give Food (%s)" % (order.order_id),
        body=email_body)

    order.notification_email_sent = datetime.now()
    order.save()
    redir_url = "%s?donenotification=true" % (reverse("admin_order", kwargs={'id': order.order_id}))
    return redirect(redir_url)


def admin_foodbank(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    template_vars = {
        "foodbank":foodbank,
    }
    return render_to_response("admin/foodbank.html", template_vars, context_instance=RequestContext(request))


def admin_foodbank_form(request, slug = None):

    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)
    else:
        foodbank = None

    if request.POST:
        form = FoodbankForm(request.POST, instance=foodbank)
        if form.is_valid():
            foodbank = form.save()
            return redirect("admin_foodbank", slug = foodbank.slug)
    else:
        form = FoodbankForm(instance=foodbank)

    template_vars = {
        "form":form,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))


def admin_foodbank_politics_form(request, slug = None):

    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)
    else:
        foodbank = None

    if request.POST:
        form = FoodbankPoliticsForm(request.POST, instance=foodbank)
        if form.is_valid():
            foodbank = form.save()
            return redirect("admin_foodbank", slug = foodbank.slug)
    else:
        form = FoodbankPoliticsForm(instance=foodbank)

    template_vars = {
        "form":form,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))


def admin_fblocation_form(request, slug = None, loc_slug = None):

    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)
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
            return redirect("admin_foodbank", slug = foodbank_location.foodbank_slug)
    else:
        form = FoodbankLocationForm(instance=foodbank_location, initial={"foodbank":foodbank})

    template_vars = {
        "form":form,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))


def admin_fblocation_politics_edit(request, slug, loc_slug):

    if slug:
        foodbank_location = get_object_or_404(FoodbankLocation, foodbank_slug = slug, slug = loc_slug)
    else:
        foodbank_location = None

    if request.POST:
        form = FoodbankLocationPoliticsForm(request.POST, instance=foodbank_location)
        if form.is_valid():
            foodbank_location = form.save()
            return redirect("admin_foodbank", slug = foodbank_location.foodbank.slug)
    else:
        form = FoodbankLocationPoliticsForm(instance=foodbank_location)

    template_vars = {
        "form":form,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))


def admin_findlocations(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)

    if foodbank.network != "Trussell Trust":
        return HttpResponse("NOT TT")

    locations_url = "%s/locations/" % (foodbank.url)
    locations_result = urlfetch.fetch(locations_url, validate_certificate = False)

    location_soup = BeautifulSoup(locations_result.content)
    headings = location_soup.findAll("h2", attrs={'class':"[ location__heading ]  h3  heading--foodbank"})
    addresses = location_soup.findAll("div", attrs={'class':"[ location__address ]"})

    locations = {}

    i = 0
    while i < len(headings):
        locations[headings[i].string] = addresses[i].findAll("p")[1].text
        i += 1


    template_vars = {
        "foodbank":foodbank,
        "locations":locations,
    }

    return render_to_response("admin/find_locations.html", template_vars, context_instance=RequestContext(request))


def admin_need(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    template_vars = {
        "need":need,
    }
    return render_to_response("admin/need.html", template_vars, context_instance=RequestContext(request))


def admin_need_form(request, id = None):

    if id:
        need = get_object_or_404(FoodbankChange, need_id = id)
    else:
        need = None

    foodbank = None
    foodbank_slug = request.GET.get("foodbank")
    if foodbank_slug:
        foodbank = Foodbank.objects.get(slug=foodbank_slug)

    if request.POST:
        form = NeedForm(request.POST, instance=need)
        if form.is_valid():
            need = form.save()
            return redirect("admin_need", id = need.need_id)
    else:
        if foodbank:
            form = NeedForm(instance=need, initial={"foodbank":foodbank})
        else:
            form = NeedForm(instance=need)

    template_vars = {
        "form":form,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))


@require_POST
def admin_need_delete(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    need.delete()
    return redirect("admin_index")


@require_POST
def admin_need_publish(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)
    need.published = True
    need.save()
    return redirect("admin_index")


@require_POST
def admin_need_tweet(request, id):

    need = get_object_or_404(FoodbankChange, need_id = id)

    api = twitter.Api(consumer_key='fG7cu74X0VvHr4nXNCU8tlw33',
                          consumer_secret='EzCwDhIsAWZP5HCuLmBLKUKnmv3AsKmuGpUcMLUkytl1s04UbZ',
                          access_token_key='1275779682726707202-eKyLOrIhfGqkSGAT4XiycGOb7jgKOo',
                          access_token_secret='LdOS2wWrm5Um9RLuwXWS5oNlmrPlez9Y1V1BO4dTqImM2')

    if need.foodbank.twitter_handle:
        fb_twitter_handle = " @%s" % (need.foodbank.twitter_handle)
    else:
        fb_twitter_handle = ""

    tweet = "%s Food Bank%s is requesting the donation of:\n\n%s https://www.givefood.org.uk/needs/at/%s/" % (
        need.foodbank_name,
        fb_twitter_handle,
        truncatechars(need.change_text, 150),
        need.foodbank_name_slug()
    )

    if is_production_environment():
        status = api.PostUpdate(tweet, latitude=need.foodbank.latt(), longitude=need.foodbank.long())
    else:
        # status = api.PostUpdate(tweet)
        logging.info(tweet)

    return redirect("admin_index")


def admin_locations(request):

    sort_options = [
        "foodbank_name",
        "name",
        "parliamentary_constituency",
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
    return render_to_response("admin/locations.html", template_vars, context_instance=RequestContext(request))


def admin_politics(request):

    foodbanks = get_all_foodbanks()
    locations = FoodbankLocation.objects.all()
    parlcons = ParliamentaryConstituency.objects.all().order_by("name")

    template_vars = {
        "foodbanks":foodbanks,
        "locations":locations,
        "parlcons":parlcons,
        "section":"politics",
    }
    return render_to_response("admin/politics.html", template_vars, context_instance=RequestContext(request))


def admin_politics_csv(request):

    foodbanks = get_all_foodbanks()
    locations = FoodbankLocation.objects.all()

    output = []
    response = HttpResponse (content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(['constituency', 'mp', 'mp_party', 'mp_parl_id'])
    for foodbank in foodbanks:
        output.append([foodbank.parliamentary_constituency, foodbank.mp, foodbank.mp_party, foodbank.mp_parl_id])
    for location in locations:
        output.append([location.parliamentary_constituency, location.mp, location.mp_party, location.mp_parl_id])
    writer.writerows(output)
    return response


def admin_map(request):

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
    return render_to_response("admin/map.html", template_vars, context_instance=RequestContext(request))


def admin_stats(request):

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
        "section":"stats",
    }
    return render_to_response("admin/stats.html", template_vars, context_instance=RequestContext(request))


def admin_test_order_email(request, id):

    order = get_object_or_404(Order, order_id = id)

    template_vars = {
        "order":order,
    }
    return render_to_response("admin/notification_email.txt", template_vars, content_type='text/plain')


def admin_resave_orders(request):

    orders = Order.objects.all().order_by("created")
    for order in orders:
        order.save()

    return HttpResponse("OK")


def admin_parlcon_form(request, slug = None):

    if slug:
        parlcon = get_object_or_404(ParliamentaryConstituency, slug = slug)
    else:
        parlcon = None

    if request.POST:
        form = ParliamentaryConstituencyForm(request.POST, instance=parlcon)
        if form.is_valid():
            foodbank = form.save()
            return redirect("admin_politics")
    else:
        form = ParliamentaryConstituencyForm(instance=parlcon)

    template_vars = {
        "form":form,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))


def admin_parlcon_loader(request):

    foodbanks = get_all_foodbanks()
    locations = FoodbankLocation.objects.all()

    for foodbank in foodbanks:
        try:
            parlcon = ParliamentaryConstituency.objects.get(slug = foodbank.parliamentary_constituency_slug)
        except ParliamentaryConstituency.DoesNotExist:
            newparlcon = ParliamentaryConstituency(
                name = foodbank.parliamentary_constituency,
                mp = foodbank.mp,
                mp_party = foodbank.mp_party,
                mp_parl_id = foodbank.mp_parl_id,
            )
            newparlcon.save()


    for location in locations:
        try:
            parlcon = ParliamentaryConstituency.objects.get(slug = location.parliamentary_constituency_slug)
        except ParliamentaryConstituency.DoesNotExist:
            newparlcon = ParliamentaryConstituency(
                name = location.parliamentary_constituency,
                mp = location.mp,
                mp_party = location.mp_party,
                mp_parl_id = location.mp_parl_id,
            )
            newparlcon.save()

    return HttpResponse("OK")