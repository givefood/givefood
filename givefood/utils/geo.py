#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import operator
import urllib

import requests
from math import radians, cos, sin, asin, sqrt
from itertools import chain
from openlocationcode import openlocationcode as olc
from urllib.parse import quote

from django.urls import reverse
from django.db.models import Value
from django_earthdistance.models import EarthDistance, LlToEarth

from givefood.const.general import SITE_DOMAIN
from givefood.utils.cache import get_cred, get_all_open_foodbanks, get_all_constituencies


def geocode(address):

    gmap_geocode_key = get_cred("gmap_geocode_key")

    address = "%s,UK" % (address)
    address_api_url = "https://maps.googleapis.com/maps/api/geocode/json?region=uk&key=%s&address=%s" % (gmap_geocode_key, requests.utils.quote(address))
    request = requests.get(address_api_url)

    if request.status_code == 200:
        try:
            address_result_json = request.json()
            lat_lng = "%s,%s" % (
                address_result_json["results"][0]["geometry"]["location"]["lat"],
                address_result_json["results"][0]["geometry"]["location"]["lng"]
            )
        except:
            lat_lng = "0,0"
    return lat_lng


def get_place_id(address):
    
    gmap_geocode_key = get_cred("gmap_geocode_key")

    address = "%s,UK" % (address)
    address_api_url = "https://maps.googleapis.com/maps/api/geocode/json?region=uk&key=%s&address=%s" % (gmap_geocode_key, requests.utils.quote(address))
    request = requests.get(address_api_url)

    if request.status_code == 200:
        address_result_json = request.json()
        place_id = address_result_json["results"][0]["place_id"]

    return place_id


def photo_from_place_id(place_id, size = 1080):

    from givefood.models import PlacePhoto

    try:
        photo = PlacePhoto.objects.get(place_id = place_id)
    except PlacePhoto.DoesNotExist:
    
        places_key = get_cred("gmap_places_key")
        places_url = "https://maps.googleapis.com/maps/api/place/details/json?place_id=%s&fields=photo&key=%s" % (place_id, places_key)
        places_response = requests.get(places_url)
        places_json = places_response.json()
        photo_ref = places_json.get("result", {}).get("photos", [{}])[0].get("photo_reference", None)

        photo_ref_url = "https://maps.googleapis.com/maps/api/place/photo?maxwidth=%s&photo_reference=%s&key=%s" % (size, photo_ref, places_key)
        photo_ref_response = requests.get(photo_ref_url)
        photo_blob = photo_ref_response.content

        photo = PlacePhoto(
            place_id = place_id,
            blob = photo_blob,
            photo_ref = photo_ref,
        )
        photo.save()

    return photo.blob


def place_has_photo(place_id):
    
    places_key = get_cred("gmap_places_key")
    places_url = "https://maps.googleapis.com/maps/api/place/details/json?place_id=%s&fields=photo&key=%s" % (place_id, places_key)
    places_response = requests.get(places_url)
    places_json = places_response.json()
    photo_ref = places_json.get("result", {}).get("photos", [{}])[0].get("photo_reference", None)

    if photo_ref:
        return True
    else:
        return False


def oc_geocode(address):

    oc_geocode_key = get_cred("oc_geocode_key")

    address_api_url = "https://api.opencagedata.com/geocode/v1/json?q=%s&key=%s" % (urllib.quote(address.encode('utf8')), oc_geocode_key)
    request = requests.get(address_api_url)
    if request.status_code == 200:
        try:
            address_result_json = request.json()
            lat_lng = "%s,%s" % (
                address_result_json["results"][0]["geometry"]["lat"],
                address_result_json["results"][0]["geometry"]["lng"]
            )
        except:
            lat_lng = "0,0"
    return lat_lng


def geojson_dict(geojson):

    geojson = geojson.strip()
    # remove last char if a comma
    if geojson[-1:] == ",":
        geojson = geojson[:-1]
    else:
        geojson = geojson
    return json.loads(geojson)


def is_uk(lat_lng):

    lat = float(lat_lng.split(",")[0])
    lng = float(lat_lng.split(",")[1])

    sw_lat = 49.1
    sw_lng = -14.015517
    ne_lat = 61.061
    ne_lng = 2.0919117

    if lat < sw_lat: return False
    if lng < sw_lng: return False
    if lat > ne_lat: return False
    if lng > ne_lng: return False

    return True


