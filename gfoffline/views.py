import logging

from datetime import datetime, timedelta, timezone

from django.http import HttpResponse
from django.core.cache import cache
from django.apps import apps

from givefood.models import Foodbank, FoodbankLocation, FoodbankSubscriber, FoodbankChange
from givefood.const.general import FB_MC_KEY, LOC_MC_KEY
from givefood.func import oc_geocode, get_all_open_foodbanks, foodbank_article_crawl


def precacher(request):

    all_locations = FoodbankLocation.objects.all()
    cache.set(LOC_MC_KEY, all_locations, 3600)

    all_foodbanks = Foodbank.objects.all()
    cache.set(FB_MC_KEY, all_foodbanks, 3600)

    return HttpResponse("OK")


def fire_oc_geocode(request):

    pass

#     foodbanks = Foodbank.objects.all()
#     for foodbank in foodbanks:
#         deferred.defer(do_oc_geocode, foodbank)

#     locations = FoodbankLocation.objects.all()
#     for location in locations:
#         deferred.defer(do_oc_geocode, location)

#     return HttpResponse("OK")


def do_oc_geocode(foodbank):

    foodbank.latt_long = oc_geocode(foodbank.full_address())
    foodbank.save()


def crawl_articles(request):

    foodbanks_with_rss = Foodbank.objects.filter(rss_url__isnull=False)

    for foodbank in foodbanks_with_rss:
        foodbank_article_crawl(foodbank)


    return HttpResponse("OK")


def cleanup_subs(request):

    unconfirmed_subscribers = FoodbankSubscriber.objects.filter(
        confirmed = False,
        created__lte = datetime.now()-timedelta(days=28),
    )

    for unconfirmed_subscriber in unconfirmed_subscribers:
        unconfirmed_subscriber.delete()

    return HttpResponse("OK")


def days_between_needs(request):

    number_of_needs = 5
    foodbanks = get_all_open_foodbanks()

    for foodbank in foodbanks:

        days_between_needs = 0

        needs = FoodbankChange.objects.filter(foodbank = foodbank).order_by("-created")[:number_of_needs]
        if len(needs) == number_of_needs:
            last_need_date = needs[number_of_needs-1].created
            days_since_earliest_sample_need = (last_need_date - datetime.now(timezone.utc)).days
            days_between_needs = int(-days_since_earliest_sample_need / number_of_needs)

        foodbank.days_between_needs = days_between_needs
        foodbank.save()


    return HttpResponse("OK")


def resaver(request):

    models = [
        "ParliamentaryConstituency",
        "FoodbankGroup",
        "Foodbank",
        "FoodbankLocation", 
        "FoodbankChange",
        "OrderGroup",
        "OrderItem",
        "Order",
        # "OrderLine",
        "FoodbankArticle",
        "GfCredential",
        "FoodbankSubscriber",
        "ConstituencySubscriber",
        "Place",
    ]

    for model in models:
        model_class = apps.get_model("givefood", model)
        instances = model_class.objects.all()
        for instance in instances:
            logging.info("Resaving %s %s" % (model, instance))
            instance.save()

    return HttpResponse("OK")