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