def find_foodbanks(lattlong, quantity = 10, skip_first = False):

    foodbanks = get_all_open_foodbanks()

    latt = float(lattlong.split(",")[0])
    long = float(lattlong.split(",")[1])

    for foodbank in foodbanks:
        foodbank.distance_m = distance_meters(foodbank.latt(), foodbank.long(), latt, long)
        foodbank.distance_mi = miles(foodbank.distance_m)

    sorted_foodbanks = sorted(foodbanks, key=operator.attrgetter('distance_m'))

    if skip_first:
        first_item = 1
        quantity = quantity + 1
    else:
        first_item = 0

    return sorted_foodbanks[first_item:quantity]


def _foodbank_queryset():
    """Build a Foodbank queryset with select_related and conditional translation prefetch."""
    from givefood.models import Foodbank, FoodbankChangeTranslation
    from django.db.models import Prefetch
    from django.utils.translation import get_language

    qs = Foodbank.objects.select_related("latest_need")
    current_language = get_language()
    if current_language and current_language != "en":
        qs = qs.prefetch_related(
            Prefetch("latest_need__foodbankchangetranslation_set", queryset=FoodbankChangeTranslation.objects.filter(language=current_language))
        )
    return qs


def find_locations(lat_lng, quantity = 10, skip_first = False):

    from givefood.models import FoodbankLocation
    from django.db.models import Prefetch

    lat = lat_lng.split(",")[0]
    lng = lat_lng.split(",")[1]

    foodbanks = _foodbank_queryset().filter(is_closed = False).annotate(
        distance=EarthDistance([
            LlToEarth([lat, lng]),
            LlToEarth(['latitude', 'longitude'])
        ])).annotate(type=Value("organisation")).order_by("distance")[:quantity]

    locations = FoodbankLocation.objects.filter(is_closed = False).prefetch_related(
        Prefetch("foodbank", queryset=_foodbank_queryset())
    ).annotate(
        distance=EarthDistance([
            LlToEarth([lat, lng]),
            LlToEarth(['latitude', 'longitude'])
        ])).annotate(type=Value("location")).order_by("distance")[:quantity]

    for foodbank in foodbanks:
        foodbank.distance_mi = miles(foodbank.distance)
        foodbank.distance_km = foodbank.distance / 1000
        foodbank.foodbank_name = foodbank.name
        foodbank.foodbank_slug = foodbank.slug
        foodbank.foodbank_network = foodbank.network
        foodbank.html_url = "%s%s" % (
            SITE_DOMAIN,
            reverse("wfbn:foodbank", kwargs={"slug":foodbank.slug}),
        )
        foodbank.homepage = foodbank.url_with_ref()

    for location in locations:
        location.distance_mi = miles(location.distance)
        location.distance_km = location.distance / 1000
        location.phone_number = location.phone_or_foodbank_phone()
        location.contact_email = location.email_or_foodbank_email()
        location.latest_need = location.foodbank.latest_need
        location.html_url = "%s%s" % (
            SITE_DOMAIN,
            reverse("wfbn:foodbank_location", kwargs={"slug":location.foodbank_slug, "locslug":location.slug}),
        )
        location.homepage = location.foodbank.url_with_ref()

    foodbanksandlocations = list(chain(foodbanks,locations))
    foodbanksandlocations = sorted(foodbanksandlocations, key=lambda k: k.distance)

    if skip_first:
        first_item = 1
        quantity = quantity + 1
    else:
        first_item = 0

    return foodbanksandlocations[first_item:quantity]


