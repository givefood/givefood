import urllib, json, logging

from google.appengine.api import urlfetch, memcache
from google.appengine.ext import deferred
from django.http import HttpResponse

from givefood.models import Foodbank, FoodbankLocation, ApiFoodbankSearch
from givefood.const.general import FB_MC_KEY, LOC_MC_KEY


def offline_precacher(request):

    all_locations = FoodbankLocation.objects.all()
    memcache.add(LOC_MC_KEY, all_locations, 3600)

    all_foodbanks = Foodbank.objects.all()
    memcache.add(FB_MC_KEY, all_foodbanks, 3600)

    return HttpResponse("OK")


def offline_search_cleanup(request):

    # Remove sample searches
    searches = ApiFoodbankSearch.objects.filter(latt_long = "51.178889,-1.826111")
    for search in searches:
        deferred.defer(search.delete)

    # Remove null island searches
    searches = ApiFoodbankSearch.objects.filter(latt_long = "0,0")
    for search in searches:
        deferred.defer(search.delete)

    # Remove searches that didn't find a food bank within 50000m (50km)
    searches = ApiFoodbankSearch.objects.filter(nearest_foodbank__gt = 50000)
    for search in searches:
        deferred.defer(search.delete)
    
    return HttpResponse("OK")


def offline_search_saver(request):

    searches = ApiFoodbankSearch.objects.all()
    for search in searches:
        deferred.defer(search.save)

    return HttpResponse("OK")


def offline_fire_search_hydrate(request):

    logging.info("Firing search hydration")

    searches = ApiFoodbankSearch.objects.filter(admin_district__isnull = True)[:10000]
    for search in searches:
        deferred.defer(hydrate_search_log, search)
    
    return HttpResponse("OK")


def hydrate_search_log(search):

    logging.info("Hydrating search")

    pc_api_url = "http://postcodes.io/postcodes?lon=%s&lat=%s&radius=10000" % (
        search.long(),
        search.latt(),
    )
    pc_api_result = urlfetch.fetch(pc_api_url)
    if pc_api_result.status_code == 200:
        pc_api_json = json.loads(pc_api_result.content)

        if pc_api_json["result"]:
            search.admin_district = pc_api_json["result"][0]["admin_district"]
            search.admin_ward = pc_api_json["result"][0]["admin_ward"]
            search.lsoa = pc_api_json["result"][0]["lsoa"]
            search.msoa = pc_api_json["result"][0]["msoa"]
            search.parliamentary_constituency = pc_api_json["result"][0]["parliamentary_constituency"]

        search.save()

    return HttpResponse("OK")
