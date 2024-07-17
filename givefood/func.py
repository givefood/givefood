#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, logging, operator, urllib, difflib, requests, feedparser, random
from math import radians, cos, sin, asin, sqrt
from collections import OrderedDict 
from datetime import datetime
from time import mktime
import openai
from bs4 import BeautifulSoup
from urllib.parse import quote

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.cache import cache
from django.contrib.humanize.templatetags.humanize import apnumber

from google.cloud import secretmanager

from givefood.const.general import FB_MC_KEY, LOC_MC_KEY, ITEMS_MC_KEY, PARLCON_MC_KEY, FB_OPEN_MC_KEY, LOC_OPEN_MC_KEY
from givefood.const.parlcon_mp import parlcon_mp
from givefood.const.parlcon_party import parlcon_party


def get_all_foodbanks():

    from givefood.models import Foodbank

    all_foodbanks = cache.get(FB_MC_KEY)
    if all_foodbanks is None:
        all_foodbanks = Foodbank.objects.all()
        cache.set(FB_MC_KEY, all_foodbanks, 3600)
    return all_foodbanks


def get_all_open_foodbanks():

    from givefood.models import Foodbank

    all_open_foodbanks = cache.get(FB_OPEN_MC_KEY)
    if all_open_foodbanks is None:
        all_open_foodbanks = Foodbank.objects.filter(is_closed = False)
        cache.set(FB_OPEN_MC_KEY, all_open_foodbanks, 3600)
    return all_open_foodbanks


def get_all_locations():

    from givefood.models import FoodbankLocation

    all_locations = cache.get(LOC_MC_KEY)
    if all_locations is None:
        all_locations = FoodbankLocation.objects.all()
        cache.set(LOC_MC_KEY, all_locations, 3600)
    return all_locations


def get_all_open_locations():

    from givefood.models import FoodbankLocation

    all_open_locations = cache.get(LOC_OPEN_MC_KEY)
    if all_open_locations is None:
        all_open_locations = FoodbankLocation.objects.filter(is_closed = False)
        cache.set(LOC_OPEN_MC_KEY, all_open_locations, 3600)
    return all_open_locations


def get_all_constituencies():

    from givefood.models import ParliamentaryConstituency

    all_parlcon = cache.get(PARLCON_MC_KEY)
    if all_parlcon is None:
        all_parlcon = ParliamentaryConstituency.objects.defer("boundary_geojson").order_by("name")
        cache.set(PARLCON_MC_KEY, all_parlcon, 3600)
    return all_parlcon


def decache(urls):
    
    # We can only uncache 30 URLs at a time
    url_limit = 30
    url_lists = [urls[x:x+url_limit] for x in range(0, len(urls), url_limit)]

    for urls in url_lists:
        url_params = "&url=".join(urls)
        remote_cache_purge_url = "http://www.givefood.org.uk/purgecache/?url=%s" % (url_params)
        request = requests.get(remote_cache_purge_url)
    cache.clear()
    return True


def diff_html(a,b):

    the_diff = list(difflib.unified_diff(a, b, n=999))

    if the_diff:
        the_diff.pop(0)
        the_diff.pop(0)
        the_diff.pop(0)

    for i in range(len(the_diff)):
        if the_diff[i][:1] == "-":
            the_diff[i] = "<del>%s</del>" % the_diff[i][1:].rstrip()
        if the_diff[i][:1] == "+":
            the_diff[i] = "<ins>%s</ins>" % the_diff[i][1:].rstrip()
            
    return '\n'.join(the_diff) 


def validate_turnstile(turnstile_response):

    turnstile_secret = get_cred("turnstile_secret")
    turnstile_fields = {
        "secret":turnstile_secret,
        "response":turnstile_response,
    }

    turnstile_result = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", turnstile_fields)
    return turnstile_result.json()["success"]


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


def foodbank_article_crawl(foodbank):

    from givefood.models import FoodbankArticle

    logging.info("Scraping %s" % (foodbank.name))

    found_new_article = False

    feed = feedparser.parse(foodbank.rss_url)
    if feed:
        for item in feed["items"]:
            if item.title != "":
                article = FoodbankArticle.objects.filter(url=item.link).first()
                logging.info("Found %s" % (item.title))
                if not article:
                    logging.info("Adding %s" % (item.title))
                    new_article = FoodbankArticle(
                        foodbank = foodbank,
                        title = item.title[0:250],
                        url = item.link,
                        published_date = datetime.fromtimestamp(mktime(item.published_parsed)),
                    )
                    new_article.save()
                    found_new_article = True

    # Update last crawl date
    foodbank.last_crawl = datetime.now()
    if found_new_article:
        foodbank.save(do_decache=True, do_geoupdate=False)
    else:
        foodbank.save(do_decache=False, do_geoupdate=False)

    return True