def find_locations_by_category(lat_lng, category, max_distance_meters=20000, quantity=20):
    """
    Find food banks and locations near a given lat_lng that need items in a specific category.
    
    Args:
        lat_lng: String in format "lat,lng"
        category: Item category to filter by (e.g. "Tinned Tomatoes", "Pasta")
        max_distance_meters: Maximum distance in meters (default 20km)
        quantity: Maximum number of results to return
    
    Returns:
        List of foodbanks and locations that need items in the specified category,
        ordered by distance
    """
    from givefood.models import Foodbank, FoodbankLocation, FoodbankChangeLine
    from django.db.models import Prefetch, Exists, OuterRef

    lat = lat_lng.split(",")[0]
    lng = lat_lng.split(",")[1]

    # Subquery to check if latest_need has the specified category
    has_category = FoodbankChangeLine.objects.filter(
        need=OuterRef('latest_need'),
        category=category,
        type='need'
    )

    # Base foodbank query with category filter
    foodbanks = _foodbank_queryset().filter(
        is_closed=False,
        latest_need__isnull=False
    ).annotate(
        distance=EarthDistance([
            LlToEarth([lat, lng]),
            LlToEarth(['latitude', 'longitude'])
        ]),
        needs_category=Exists(has_category)
    ).filter(
        distance__lte=max_distance_meters,
        needs_category=True
    ).annotate(type=Value("organisation")).order_by("distance")[:quantity]

    # Get the IDs of foodbanks that need the category
    foodbank_ids_with_category = list(
        Foodbank.objects.filter(
            is_closed=False,
            latest_need__isnull=False
        ).annotate(
            needs_category=Exists(has_category)
        ).filter(
            needs_category=True
        ).values_list('id', flat=True)
    )

    # Query locations whose foodbank needs the category
    # Filter by foodbank_id instead of using Exists subquery to avoid column ambiguity
    locations = FoodbankLocation.objects.filter(
        is_closed=False,
        foodbank_id__in=foodbank_ids_with_category
    ).prefetch_related(
        Prefetch("foodbank", queryset=_foodbank_queryset())
    ).annotate(
        distance=EarthDistance([
            LlToEarth([lat, lng]),
            LlToEarth(['latitude', 'longitude'])
        ])
    ).filter(
        distance__lte=max_distance_meters
    ).annotate(type=Value("location")).order_by("distance")[:quantity]

    # Process foodbanks
    for foodbank in foodbanks:
        foodbank.distance_mi = miles(foodbank.distance)
        foodbank.distance_km = foodbank.distance / 1000
        foodbank.foodbank_name = foodbank.name
        foodbank.foodbank_slug = foodbank.slug
        foodbank.foodbank_network = foodbank.network
        foodbank.html_url = "%s%s" % (
            SITE_DOMAIN,
            reverse("wfbn:foodbank", kwargs={"slug": foodbank.slug}),
        )
        foodbank.homepage = foodbank.url_with_ref()

    # Process locations
    for location in locations:
        location.distance_mi = miles(location.distance)
        location.distance_km = location.distance / 1000
        location.phone_number = location.phone_or_foodbank_phone()
        location.contact_email = location.email_or_foodbank_email()
        location.latest_need = location.foodbank.latest_need
        location.html_url = "%s%s" % (
            SITE_DOMAIN,
            reverse("wfbn:foodbank_location", kwargs={"slug": location.foodbank_slug, "locslug": location.slug}),
        )
        location.homepage = location.foodbank.url_with_ref()

    # Combine and sort by distance
    foodbanksandlocations = list(chain(foodbanks, locations))
    foodbanksandlocations = sorted(foodbanksandlocations, key=lambda k: k.distance)

    return foodbanksandlocations[:quantity]


def find_donationpoints(lat_lng, quantity = 10, foodbank = None):

    from givefood.models import FoodbankLocation, FoodbankDonationPoint
    from django.db.models import Prefetch

    lat = lat_lng.split(",")[0]
    lng = lat_lng.split(",")[1]

    donationpoints = FoodbankDonationPoint.objects.filter(is_closed = False).prefetch_related(
        Prefetch("foodbank", queryset=_foodbank_queryset())
    ).annotate(
    distance=EarthDistance([
        LlToEarth([lat, lng]),
        LlToEarth(['latitude', 'longitude'])
    ])).annotate(type=Value("donationpoint")).order_by("distance")[:quantity]

    location_donationpoints = FoodbankLocation.objects.filter(is_closed = False, is_donation_point = True).prefetch_related(
        Prefetch("foodbank", queryset=_foodbank_queryset())
    ).annotate(
    distance=EarthDistance([
        LlToEarth([lat, lng]),
        LlToEarth(['latitude', 'longitude'])
    ])).annotate(type=Value("location")).order_by("distance")[:quantity]

    if foodbank:
        donationpoints = donationpoints.filter(foodbank = foodbank)
        location_donationpoints = location_donationpoints.filter(foodbank = foodbank)

    donationpoints = list(chain(donationpoints,location_donationpoints))
    donationpoints = sorted(donationpoints, key=lambda k: k.distance)[:quantity]

    for donationpoint in donationpoints:
        if donationpoint.type == "location":
            donationpoint.url = reverse("wfbn:foodbank_location", kwargs={"slug":donationpoint.foodbank_slug, "locslug":donationpoint.slug})
            donationpoint.photo_url = reverse("wfbn-generic:foodbank_location_photo", kwargs={"slug":donationpoint.foodbank_slug, "locslug":donationpoint.slug})
        if donationpoint.type == "donationpoint":
            # Preserve the original homepage URL before overwriting
            donationpoint.homepage_url = donationpoint.url
            donationpoint.url = reverse("wfbn:foodbank_donationpoint", kwargs={"slug":donationpoint.foodbank_slug, "dpslug":donationpoint.slug})
            donationpoint.photo_url = reverse("wfbn-generic:foodbank_donationpoint_photo", kwargs={"slug":donationpoint.foodbank_slug, "dpslug":donationpoint.slug})
        donationpoint.distance_mi = miles(donationpoint.distance)

    return donationpoints


