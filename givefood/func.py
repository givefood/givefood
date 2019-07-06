#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, logging
from givefood.const.calories import CALORIES


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
            "calories":get_calories(order_item_line_bits[1], get_weight(order_item_line_bits[1])),
        })

    return order_lines


def get_calories(text, weight):

    calories = CALORIES.get(text, 0)
    total_calories = calories * (weight/10)
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
      weight = float(text[-4:].replace("L","")) * 1000

    # Millilitres
    if text[-2:] == "Ml":
      weight = float(text[-5:].replace("Ml",""))

    return weight
