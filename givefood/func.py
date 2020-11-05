#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, logging, operator, json, urllib
from math import radians, cos, sin, asin, sqrt

from google.appengine.api import memcache
from google.appengine.api import urlfetch

from givefood.const.calories import CALORIES
from givefood.const.tesco_image_ids import TESCO_IMAGE_IDS
from givefood.const.general import FB_MC_KEY, LOC_MC_KEY
from givefood.const.parlcon_mp import parlcon_mp
from givefood.const.parlcon_party import parlcon_party


def get_all_foodbanks():

    from models import Foodbank

    all_foodbanks = memcache.get(FB_MC_KEY)
    if all_foodbanks is None:
        all_foodbanks = Foodbank.objects.all()
        memcache.add(FB_MC_KEY, all_foodbanks, 3600)
    return all_foodbanks


def get_all_open_foodbanks():

    foodbanks = get_all_foodbanks()
    foodbanks = list(foodbanks)
    for foodbank in foodbanks:
        if foodbank.is_closed:
            foodbanks.remove(foodbank)

    return foodbanks


def get_all_locations():

    from models import FoodbankLocation

    all_locations = memcache.get(LOC_MC_KEY)
    if all_locations is None:
        all_locations = FoodbankLocation.objects.all()
        memcache.add(LOC_MC_KEY, all_locations, 3600)
    return all_locations


def get_all_constituencies():

    foodbanks = get_all_foodbanks()
    locations = get_all_locations()
    constituencies = set()

    for foodbank in foodbanks:
        if foodbank.parliamentary_constituency:
            constituencies.add(foodbank.parliamentary_constituency)

    for location in locations:
        if location.parliamentary_constituency:
            constituencies.add(location.parliamentary_constituency)

    constituencies = sorted(constituencies)

    return constituencies


def geocode(address):

    address_api_url = "https://maps.googleapis.com/maps/api/geocode/json?key=AIzaSyCgc052pX0gMcxOF1PKexrTGTu8qQIIuRk&address=%s" % (urllib.quote(address))
    address_api_result = urlfetch.fetch(address_api_url)
    if address_api_result.status_code == 200:
        try:
            address_result_json = json.loads(address_api_result.content)
            lattlong = "%s,%s" % (
                address_result_json["results"][0]["geometry"]["location"]["lat"],
                address_result_json["results"][0]["geometry"]["location"]["lng"]
            )
        except:
            lattlong = "0,0"
    return lattlong


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


def parse_sainsburys_order_text(order_text):

    # 50 x Hubbard's Foodstore Chicken Curry 392g - Total Price £29.50
    # 25 x Hubbard's Foodstore Strawberry Jam 454g - Total Price £7.00

    order_lines = []

    order_items = order_text.splitlines()
    for order_item_line in order_items:
        order_item_line_bits = re.split(r'( x | - Total Price )', order_item_line)

        logging.info(order_item_line)
        logging.info("Got bits %s, %s, %s" % (order_item_line_bits[0], order_item_line_bits[1], order_item_line_bits[2]))

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


def get_calories(text, weight, quantity):

    calories = CALORIES.get(text, 0)
    total_calories = calories * (weight/100) * quantity
    # logging.info("calories: %s, weight: %s, total: %s" % (calories,weight,total_calories))
    return total_calories


def get_weight(text):

    weight = 0

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

    # 2x95g
    if text[-6:] == " 2x95g":
      weight = 190

    # Kilogram
    if text[-2:] == "Kg":
        weight = float(text[-4:].replace("Kg","")) * 1000

    # Grams
    if text[-1:] == "G":
      weight = float(text[-4:].replace("G",""))

    # Grams
    if text[-1:] == "g" and not weight:
      weight = float(text[-4:].replace("g",""))

    # Litre
    if text[-6:] == " Litre":
      weight = float(text[-7:].replace(" Litre","")) * 1000

    # L (Litre)
    if text[-1:] == "L":
      weight = float(text[-3:].replace("L","")) * 1000

    # Millilitres
    if text[-2:] == "Ml":
      weight = float(text[-5:].replace("Ml",""))

    # Banana 5-pack
    if text[-6:] == "5 Pack":
      weight = 750

    # 4 X 410G
    if text[-9:] == " 4 X 410G":
      weight = 1640

    if text[-12:] == " 6 X 1 Litre":
        weight = 6000

    ## PIES
    if text == "Tesco Mince Pies 6 Pack":
      weight = 324
    if text == "Tesco Lattice Mince Pies 6 Pack":
      weight = 324

    return weight