def find_parlcons(lattlong, quantity = 10, skip_first = False):

    parlcons = get_all_constituencies()

    latt = float(lattlong.split(",")[0])
    long = float(lattlong.split(",")[1])

    for parlcon in parlcons:
        parlcon.distance_m = distance_meters(parlcon.latt(), parlcon.long(), latt, long)
        parlcon.distance_mi = miles(parlcon.distance_m)

    sorted_parlcons = sorted(parlcons, key=operator.attrgetter('distance_m'))

    if skip_first:
        first_item = 1
        quantity = quantity + 1
    else:
        first_item = 0

    return sorted_parlcons[first_item:quantity]


def miles(meters):
    return meters*0.000621371192


def distance_meters(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    
    Stolen from https://medium.com/@petehouston/calculate-distance-of-two-locations-on-earth-using-python-1501b1944d97
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    meters = 6367000 * c
    return meters


def validate_postcode(postcode):

    pc_api_url = "https://api.postcodes.io/postcodes/%s/validate" % (urllib.parse.quote(postcode))
    request = requests.get(pc_api_url)
    if request.status_code == 200:
        pc_api_json = request.json()
        return pc_api_json["result"]
    else:
        return False


def admin_regions_from_postcode(postcode):
    pc_api_url = "https://api.postcodes.io/postcodes/%s?decache=true" % (urllib.parse.quote(postcode))
    request = requests.get(pc_api_url)
    if request.status_code == 200:
        pc_api_json = request.json()

        if pc_api_json["result"]["parliamentary_constituency_2024"]:
            parlimentary_constituency = pc_api_json["result"]["parliamentary_constituency_2024"]
        else:
            parlimentary_constituency = pc_api_json["result"]["parliamentary_constituency"]

        regions = {
            "county":pc_api_json["result"]["admin_county"],
            "country":pc_api_json["result"]["country"],
            "parliamentary_constituency":parlimentary_constituency,
            "ward":pc_api_json["result"]["admin_ward"],
            "district":pc_api_json["result"]["admin_district"],
            "lsoa":pc_api_json["result"]["codes"]['lsoa'],
            "msoa":pc_api_json["result"]["codes"]['msoa'],
        }

        return regions
    else:
        return {}


def pluscode(lat_lng, locality=None):
    """
    Generate Plus Codes (Open Location Codes) from latitude/longitude coordinates.
    
    Args:
        lat_lng: A string in the format "latitude,longitude"
        locality: Optional locality name for compound code (e.g., "London, UK")
    
    Returns:
        A dict with 'global' (full Plus Code) and 'compound' (local code + locality) keys,
        or an empty dict if the input is invalid.
    """
    try:
        lat, lng = lat_lng.split(",")
        lat = float(lat.strip())
        lng = float(lng.strip())
        
        # Generate the global Plus Code using openlocationcode library
        global_code = olc.encode(lat, lng)
        
        # Generate a shortened local code for compound code format
        # This creates a 4+2 character code (e.g., "GW6F+M4" from "9C3XGW6F+M4")
        if "+" in global_code:
            suffix = global_code.split("+")[1]
            prefix_end = global_code.index("+")
            short_prefix = global_code[max(0, prefix_end - 4):prefix_end]
            local_code = short_prefix + "+" + suffix
        else:
            local_code = global_code
        
        if locality:
            compound_code = "%s %s" % (local_code, locality)
        else:
            compound_code = local_code
        
        return {
            "global": global_code,
            "compound": compound_code,
        }
    except ValueError:
        return {}


def mpid_from_name(name):

    if name:
        mpid_url = "https://members-api.parliament.uk/api/Members/Search?Name=%s&House=Commons&IsCurrentMember=true&skip=0&take=20" % (quote(name))
        response = requests.get(mpid_url)
        if response.status_code == 200:
            mpid_api_json = response.json()
            if mpid_api_json["totalResults"] != 0:
                return mpid_api_json["items"][0]["value"]["id"]
    return False
