#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import difflib
from collections import Counter

from bs4 import BeautifulSoup
from furl import furl

from givefood.const.general import QUERYSTRING_RUBBISH


def get_user_ip(request):
    """
    Get the client's IP address from a request.
    Handles proxies by checking headers in the following order:
    1. CF-Connecting-IP (Cloudflare)
    2. X-Forwarded-For (other proxies)
    3. REMOTE_ADDR (direct connection)
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: The client's IP address
    """
    # Cloudflare provides the original client IP in CF-Connecting-IP header
    ip_address = request.META.get("HTTP_CF_CONNECTING_IP")
    
    # Fallback to X-Forwarded-For if not behind Cloudflare
    if not ip_address:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip_address = x_forwarded_for.split(",")[0].strip()
    
    # Final fallback to REMOTE_ADDR
    if not ip_address:
        ip_address = request.META.get("REMOTE_ADDR", "")
    
    return ip_address


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


def text_for_comparison(text):
    if text:
        return text.lower().replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "").replace(".", "")
    else:
        return text


def clean_foodbank_need_text(text):

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

    # UHT miscaptialisation
    text = text.replace("Uht","UHT")

    return text


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


def remove_letters(the_string):
    return re.sub(r'[a-z]+', '', the_string, flags=re.I)


def group_list(lst):

    return list(Counter(lst).items())


def filter_change_text(change_text, filter_list):

    change_text_list = change_text.splitlines()
    filtered_change_text_list = set()

    for change_text_list_item in change_text_list:
        for filter in filter_list:
            if filter in change_text_list_item:
                filtered_change_text_list.add(change_text_list_item)

    return "\n".join(filtered_change_text_list)


def make_url_friendly(url):
    url = url.replace("https://","")
    url = url.replace("http://","")
    url = furl(url)
    url.remove(QUERYSTRING_RUBBISH)
    url = url.url
    if url[-1:] == "/":
        url = url[:-1]
    return url


def make_friendly_phone(phone):
    if phone:
        return phone[0:5] + " " + phone[5:8] + " " + phone[8:]
    else:
        return phone


def make_full_phone(phone):
    if phone:
        if phone.startswith("0"):
            phone = "+44%s" % (phone[1:])
        return phone
    else:
        return phone


def htmlbodytext(html):

    soup = BeautifulSoup(html, features="html.parser")
    if soup.body:
        return soup.body.get_text()
    else:
        return False

