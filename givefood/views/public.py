from django.shortcuts import render_to_response, get_object_or_404
from django.views.decorators.cache import cache_page
from django.shortcuts import redirect
from django.http import HttpResponse

from givefood.models import Foodbank, Order, FoodbankChange
from givefood.func import get_image


# @cache_page(60*15)
def public_index(request):

    total_weight = 0
    total_calories = 0
    total_items = 0

    orders = Order.objects.all()
    for order in orders:
        total_weight = total_weight + order.weight
        total_calories = total_calories + order.calories
        total_items = total_items + order.no_items

    total_weight = float(total_weight) / 1000000
    total_calories = float(total_calories) / 1000000

    no_foodbanks = len(Foodbank.objects.all())

    template_vars = {
        "no_foodbanks":no_foodbanks,
        "total_weight":total_weight,
        "total_calories":total_calories,
        "total_items":total_items,
    }
    return render_to_response("public/index.html", template_vars)


@cache_page(60*60)
def public_product_image(request):

    delivery_provider = request.GET.get("delivery_provider")
    product_name = request.GET.get("product_name")

    url = get_image(delivery_provider,product_name)

    return redirect(url)


def distill_webhook(request):

    new_foodbank_change = FoodbankChange(
        post_text = request.POST,
    )
    new_foodbank_change.save()

    return HttpResponse("OK")