def parse_tesco_order_text(order_text):

    # 10	Tesco Sliced Carrots In Water 300G	£0.30	£3.00

    order_lines = []

    order_items = order_text.splitlines()
    for order_item_line in order_items:
        order_item_line_bits = re.split(r'\t+', order_item_line)

        order_lines.append({
            "quantity":int(order_item_line_bits[0]),
            "name":order_item_line_bits[1],
            "item_cost":int(float(order_item_line_bits[2].replace(u"\xA3","").replace(".",""))),
            "weight":get_weight(order_item_line_bits[1]),
            "calories":get_calories(
                order_item_line_bits[1],
                get_weight(order_item_line_bits[1]),
                int(order_item_line_bits[0])
            ),
        })

    return order_lines


def parse_old_sainsburys_order_text(order_text):

    # 50 x Hubbard's Foodstore Chicken Curry 392g - Total Price £29.50

    order_lines = []

    order_items = order_text.splitlines()
    for order_item_line in order_items:
        order_item_line_bits = re.split(r'( x | - Total Price )', order_item_line)

        order_lines.append({
            "quantity":int(order_item_line_bits[0]),
            "name":order_item_line_bits[2],
            "item_cost":int(float(order_item_line_bits[4].replace(u"\xA3","").replace(".",""))),
            "weight":get_weight(order_item_line_bits[2]),
            "calories":get_calories(
                order_item_line_bits[2],
                get_weight(order_item_line_bits[2]),
                int(order_item_line_bits[0])
            ),
        })

    return order_lines


def parse_sainsburys_order_text(order_text):

    order_lines = []
    sub_line = 1

    order_items = order_text.splitlines()
    for order_item_line in order_items:
        if sub_line == 1:
            item_name = order_item_line
        if sub_line == 5:
            item_quantity = order_item_line
        if sub_line == 7:
            item_cost = int(order_item_line.replace("£","").replace(".",""))
        if sub_line == 9:
            order_lines.append({
                "quantity":int(item_quantity),
                "name":item_name,
                "item_cost":item_cost,
                "weight":get_weight(item_name),
                "calories":get_calories(
                    item_name,
                    get_weight(item_name),
                    int(item_quantity)
                ),
            })
        if sub_line == 10:
            sub_line = 0

        sub_line = sub_line + 1

    return order_lines


def get_calories(text, weight, quantity):

    from givefood.models import OrderItem

    try:
        order_item = OrderItem.objects.get(name = text)
        calories = order_item.calories
    except OrderItem.DoesNotExist:
        calories = 0

    total_calories = calories * (weight/100) * quantity
    # logging.info("calories: %s, weight: %s, total: %s" % (calories,weight,total_calories))
    return total_calories


