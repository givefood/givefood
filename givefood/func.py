#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, logging
from givefood.const.calories import CALORIES
from givefood.const.tesco_image_ids import TESCO_IMAGE_IDS


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
