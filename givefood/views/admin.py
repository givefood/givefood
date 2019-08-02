from datetime import datetime, timedelta

from google.appengine.api import mail

from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.template.loader import render_to_string
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from givefood.models import Foodbank, Order, OrderLine
from givefood.forms import FoodbankForm, OrderForm

def admin_index(request):

    foodbanks = Foodbank.objects.all().order_by("-last_order")
    total_foodbanks = len(foodbanks)

    total_weight = 0
    total_calories = 0
    total_items = 0

    all_orders = Order.objects.all()
    total_orders = len(all_orders)
    for order in all_orders:
        total_weight = total_weight + order.weight
        total_calories = total_calories + order.calories
        total_items = total_items + order.no_items

    total_weight = total_weight / 1000


    open_order_threshold = datetime.now() - timedelta(days=1)
    open_orders = Order.objects.filter(delivery_datetime__gt = open_order_threshold).order_by("delivery_datetime")

    prev_order_threshold = datetime.now() - timedelta(days=1)
    prev_orders = Order.objects.filter(delivery_datetime__lt = prev_order_threshold).order_by("-delivery_datetime")[:20]

    template_vars = {
        "total_weight":total_weight,
        "total_calories":total_calories,
        "total_items":total_items,
        "total_orders":total_orders,
        "total_foodbanks":total_foodbanks,
        "foodbanks":foodbanks,
        "open_orders":open_orders,
        "prev_orders":prev_orders,
    }
    return render_to_response("admin/index.html", template_vars)


def admin_stats(request):

    orders = Order.objects.all().order_by("-delivery_datetime")

    template_vars = {
        "weeks":weeks,
    }
    return render_to_response("admin/stats.html", template_vars)



def admin_order(request, id):

    order = get_object_or_404(Order, order_id = id)

    template_vars = {
        "order":order,
    }
    return render_to_response("admin/order.html", template_vars, context_instance=RequestContext(request))



def admin_order_form(request, id = None):

    foodbank = None
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

    template_vars = {
        "form":form,
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
        subject="Food donation from Give Food",
        body=email_body)

    order.notification_email_sent = datetime.now()
    order.save()
    return HttpResponse("OK")


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


def admin_map(request):

    foodbanks = Foodbank.objects.all()
    template_vars = {
        "foodbanks":foodbanks,
    }
    return render_to_response("admin/map.html", template_vars, context_instance=RequestContext(request))


def admin_nocalories(request):

    nocalitems = OrderLine.objects.filter(calories = 0)

    template_vars = {
        "nocalitems":nocalitems,
    }
    return render_to_response("admin/nocalories.html", template_vars, context_instance=RequestContext(request))


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