def get_weight(text):

    weight = 0

    # 300g (185g*)
    if text[-13:] == " 300g (185g*)":
      weight = 300

    # 400g (184g*)
    if text[-13:] == " 400g (184g*)":
      weight = 400

    # 400g (240g*)
    if text[-13:] == " 400g (240g*)":
      weight = 400

    # 380g (230g*)
    if text[-13:] == " 380g (230g*)":
      weight = 380
    
    # 400g (265g*)
    if text[-13:] == " 400g (265g*)":
      weight = 400

    # 155g (93g*)
    if text[-12:] == " 155g (93g*)":
      weight = 155
      

    # 198g (157g*)
    if text[-13:] == " 198g (157g*)":
      weight = 198

    # 300g (195g*)
    if text[-13:] == " 300g (195g*)":
      weight = 300

    # 560g (360g*)
    if text[-13:] == " 560g (360g*)":
      weight = 560

    # 290g (156g*)
    if text[-13:] == " 290g (156g*)":
      weight = 290

    # 400g (280g*)
    if text[-13:] == " 400g (280g*)":
      weight = 400

    # 120g (90g*)
    if text[-12:] == " 120g (90g*)":
      weight = 120
    
    # 125g (90g*)
    if text[-12:] == " 125g (90g*)":
      weight = 125

    # 4x400g
    if text[-7:] == " 4x400g":
      weight = 1600

    # 3X250ml
    if text[-8:] == " 3X250ml":
      weight = 750

    # 4X125g
    if text[-7:] == " 4X125g":
      weight = 500

    # 2X110g
    if text[-7:] == " 2X110g":
      weight = 220

    # 2X95g
    if text[-6:] == " 2X95g":
      weight = 190

    #2x82g
    if text[-6:] == " 2x82g":
      weight = 164

    # 2x95g
    if text[-6:] == " 2x95g":
      weight = 190

    #20x27g
    if text[-7:] == " 20x27g":
      weight = 540

    #4x22g
    if text[-6:] == " 4x22g":
        weight = 88

    #6x25g
    if text[-6:] == " 6x25g":
        weight = 150

    #24x25g
    if text[-7:] == " 24x25g":
        weight = 600
    
    #5x32g
    if text[-6:] == " 5x32g":
        weight = 160
    
    #12x25g
    if text[-7:] == " 12x25g":
        weight = 300

    # Kilogram
    if text[-2:] == "Kg":
        weight = float(text[-4:].replace("Kg","")) * 1000

    # Kilogram
    if text[-2:] == "kg":
        weight = float(text[-4:].replace("kg","")) * 1000

    # Grams
    if text[-1:] == "G":
      weight = float(remove_letters(text[-4:].replace("G","")))

    # Grams
    if text[-1:] == "g" and not weight:
      weight = float(remove_letters(text[-4:].replace("g","")))

    # 6x1L
    if text[-5:] == " 6x1L":
      weight = 6000

    # 6x1l
    if text[-5:] == " 6X1l":
      weight = 6000

    # Litre
    if text[-6:] == " Litre":
      weight = float(text[-7:].replace(" Litre","")) * 1000

    # L (Litre)
    if text[-1:] == "L" and not weight:
      weight = float(text[-3:].replace("L","")) * 1000

    # Millilitres
    if text[-2:] == "Ml":
      weight = float(text[-5:].replace("Ml",""))

    # Millilitres
    if text[-2:] == "ml":
      weight = float(text[-5:].replace("ml",""))

    # Banana 5-pack
    if text[-6:] == "5 Pack":
      weight = 750

    # 4 X 410G
    if text[-9:] == " 4 X 410G":
      weight = 1640

    if text[-12:] == " 6 X 1 Litre":
        weight = 6000

    if text[-13:] == " 300g (180g*)":
        weight = 300

    if text[-15:] == " 1.13L (2 pint)":
        weight = 1130

    # 325g (260g*)
    if text[-13:] == " 325g (260g*)":
      weight = 325

    # 400g (220g*)
    if text[-13:] == " 400g (220g*)":
      weight = 400

    # 415g (250g Drained)
    if text[-20:] == " 415g (250g Drained)":
      weight = 415

    # 150g (140g*)
    if text[-13:] == " 150g (140g*)":
      weight = 415
      
    ## PIES
    if text == "Tesco Mince Pies 6 Pack":
      weight = 324
    if text == "Tesco Lattice Mince Pies 6 Pack":
      weight = 324

    return weight


def get_all_items():

    from givefood.models import OrderItem

    all_items = cache.get(ITEMS_MC_KEY)
    if all_items is None:
        all_items = OrderItem.objects.all()
        cache.set(ITEMS_MC_KEY, all_items, 3600)
    return all_items


def get_image(delivery_provider, text):

    item_id = ""
    url = None

    if not delivery_provider:
        delivery_provider = "Tesco"

    all_items = get_all_items()

    for item in all_items:
        if item.name == text:
            if delivery_provider == "Sainsbury's":
                if item.sainsburys_image_id:
                    url = "https://assets.sainsburys-groceries.co.uk/gol/%s/image.jpg" % (item.sainsburys_image_id)
            if delivery_provider == "Tesco":
                if item.tesco_image_id:
                    url = "https://digitalcontent.api.tesco.com/v1/media/ghs/snapshotimagehandler_%s.jpeg?w=100" % (item.tesco_image_id)

    if url:
        return url
    else:
        return "/static/img/1px.gif"


def item_class_count(all_items, item_class_items):

    count = 0

    for class_item in item_class_items:
        count = count + all_items.get(class_item, 0)

    return count


