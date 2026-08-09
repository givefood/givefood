#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests

from django.core.cache import cache
from django_tasks import task

from givefood.const.general import FB_MC_KEY, LOC_MC_KEY, PARLCON_MC_KEY, FB_OPEN_MC_KEY, LOC_OPEN_MC_KEY, CRED_MC_KEY_PREFIX, STATS_MC_KEY


def get_slug_redirects():
    """Get slug redirects from database with caching."""
    from django.db.utils import ProgrammingError, OperationalError
    
    cache_key = 'slug_redirects_dict'
    redirects = cache.get(cache_key)
    
    if redirects is None:
        # Import here to avoid circular imports at module load time
        from givefood.models import SlugRedirect
        
        try:
            # Fetch all redirects from database
            slug_redirects = SlugRedirect.objects.all().values_list('old_slug', 'new_slug')
            redirects = dict(slug_redirects)
            
            # Cache for 1 hour (3600 seconds)
            cache.set(cache_key, redirects, 3600)
        except (ProgrammingError, OperationalError):
            # If table doesn't exist yet (e.g., during initial migration), return empty dict
            redirects = {}
    
    return redirects


def get_all_foodbanks():
    """Return all Foodbank objects, using a cached queryset."""
    from givefood.models import Foodbank

    all_foodbanks = cache.get(FB_MC_KEY)
    if all_foodbanks is None:
        all_foodbanks = Foodbank.objects.all()
        cache.set(FB_MC_KEY, all_foodbanks, 3600)
    return all_foodbanks


def get_all_open_foodbanks():
    """Return all open Foodbank objects, using a cached queryset."""
    from givefood.models import Foodbank

    all_open_foodbanks = cache.get(FB_OPEN_MC_KEY)
    if all_open_foodbanks is None:
        all_open_foodbanks = Foodbank.objects.filter(is_closed = False)
        cache.set(FB_OPEN_MC_KEY, all_open_foodbanks, 3600)
    return all_open_foodbanks


def get_all_locations():
    """Return all FoodbankLocation objects, using a cached queryset."""
    from givefood.models import FoodbankLocation

    all_locations = cache.get(LOC_MC_KEY)
    if all_locations is None:
        all_locations = FoodbankLocation.objects.all()
        cache.set(LOC_MC_KEY, all_locations, 3600)
    return all_locations


def get_all_open_locations():
    """Return all open FoodbankLocation objects, using a cached queryset."""
    from givefood.models import FoodbankLocation

    all_open_locations = cache.get(LOC_OPEN_MC_KEY)
    if all_open_locations is None:
        all_open_locations = FoodbankLocation.objects.filter(is_closed = False)
        cache.set(LOC_OPEN_MC_KEY, all_open_locations, 3600)
    return all_open_locations


def get_site_stats():
    """
    Headline counts for the homepage, its markdown twin and llms.txt.

    All three wanted the same numbers and each computed them itself, nine
    queries a time, over the largest tables in the schema -- FoodbankChangeLine
    alone holds a row per item per need, and the meals figure sums calories
    across every order ever placed. Being behind cache_page did not save much:
    that varies by language and by worker, so the same nine queries ran again
    for every translation of every one of the three pages.

    The Foodbank and FoodbankLocation counts are gathered per table with
    conditional aggregates, so what was nine queries -- one of them run twice --
    is now five.
    """
    from django.db.models import Count, Q, Sum

    from givefood.models import (
        Foodbank, FoodbankChangeLine, FoodbankDonationPoint, FoodbankLocation,
        Order,
    )

    stats = cache.get(STATS_MC_KEY)
    if stats is not None:
        return stats

    foodbanks = Foodbank.objects.aggregate(
        total = Count("pk"),
        delivering = Count("pk", filter = ~Q(delivery_address = "")),
        not_administrative = Count("pk", filter = ~Q(address_is_administrative = True)),
    )
    locations = FoodbankLocation.objects.aggregate(
        total = Count("pk"),
        donation_points = Count("pk", filter = Q(is_donation_point = True)),
    )
    donation_points = FoodbankDonationPoint.objects.count()
    calories = Order.objects.aggregate(Sum("calories"))["calories__sum"] or 0

    stats = {
        "foodbanks": foodbanks["total"] + foodbanks["delivering"] + locations["total"],
        "donationpoints": (
            donation_points
            + foodbanks["not_administrative"]
            + foodbanks["delivering"]
            + locations["donation_points"]
        ),
        # One row per item per need. md_index counted FoodbankChange here, which
        # is one row per shopping list, so it reported a much smaller number
        # under the same "Items requested" label as the homepage.
        "items": FoodbankChangeLine.objects.count(),
        "meals": int(calories / 500),
    }

    cache.set(STATS_MC_KEY, stats, 3600)
    return stats


def get_all_constituencies():
    """Return all ParliamentaryConstituency objects ordered by name, using a cached queryset."""
    from givefood.models import ParliamentaryConstituency

    all_parlcon = cache.get(PARLCON_MC_KEY)
    if all_parlcon is None:
        all_parlcon = ParliamentaryConstituency.objects.defer("boundary_geojson").order_by("name")
        cache.set(PARLCON_MC_KEY, all_parlcon, 3600)
    return all_parlcon


@task(queue_name="decache", priority=20)
def decache_async(urls = None, prefixes = None):
    """Async task to purge URLs and prefixes from the Cloudflare and local caches."""
    decache(urls = urls, prefixes = prefixes)
    return True


def decache(urls = None, prefixes = None):
    """Purge specific URLs and/or URL prefixes from the Cloudflare CDN cache and clear the local cache."""
    domain = "www.givefood.org.uk"

    cf_zone_id = get_cred("cf_zone_id")
    cf_api_key = get_cred("cf_api_key")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % (cf_api_key),
    }
    api_url = "https://api.cloudflare.com/client/v4/zones/%s/purge_cache" % (cf_zone_id)

    if prefixes:
        full_prefixes = []
        for prefix in prefixes:
            full_prefixes.append("%s%s" % (domain, prefix))

        requests.post(api_url, headers = headers, json = {
            "prefixes": full_prefixes,
        })
    
    if urls:
        full_urls = []
        for url in urls:
            full_urls.append("%s%s%s" % ("https://", domain, url))

        # We can only uncache 30 URLs at a time
        url_limit = 30
        url_lists = [full_urls[x:x+url_limit] for x in range(0, len(full_urls), url_limit)]

        for urls in url_lists:
            requests.post(api_url, headers = headers, json = {
                "files": urls,
            })

    cache.clear()
    return True


def get_cred(cred_name):
    """Retrieve a credential value by name from the database, using a cached lookup."""
    from givefood.models import GfCredential

    cache_key = f"{CRED_MC_KEY_PREFIX}{cred_name}"
    cred_value = cache.get(cache_key)
    
    if cred_value is None:
        try:
            credential = GfCredential.objects.filter(cred_name = cred_name).latest("created")
            cred_value = credential.cred_value
            # Cache for 1 hour (3600 seconds)
            cache.set(cache_key, cred_value, 3600)
        except GfCredential.DoesNotExist:
            cred_value = None
    
    return cred_value


def delete_all_cached_credentials():
    """Delete all cached credentials from the cache."""
    from givefood.models import GfCredential
    
    # Get all unique credential names
    cred_names = GfCredential.objects.values_list('cred_name', flat=True).distinct()
    
    # Delete each cached credential
    for cred_name in cred_names:
        cache_key = f"{CRED_MC_KEY_PREFIX}{cred_name}"
        cache.delete(cache_key)
    
    return True
