from datetime import datetime, timedelta

from google.appengine.api import mail

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from givefood.const.general import PACKAGING_WEIGHT_PC
from givefood.func import get_all_foodbanks
from givefood.models import Foodbank, Order, OrderLine, FoodbankChange, FoodbankLocation
from givefood.forms import FoodbankForm, OrderForm, NeedForm, FoodbankPoliticsForm, FoodbankLocationForm


def admin_index(request):

    foodbank_sort = request.GET.get("foodbank_sort","last_order")
    VALID_FOODBANK_SORTS = ["last_order", "social_check"]
    if foodbank_sort not in VALID_FOODBANK_SORTS:
        return HttpResponseForbidden()

    if foodbank_sort == "last_order":
        foodbanks = Foodbank.objects.all().order_by("-last_order")[:50]
    else:
        foodbanks = Foodbank.objects.all().order_by("-last_social_media_check")[:50]

    today = datetime.today()
    today_orders = Order.objects.filter(delivery_date = today).order_by("delivery_date")

    # upcoming_order_threshold = datetime.now() - timedelta(days=1)
    upcoming_orders = Order.objects.filter(delivery_date__gt = today).order_by("delivery_date")

    prev_order_threshold = datetime.now() - timedelta(days=1)
    prev_orders = Order.objects.filter(delivery_datetime__lt = prev_order_threshold).order_by("-delivery_datetime")[:40]

    needs = FoodbankChange.objects.all().order_by("-created")[:50]

    template_vars = {
        "foodbanks":foodbanks,
        "today_orders":today_orders,
        "upcoming_orders":upcoming_orders,
        "prev_orders":prev_orders,
        "foodbank_sort":foodbank_sort,
        "needs":needs,
        "section":"home",
    }
    return render_to_response("admin/index.html", template_vars, context_instance=RequestContext(request))


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


def admin_needs(request):

    needs = FoodbankChange.objects.all().order_by("-created")

    template_vars = {
        "needs":needs,
        "section":"needs",
    }
    return render_to_response("admin/needs.html", template_vars, context_instance=RequestContext(request))


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


@require_POST
def admin_foodbank_sm_checked(request, slug):

    foodbank = get_object_or_404(Foodbank, slug = slug)
    foodbank.last_social_media_check = datetime.now()
    foodbank.save()

    return redirect("admin_foodbank", slug = foodbank.slug)


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


def admin_locations(request):

    locations = FoodbankLocation.objects.all().order_by("foodbank_name")

    template_vars = {
        "locations":locations,
        "section":"locations",
    }
    return render_to_response("admin/locations.html", template_vars, context_instance=RequestContext(request))


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

    locations = FoodbankLocation.objects.all()
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