def clean_foodbank_need_text(text):

    to_clean = [
        "Things We Need:",
        "Urgently Needed Food Items",
        "Urgently needed food items",
        "Currently Needed Items",
        "Urgently needed items",
        "This week, we would particularly appreciate donations of:",
        "Items required this week",
        "Items that we are currently short of:",
        "Our shopping list",
        "Currently needed items",
        "Most needed items:",
        "Our current most needed list:",
        "Items we are short of",
        "Things we need please",
        "Urgently needed stock items",
        "Urgently Needed Items",
        "Wish list",
        "Most needed food parcel items",
        "Our urgently needed items",
        "Current Pantry Items Needed",
        "Items we urgently need",
        "Most needed items",
        "Most needed food items",
        "Items needed:",
        "We're currently in need of:",
        "Items we have urgent need of",
        "Low stock list",
        "- Updated on Wednesdays -",
        "Most needed food items.",
        "Urgently needed food items - all non-perishable:-",
        "Shopping List",
        "Food items needed",
        "Current Shortages",
        "Most needed food items.",
        "We are short of:",
        "Food items urgently needed right now",
        " Find out what's in a food parcel",
        "Our current needs",
        "(updated weekly)",
        "Items required",
        "Currently needed food items",
        "We are currently shortest of: (Please)",
        "Urgently needed food & toiletry items",
        "Urgently Required",
        "We're running low on",
        "We are short of",
        "You can donate",
        "Always needed",
        "Current Food Needed:",
        "OUR SHOPPING LIST",
        "Urgently Needed",
        "To Maintain Our Stocks",
        "Our current shopping list ....",
        "Current needed items",
        "MOST NEEDED (please avoid donating out of date items)",
        "Less urgent items",
        "Shortages this week",
        "Regulary Needed Items",
    ]

    # Clean out rubbish strings
    for string_to_clean in to_clean:
        text = text.replace(string_to_clean,"")

    # Remove double spaces
    text = text.replace("  "," ")
    
    # Remove whitespace
    text = text.strip()

    # Remove empty lines
    text = "".join([s for s in text.strip().splitlines(True) if s.strip()])

    # Remove whitespace on each line
    text_list = text.splitlines()
    for line_number, line in enumerate(text_list):
        text_list[line_number] = text_list[line_number].strip()
    text = '\n'.join(text_list)

    return text


def is_uk(lat_lng):

    lat = float(lat_lng.split(",")[0])
    lng = float(lat_lng.split(",")[1])

    sw_lat = 49.674
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


def find_locations(lat_lng, quantity = 10, skip_first = False):

    locations = get_all_open_locations()
    foodbanks = get_all_open_foodbanks()

    try:
        lat = float(lat_lng.split(",")[0])
        lng = float(lat_lng.split(",")[1])
    except ValueError:
        return []

    searchable_locations = []

    for location in locations:
        searchable_locations.append({
            "type":"location",
            "name":location.name,
            "lat":location.latt(),
            "lng":location.long(),
            "lat_lng":location.latt_long,
            "address":location.full_address(),
            "postcode":location.postcode,
            "parliamentary_constituency":location.parliamentary_constituency_name,
            "parliamentary_constituency_slug":location.parliamentary_constituency_slug,
            "mp":location.mp,
            "mp_party":location.mp_party,
            "mp_parl_id":location.mp_parl_id,
            "ward":location.ward,
            "district":location.district,
            "phone":location.phone_or_foodbank_phone(),
            "email":location.email_or_foodbank_email(),
            "slug":location.slug,
            "foodbank_slug":location.foodbank_slug,
            "foodbank_name":location.foodbank_name,
            "foodbank_network":location.foodbank_network,
        })

    for foodbank in foodbanks:
        searchable_locations.append({
            "type":"organisation",
            "name":foodbank.name,
            "lat":foodbank.latt(),
            "lng":foodbank.long(),
            "lat_lng":foodbank.latt_long,
            "address":foodbank.full_address(),
            "postcode":foodbank.postcode,
            "parliamentary_constituency":foodbank.parliamentary_constituency_name,
            "parliamentary_constituency_slug":foodbank.parliamentary_constituency_slug,
            "mp":foodbank.mp,
            "mp_party":foodbank.mp_party,
            "mp_parl_id":foodbank.mp_parl_id,
            "ward":foodbank.ward,
            "district":foodbank.district,
            "phone":foodbank.phone_number,
            "email":foodbank.contact_email,
            "slug":foodbank.slug,
            "foodbank_slug":foodbank.slug,
            "foodbank_name":foodbank.name,
            "foodbank_network":foodbank.network,
        })

    for searchable_location in searchable_locations:
        searchable_location["distance_m"] = distance_meters(searchable_location.get("lat"), searchable_location.get("lng"), lat, lng)
        searchable_location["distance_km"] = searchable_location["distance_m"] / 1000
        searchable_location["distance_mi"] = miles(searchable_location.get("distance_m"))

    sorted_searchable_locations = sorted(searchable_locations, key=lambda k: k['distance_m'])

    if skip_first:
        first_item = 1
        quantity = quantity + 1
    else:
        first_item = 0

    return sorted_searchable_locations[first_item:quantity]


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