def get_image(delivery_provider, text):

    url = None

    if not delivery_provider:
        delivery_provider = "Tesco"

    if delivery_provider == "Tesco":
        image_id = TESCO_IMAGE_IDS.get(text)
        if image_id:
            url = "https://digitalcontent.api.tesco.com/v1/media/ghs/snapshotimagehandler_%s.jpeg?w=100" % (image_id)

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
        "Urgently needed food items",
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
        "Food Items",
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
    ]

    for string_to_clean in to_clean:
        text = text.replace(string_to_clean,"")
    text = text.strip()
    return text


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


def find_locations(lattlong, quantity = 10, skip_first = False):

    locations = get_all_locations()
    foodbanks = get_all_open_foodbanks()

    latt = float(lattlong.split(",")[0])
    long = float(lattlong.split(",")[1])

    searchable_locations = []

    for location in locations:
        searchable_locations.append({
            "type":"location",
            "name":location.full_name(),
            "lat":location.latt(),
            "lng":location.long(),
            "lat_lng":location.latt_long,
            "needs":location.latest_need(),
            "address":location.full_address(),
            "postcode":location.postcode,
            "parliamentary_constituency":location.parliamentary_constituency,
            "parliamentary_constituency_slug":location.parliamentary_constituency_slug,
            "mp":location.mp,
            "mp_party":location.mp_party,
            "mp_parl_id":location.mp_parl_id,
            "ward":location.ward,
            "district":location.district,
        })

    for foodbank in foodbanks:
        searchable_locations.append({
            "type":"organisation",
            "name":foodbank.name,
            "lat":foodbank.latt(),
            "lng":foodbank.long(),
            "lat_lng":foodbank.latt_long,
            "needs":foodbank.latest_need(),
            "address":foodbank.full_address(),
            "postcode":foodbank.postcode,
            "parliamentary_constituency":foodbank.parliamentary_constituency,
            "parliamentary_constituency_slug":foodbank.parliamentary_constituency_slug,
            "mp":foodbank.mp,
            "mp_party":foodbank.mp_party,
            "mp_parl_id":foodbank.mp_parl_id,
            "ward":foodbank.ward,
            "district":foodbank.district,
        })

    for searchable_location in searchable_locations:
        searchable_location["distance_m"] = distance_meters(searchable_location.get("lat"), searchable_location.get("lng"), latt, long)
        searchable_location["distance_mi"] = miles(searchable_location.get("distance_m"))
        logging.info(searchable_location)

    sorted_searchable_locations = sorted(searchable_locations, key=lambda k: k['distance_m'])

    if skip_first:
        first_item = 1
        quantity = quantity + 1
    else:
        first_item = 0

    return sorted_searchable_locations[first_item:quantity]


def miles(meters):
    return meters*0.000621371192


def distance_meters(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
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
    pc_api_url = "https://api.postcodes.io/postcodes/%s" % (urllib.quote(postcode))
    pc_api_result = urlfetch.fetch(pc_api_url)
    if pc_api_result.status_code == 200:
        pc_api_json = json.loads(pc_api_result.content)

        return {
            "county":pc_api_json["result"]["admin_county"],
            "parliamentary_constituency":pc_api_json["result"]["parliamentary_constituency"],
            "ward":pc_api_json["result"]["admin_ward"],
            "district":pc_api_json["result"]["admin_district"],
        }
    else:
        return {}


def mp_from_parlcon(parliamentary_constituency):

    return {
        "mp":parlcon_mp.get(parliamentary_constituency),
        "party":parlcon_party.get(parliamentary_constituency),
    }


def mpid_from_name(name):

    logging.info("getting mp name %s" % (name))

    if name:
        mpid_url = "https://members-api.parliament.uk/api/Members/Search?Name=%s&House=Commons&IsCurrentMember=true&skip=0&take=20" % (urllib.quote(name))
        mpid_api_result = urlfetch.fetch(mpid_url)
        if mpid_api_result.status_code == 200:
            mpid_api_json = json.loads(mpid_api_result.content)
            if mpid_api_json["totalResults"] != 0:
                logging.info("getting got id %s" % (mpid_api_json["items"][0]["value"]["id"]))
                return mpid_api_json["items"][0]["value"]["id"]
    return False


def lattlong_from_postcode(postcode):
    pass


def make_url_friendly(url):
    url = url.replace("https://","")
    url = url.replace("http://","")
    return url
