#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
import logging
from urllib.parse import urlparse

import requests
from django_tasks import task

from givefood.utils.cache import get_cred


def validate_turnstile(turnstile_response):
    """Validate a Cloudflare Turnstile CAPTCHA response and return whether it succeeded."""
    turnstile_secret = get_cred("turnstile_secret")
    turnstile_fields = {
        "secret":turnstile_secret,
        "response":turnstile_response,
    }

    turnstile_result = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", turnstile_fields)
    return turnstile_result.json()["success"]


def get_screenshot(url, width=1280, height=1280):
    """Capture a screenshot of a URL using the Cloudflare Browser Rendering API."""
    cf_account_id = get_cred("cf_account_id")
    cf_api_key = get_cred("gf_browser_api")

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % (cf_api_key),
    }
    api_url = "https://api.cloudflare.com/client/v4/accounts/%s/browser-rendering/screenshot" % (cf_account_id)

    response = requests.post(api_url, headers = headers, json = {
        "url": url,
        "viewport": {
            "width": width,
            "height": height,
        },
        "gotoOptions": {
            "waitUntil": "networkidle0",
            "timeout": 45000
        },
        "addStyleTag": [
            {
                "content": "#ccc {display:none};",
            }
        ],
    })
    
    if response.status_code != 200:
        return False
    else:
        return response.content


def get_favicon(url):
    """Fetch a favicon PNG for the given URL via Google's favicon service. Returns image bytes or None."""
    if not url:
        return None
    domain = urlparse(url).netloc
    favicon_url = "https://www.google.com/s2/favicons?domain=%s&sz=64" % (domain)
    response = requests.get(favicon_url, timeout=10)
    if response.status_code != 200:
        return None
    return response.content


def get_translation(language, text, source="en"):
    """Translate text to the given language using the Google Cloud Translation API."""
    key = get_cred("gcp_translate_key")

    translate_url = "https://translation.googleapis.com/language/translate/v2?key=%s" % (key)
    translate_url = "%s&source=%s&target=%s&q=%s&format=text" % (translate_url, source, language, urllib.parse.quote(text))
    request = requests.get(translate_url)
    if request.status_code == 200:
        translate_json = request.json()
        if "data" in translate_json:
            if "translations" in translate_json["data"]:
                if len(translate_json["data"]["translations"]) > 0:
                    return translate_json["data"]["translations"][0]["translatedText"]


@task(queue_name="translate")
def translate_need_async(language, need_id_str):
    """Async task to translate a food bank need into the given language."""
    from givefood.models import FoodbankChange
    need = FoodbankChange.objects.get(need_id_str=need_id_str)
    result = translate_need(language, need)
    return True


def translate_need(language, need):
    """Translate a food bank need's change text and excess text into the given language."""
    from givefood.models import FoodbankChangeTranslation

    FoodbankChangeTranslation.objects.filter(need = need, language = language).delete()
    translated_change = get_translation(language, need.change_text)
    if need.excess_change_text:
        translated_excess = get_translation(language, need.excess_change_text)
    else:
        translated_excess = None

    translated_need = FoodbankChangeTranslation(
        need = need,
        language = language,
        change_text = translated_change,
        excess_change_text = translated_excess,
    )
    translated_need.save()
    return translated_need