def remove_letters(the_string):

    the_string = re.sub(r'[a-z]+', '', the_string, re.I) 
    return the_string


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


def pluscode(lat_lng):

    pc_api_url = "https://plus.codes/api?address=%s&ekey=%s" % (urllib.parse.quote(lat_lng), get_cred("gmap_geocode_key"))
    request = requests.get(pc_api_url)
    if request.status_code == 200:
        pc_api_json = request.json()
        return {
            "global":pc_api_json["plus_code"]["global_code"],
            "compound":"%s %s" % (pc_api_json["plus_code"]["local_code"], pc_api_json["plus_code"]["locality"]["local_address"]),
        }
    else:
        return {}


def mp_from_parlcon(parliamentary_constituency):

    return {
        "mp":parlcon_mp.get(parliamentary_constituency),
        "party":parlcon_party.get(parliamentary_constituency),
    }


def mpid_from_name(name):

    if name:
        mpid_url = "https://members-api.parliament.uk/api/Members/Search?Name=%s&House=Commons&IsCurrentMember=true&skip=0&take=20" % (quote(name))
        response = requests.get(mpid_url)
        if response.status_code == 200:
            mpid_api_json = response.json()
            if mpid_api_json["totalResults"] != 0:
                return mpid_api_json["items"][0]["value"]["id"]
    return False


def mp_contact_details(mpid):

    mp_contact_details = {}

    member_url = "https://members-api.parliament.uk/api/Members/%s/" % (mpid)
    member_json = fetch_json(member_url)
    mp_contact_details["display_name"] = member_json["value"]["nameDisplayAs"]

    synopsis_url = "https://members-api.parliament.uk/api/Members/%s/Synopsis" % (mpid)
    synopsis_json = fetch_json(synopsis_url)
    mp_contact_details["synopsis"] = strip_tags(synopsis_json["value"])

    contact_url = "https://members-api.parliament.uk/api/Members/%s/Contact" % (mpid)
    contact_json = fetch_json(contact_url)
    for contact_method in contact_json["value"]:

        if contact_method["type"] == "Parliamentary":
            mp_contact_details["email_parl"] = contact_method["email"]
            address = contact_method["line1"]
            if contact_method["line2"]:
                address = address + "\n" + contact_method["line2"]
            if contact_method["line3"]:
                address = address + "\n" + contact_method["line3"]
            if contact_method["line4"]:
                address = address + "\n" + contact_method["line4"]
            if contact_method["line5"]:
                address = address + "\n" + contact_method["line5"]
            mp_contact_details["address_parl"] = address
            mp_contact_details["postcode_parl"] = contact_method["postcode"]
            mp_contact_details["phone_parl"] = contact_method["phone"]
            if mp_contact_details["address_parl"] and mp_contact_details["postcode_parl"]:
                mp_contact_details["lat_lng_parl"] = geocode("%s\n%s" % (mp_contact_details["address_parl"], mp_contact_details["postcode_parl"]))

        if contact_method["type"] == "Constituency":
            mp_contact_details["email_con"] = contact_method["email"]
            address = contact_method["line1"]
            if contact_method["line2"]:
                address = address + "\n" + contact_method["line2"]
            if contact_method["line3"]:
                address = address + "\n" + contact_method["line3"]
            if contact_method["line4"]:
                address = address + "\n" + contact_method["line4"]
            if contact_method["line5"]:
                address = address + "\n" + contact_method["line5"]
            mp_contact_details["address_con"] = address
            mp_contact_details["postcode_con"] = contact_method["postcode"]
            mp_contact_details["phone_con"] = contact_method["phone"]
            if mp_contact_details["address_con"] and mp_contact_details["postcode_con"]:
                mp_contact_details["lat_lng_con"] = geocode("%s\n%s" % (mp_contact_details["address_con"], mp_contact_details["postcode_con"]))
        
        if contact_method["type"] == "Website":
            mp_contact_details["website"] = contact_method["line1"]
        
        if contact_method["type"] == "Twitter":
            mp_contact_details["twitter"] = contact_method["line1"].replace("https://twitter.com/","")

    return mp_contact_details


