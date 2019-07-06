from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext

from givefood.models import Foodbank, Order
from givefood.forms import FoodbankForm, OrderForm

def admin_index(request):

    foodbanks = Foodbank.objects.all().order_by("name")
    orders = Order.objects.all().order_by("delivery_date")[:20]

    template_vars = {
        "foodbanks":foodbanks,
        "orders":orders,
    }
    return render_to_response("admin/index.html", template_vars)


def admin_order(request, id):

    order = get_object_or_404(Order, order_id = id)

    template_vars = {
        "order":order,
    }
    return render_to_response("admin/order.html", template_vars)



def admin_order_form(request, id = None):

    if id:
        order = get_object_or_404(Order, order_id = id)
    else:
        order = None

    if request.POST:
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            return HttpResponseRedirect(reverse("admin_index"))
    else:
        form = OrderForm(instance=order)

    template_vars = {
        "form":form,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))


def admin_foodbank_form(request, slug = None):

    if slug:
        foodbank = get_object_or_404(Foodbank, slug = slug)
    else:
        foodbank = None

    if request.POST:
        form = FoodbankForm(request.POST, instance=foodbank)
        if form.is_valid():
            foodbank = form.save()
            return HttpResponseRedirect(reverse("admin_index"))
    else:
        form = FoodbankForm(instance=foodbank)

    template_vars = {
        "form":form,
    }
    return render_to_response("admin/form.html", template_vars, context_instance=RequestContext(request))
