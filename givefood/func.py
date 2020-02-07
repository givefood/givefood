#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, logging, operator
from math import radians, cos, sin, asin, sqrt

from google.appengine.api import memcache

from givefood.const.calories import CALORIES
from givefood.const.tesco_image_ids import TESCO_IMAGE_IDS


def get_all_foodbanks():

    from models import Foodbank

    all_foodbanks = memcache.get("all_foodbanks")
    if all_foodbanks is None:
        all_foodbanks = Foodbank.objects.all()
        memcache.add("all_foodbanks", all_foodbanks, 3600)
    return all_foodbanks


def parse_order_text(order_text):

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


def get_calories(text, weight, quantity):

    calories = CALORIES.get(text, 0)
    total_calories = calories * (weight/100) * quantity
    # logging.info("calories: %s, weight: %s, total: %s" % (calories,weight,total_calories))
    return total_calories

def get_weight(text):

    weight = 0

    # Kilogram
    if text[-2:] == "Kg":
        weight = float(text[-4:].replace("Kg","")) * 1000

    # Grams
    if text[-1:] == "G":
      weight = float(text[-4:].replace("G",""))

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

    # 3X250ml
    if text[-8:] == " 3X250ml":
      weight = 750

    # 2X110g
    if text[-7:] == " 2X110g":
      weight = 220

    # 2X95g
    if text[-6:] == " 2X95g":
      weight = 190

    # 4 X 410G
    if text[-9:] == " 4 X 410G":
      weight = 1640

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
    ]

    for string_to_clean in to_clean:
        text = text.replace(string_to_clean,"")
    text = text.strip()
    return text


def find_foodbanks(lattlong, quantity = 10):

    from givefood.models import Foodbank
    foodbanks = Foodbank.objects.filter(is_closed = False)

    latt = float(lattlong.split(",")[0])
    long = float(lattlong.split(",")[1])

    for foodbank in foodbanks:
        foodbank.distance_m = distance_meters(foodbank.latt(), foodbank.long(), latt, long)
        foodbank.distance_mi = miles(foodbank.distance_m)

    sorted_foodbanks = sorted(foodbanks, key=operator.attrgetter('distance_m'))

    return sorted_foodbanks[:quantity]


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


def lattlong_from_postcode(postcode):
    pass