def fetch_json(url):

    request = requests.get(url)
    if request.status_code == 200:
        url_result_json = request.json()
        return url_result_json

    return False


def make_url_friendly(url):
    url = url.replace("https://","")
    url = url.replace("http://","")
    if url[-1:] == "/":
        url = url[:-1]
    return url


def make_friendly_phone(phone):
    return phone[0:5] + " " + phone[5:8] + " " + phone[8:]


def make_full_phone(phone):
    if phone.startswith("0"):
        phone = "+44%s" % (phone[1:])
    return phone


def get_cred(cred_name):

    from givefood.models import GfCredential

    try:
        credential = GfCredential.objects.filter(cred_name = cred_name).latest("created")
        return credential.cred_value
    except GfCredential.DoesNotExist:
        return None



def post_to_subscriber(need, subscriber):

    possible_emoji = [
        "🍝",
        "🍲",
        "🍛",
        "🥫",
        "🌽",
        "🥕",
        "🥔",
        "🍚",
        "🍽️",
        "🍴",
        "🥘",
        "🍅",
        "🫘",
        "🫛",
        "🥄",
        "🥣",
        "🥧",
    ]
    emoji = random.choice(possible_emoji)

    subject = "%s %s needs %s items" % (emoji, need.foodbank.full_name(), apnumber(need.no_items()))

    text_body = render_to_string(
        "wfbn/emails/notification.txt",
        {
            "need":need,
            "subscriber":subscriber,
        }
    )
    html_body = render_to_string(
        "wfbn/emails/notification.html",
        {
            "need":need,
            "subscriber":subscriber,
        }
    )

    send_email(
        to = subscriber.email,
        subject = subject,
        body = text_body,
        html_body = html_body,
        is_broadcast = True,
    )


def post_to_email(post, extra = {}, header = None):

    body_str = ""
    fields = post.copy()
    fields.update(extra)

    fields.pop("csrfmiddlewaretoken", None)

    for fieldname, fieldvalue in fields.items():
        body_str += "%s: %s\n" % (fieldname, fieldvalue)

    if header:
        body_str = header + "\n\n" + body_str

    send_email("mail@givefood.org.uk", "Food Bank Data Amendment", body_str)


def send_email(to, subject, body, html_body=None, cc=None, cc_name=None, reply_to=None, reply_to_name=None, is_broadcast=False, bcc=None, bcc_name=None):

    api_url = "https://api.postmarkapp.com/email"
    server_token = get_cred("postmark_server_token")

    request_headers = {
        "X-Postmark-Server-Token": server_token,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if is_broadcast:
        message_stream = "broadcast"
    else:
        message_stream = "outbound"

    # Handle test emails
    if reply_to == "test@example.com":
        to = "mail+testemail@givefood.org.uk"

    request_body = {
        "From": "mail@givefood.org.uk",
        "To": to,
        "Cc": cc,
        "Bcc": bcc,
        "Subject": subject,
        "TextBody": body,
        "HtmlBody": html_body,
        "ReplyTo": reply_to,
        "MessageStream": message_stream
      }

    result = requests.post(
        api_url,
        headers = request_headers,
        json = request_body,
    )

    return True

  
def group_list(lst):
      
    res =  [(el, lst.count(el)) for el in lst]
    return list(OrderedDict(res).items())


def get_secret(secret_id, version_id="latest"):
    
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/givefood/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')


def filter_change_text(change_text, filter_list):

    change_text_list = change_text.splitlines()
    filtered_change_text_list = set()

    for change_text_list_item in change_text_list:
        for filter in filter_list:
            if filter in change_text_list_item:
                filtered_change_text_list.add(change_text_list_item)

    return "\n".join(filtered_change_text_list)


def chatgpt(prompt, temperature):

    openai.api_key = get_cred("openai_api_key")
    response = openai.ChatCompletion.create(
        model = 'gpt-3.5-turbo',
        temperature = temperature,
        messages = [
            {"role": "user", "content": prompt}
        ]
    )
    return response["choices"][0]["message"]["content"]


def htmlbodytext(html):

    soup = BeautifulSoup(html, features="html.parser")
    return soup.body.get_text()