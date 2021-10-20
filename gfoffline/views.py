import urllib, json, logging
import feedparser

from datetime import datetime
from time import mktime

from google.appengine.api import urlfetch, memcache
from google.appengine.ext import deferred
from django.http import HttpResponse
from django.db import IntegrityError

from givefood.models import Foodbank, FoodbankLocation, ApiFoodbankSearch, FoodbankArticle
from givefood.const.general import FB_MC_KEY, LOC_MC_KEY


def precacher(request):

    all_locations = FoodbankLocation.objects.all()
    memcache.add(LOC_MC_KEY, all_locations, 3600)

    all_foodbanks = Foodbank.objects.all()
    memcache.add(FB_MC_KEY, all_foodbanks, 3600)

    return HttpResponse("OK")


def search_cleanup(request):

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


def search_saver(request):

    searches = ApiFoodbankSearch.objects.all()
    for search in searches:
        deferred.defer(search.save)

    return HttpResponse("OK")


def fire_search_hydrate(request):

    logging.info("Firing search hydration")

    searches = ApiFoodbankSearch.objects.filter(admin_district__isnull = True)[:10000]
    for search in searches:
        deferred.defer(hydrate_search_log, search)
    
    return HttpResponse("OK")


def hydrate_search_log(search):

    logging.info("Hydrating search")

    pc_api_url = "https://postcodes.io/postcodes?lon=%s&lat=%s&radius=10000" % (
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


def crawl_articles(request):

    foodbanks_with_rss = Foodbank.objects.filter(rss_url__isnull=False)

    for foodbank in foodbanks_with_rss:
        logging.info("Scraping %s" % (foodbank.name))
        feed = feedparser.parse(foodbank.rss_url)
        if feed:
            for item in feed["items"]:
                try:
                    new_article = FoodbankArticle(
                        foodbank = foodbank,
                        title = item.title,
                        url = item.link,
                        published_date = datetime.fromtimestamp(mktime(item.published_parsed)),
                    )
                    new_article.save()
                except IntegrityError:
                    pass

    return HttpResponse("OK")