import logging

from datetime import datetime, timedelta, timezone

from django.http import HttpResponse
from django.core.cache import cache
from django.apps import apps

from givefood.models import Foodbank, FoodbankLocation, FoodbankSubscriber, FoodbankChange
from givefood.const.general import FB_MC_KEY, LOC_MC_KEY
from givefood.func import oc_geocode, get_all_open_foodbanks, foodbank_article_crawl, get_place_id, pluscode


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


def pluscodes(request):

    foodbanks = Foodbank.objects.filter(plus_code_global__isnull=True)
    for foodbank in foodbanks:
        pluscodes = pluscode(foodbank.latt_long)
        foodbank.plus_code_compound = pluscodes["compound"]
        foodbank.plus_code_global = pluscodes["global"]
        foodbank.save(do_decache=False, do_geoupdate=False)

    locations = FoodbankLocation.objects.filter(plus_code_global__isnull=True)
    for location in locations:
        pluscodes = pluscode(location.latt_long)
        location.plus_code_compound = pluscodes["compound"]
        location.plus_code_global = pluscodes["global"]
        location.save(do_geoupdate=False)

    return HttpResponse("OK")


def place_ids(request):

    foodbanks = Foodbank.objects.filter(place_id__isnull=True)
    for foodbank in foodbanks:
        address = "%s %s %s" % (
            foodbank.full_name(),
            foodbank.address,
            foodbank.postcode,
        )
        place_id = get_place_id(address)
        foodbank.place_id = place_id
        foodbank.save(do_decache=False, do_geoupdate=False)

    locations = FoodbankLocation.objects.filter(place_id__isnull=True)
    for location in locations:
        address = "%s %s %s" % (
            location.name,
            location.address,
            location.postcode,
        )
        place_id = get_place_id(address)
        location.place_id = place_id
        location.save(do_geoupdate=False, do_foodbank_resave=False)

    return HttpResponse("OK")