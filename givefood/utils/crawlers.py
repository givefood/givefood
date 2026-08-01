#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import logging

import requests
from datetime import datetime
from time import mktime, sleep
import feedparser

from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django_tasks import task

from givefood.const.general import BOT_USER_AGENT
from givefood.utils.cache import get_cred
from givefood.utils.general import get_markdown
from givefood.utils.text import clean_foodbank_need_text, need_items_key, htmlbodytext
from givefood.utils.ai import openrouter


def foodbank_article_crawl(foodbank, crawl_set = None):
    """Crawl a food bank's RSS feed for new articles and save any that are found."""
    from givefood.models import FoodbankArticle, CrawlItem

    crawl_item = CrawlItem(
        foodbank = foodbank,
        crawl_type = "article",
        crawl_set = crawl_set,
        url = foodbank.rss_url,
    )
    crawl_item.save()

    found_new_article = False

    feedparser.USER_AGENT = BOT_USER_AGENT
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
    foodbank.last_crawl = timezone.now()
    if found_new_article:
        foodbank.save(do_decache=True, do_geoupdate=False)
    else:
        foodbank.save(do_decache=False, do_geoupdate=False)

    crawl_item.finish = timezone.now()
    crawl_item.save()

    return True


@task(priority=30)
def foodbank_article_crawl_async(foodbank_slug):
    """Async task to crawl a food bank's RSS feed for new articles."""
    from givefood.models import Foodbank
    foodbank = Foodbank.objects.get(slug=foodbank_slug)
    foodbank_article_crawl(foodbank)
    return True


def foodbank_charity_crawl(foodbank, crawl_set = None):
    """
    Crawl charity details for an individual food bank from the appropriate
    charity register based on the food bank's country.
    
    Supports:
    - England & Wales: Charity Commission API
    - Scotland: OSCR API
    - Northern Ireland: Charity Commission NI CSV export
    """
    if not foodbank.charity_number:
        return False

    country = foodbank.country

    if country in ["England", "Wales"]:
        return _crawl_charity_ew(foodbank, crawl_set)
    elif country == "Scotland":
        return _crawl_charity_scotland(foodbank, crawl_set)
    elif country == "Northern Ireland":
        return _crawl_charity_ni(foodbank, crawl_set)
    else:
        return False


def _crawl_charity_ew(foodbank, crawl_set = None):
    """Crawl charity details from England & Wales Charity Commission API."""
    from givefood.models import CharityYear, CrawlItem

    ew_charity_api_key = get_cred("ew_charity_api_key")
    
    url = "https://api.charitycommission.gov.uk/register/api/allcharitydetailsV2/%s/0" % foodbank.charity_number

    crawl_item = CrawlItem(
        foodbank = foodbank,
        crawl_type = "charity",
        crawl_set = crawl_set,
        url = url,
    )
    crawl_item.save()

    headers = {
        "Cache-Control": "no-cache",
        "Ocp-Apim-Subscription-Key": ew_charity_api_key,
        "User-Agent": BOT_USER_AGENT,
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            foodbank.charity_id = data["organisation_number"]
            foodbank.charity_name = data["charity_name"]
            foodbank.charity_type = data["charity_type"]
            foodbank.charity_reg_date = data["date_of_registration"].replace("T00:00:00", "")
            foodbank.charity_postcode = data["address_post_code"]
            foodbank.charity_website = data["web"]
            foodbank.charity_purpose = ""
            for item in data["who_what_where"]:
                if item["classification_type"] == "What":
                    foodbank.charity_purpose += item["classification_desc"] + "\n"

    url = "https://api.charitycommission.gov.uk/register/api/charityoverview/%s/0" % foodbank.charity_number
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            foodbank.charity_objectives = data["activities"]

    CharityYear.objects.filter(foodbank=foodbank).delete()

    url = "https://api.charitycommission.gov.uk/register/api/charityfinancialhistory/%s/0" % foodbank.charity_number
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            for year in data:
                charity_year = CharityYear(
                    foodbank=foodbank,
                    date=year.get("financial_period_end_date").replace("T00:00:00", ""),
                    income=year.get("income", 0),
                    expenditure=year.get("expenditure", 0),
                )
                charity_year.save()

    foodbank.last_charity_check = timezone.now()
    foodbank.save(do_decache=False, do_geoupdate=False)

    crawl_item.finish = timezone.now()
    crawl_item.save()

    return True


def _crawl_charity_scotland(foodbank, crawl_set = None):
    """Crawl charity details from Scottish Charity Regulator (OSCR) API."""
    from givefood.models import CharityYear, CrawlItem

    sc_charity_api_key = get_cred("scot_charity_api_key")
    
    url = "https://oscrapi.azurewebsites.net/api/all_charities/?charitynumber=%s" % foodbank.charity_number

    crawl_item = CrawlItem(
        foodbank = foodbank,
        crawl_type = "charity",
        crawl_set = crawl_set,
        url = url,
    )
    crawl_item.save()

    headers = {
        "x-functions-key": sc_charity_api_key,
        "User-Agent": BOT_USER_AGENT,
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            foodbank.charity_id = data["id"]
            foodbank.charity_name = data["charityName"]
            foodbank.charity_reg_date = data["registeredDate"]
            foodbank.charity_postcode = data["postcode"]
            foodbank.charity_website = data["website"]
            foodbank.charity_purpose = ""
            for item in data["purposes"]:
                foodbank.charity_purpose += item + "\n"
            foodbank.charity_objectives = data["objectives"]

    CharityYear.objects.filter(foodbank=foodbank).delete()
    url = "https://oscrapi.azurewebsites.net/api/annualreturns?charityid=%s" % foodbank.charity_id
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            for year in data:
                charity_year = CharityYear(
                    foodbank=foodbank,
                    date=year.get("AccountingReferenceDate"),
                    income=year.get("GrossIncome", 0),
                    expenditure=year.get("GrossExpenditure", 0),
                )
                charity_year.save()

    foodbank.last_charity_check = timezone.now()
    foodbank.save(do_decache=False, do_geoupdate=False)

    crawl_item.finish = timezone.now()
    crawl_item.save()

    return True


def _crawl_charity_ni(foodbank, crawl_set = None):
    """Crawl charity details from Charity Commission for Northern Ireland CSV export."""
    import csv
    from io import StringIO
    from givefood.models import CrawlItem

    reg_id = foodbank.charity_number.replace("NIC","")
    url = "https://www.charitycommissionni.org.uk/umbraco/api/CharityApi/ExportDetailsToCsv?regid=%s&subid=0" % (reg_id)

    crawl_item = CrawlItem(
        foodbank = foodbank,
        crawl_type = "charity",
        crawl_set = crawl_set,
        url = url,
    )
    crawl_item.save()

    headers = {
        "User-Agent": BOT_USER_AGENT,
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        csv_input = csv.reader(StringIO(response.text))
        try:
            csv_headers = next(csv_input)
            data_row = next(csv_input)
        except StopIteration:
            # Empty or malformed CSV response
            pass
        else:
            data = dict(zip(csv_headers, data_row))
            foodbank.charity_name = data.get("Charity name")
            foodbank.charity_reg_date = data.get("Date registered")
            foodbank.charity_website = data.get("Website")
            # Objectives and purposes are reversed in NI
            foodbank.charity_objectives = data.get("Charitable purposes")
            objectives = data.get("What the charity does")
            if objectives:
                objectives = re.sub(r",(?!\s)", "\n", objectives)
            foodbank.charity_purpose = objectives

    foodbank.last_charity_check = timezone.now()
    foodbank.save(do_decache=False, do_geoupdate=False)

    crawl_item.finish = timezone.now()
    crawl_item.save()

    return True


def do_foodbank_need_check(foodbank, crawl_set = None):
    """Scrape a food bank's website for current needs using AI, and record any changes."""
    from givefood.models import FoodbankChange, FoodbankDiscrepancy, CrawlItem

    crawl_item = CrawlItem(
        foodbank = foodbank,
        crawl_type = "need",
        crawl_set = crawl_set,
        url = foodbank.shopping_list_url,
    )
    crawl_item.save()

    headers = {
        "User-Agent": BOT_USER_AGENT,
    }

    scrape_type = "web"
    if "facebook.com" in foodbank.shopping_list_url:
        scrape_type = "facebook"
    if "bankthefood.org" in foodbank.shopping_list_url:
        scrape_type = "bankthefood"

    foodbank_shoppinglist_page = None
    foodbank_shoppinglist_html = None

    if scrape_type == "web":
        # Render the page to Markdown via Cloudflare Browser Rendering. It uses a headless
        # browser, so JS-heavy sites (e.g. the Trussell/IFAN *.foodbank.org.uk platforms)
        # render correctly.
        foodbank_shoppinglist_page = get_markdown(foodbank.shopping_list_url)
        if not foodbank_shoppinglist_page:
            website_discrepancy = FoodbankDiscrepancy(
                foodbank = foodbank,
                discrepancy_type = "website",
                discrepancy_text = "Website %s render failed" % (foodbank.url),
                url = foodbank.url,
            )
            website_discrepancy.save()
            foodbank.last_need_check = timezone.now()
            foodbank.save(do_decache=False, do_geoupdate=False)
            crawl_item.finish = timezone.now()
            crawl_item.save()
            return {
                "foodbank": foodbank,
                "need_prompt": "Connection error: Unable to retrieve needs from foodbank website. Please try again later.",
                "is_nonpertinent": False,
                "is_change": False,
                "change_state": ["Render failed"],
                "need_text": "",
                "excess_text": "",
                "last_published_need": None,
                "last_nonpublished_needs": [],
            }

    if scrape_type == "facebook":

        url = f"https://www.facebook.com/v16.0/plugins/page.php?adapt_container_width=true&app_id=224169065968597&container_width=538&height=1000&hide_cover=false&href=https%3A%2F%2Fwww.facebook.com%2F{ foodbank.facebook_page }&lazy=true&locale=en_GB&sdk=joey&show_facepile=true&show_posts=true&small_header=false&width="

        request = requests.get(url, headers=headers, timeout=10)
        if request.status_code == 200:
            foodbank_shoppinglist_html = request.text
            foodbank_shoppinglist_page = htmlbodytext(request.text)
        
    if scrape_type == "bankthefood":

        # Get token
        request_payload = {"Key1":"{\"DeviceID\":\"widget_c678503d-fdfa-47d9-a1f3-7ea60fc477b2\",\"Token\":\"\",\"RefreshToken\":\"\",\"AffiliateID\":0,\"Code\":\"widget\"}","HTMLVersion":"1.0.6","AppVersion":"1","MainVersion":"1","Platform":2,"AffiliateID":0,"Language":"EN","Country":"GB","Currency":"GBP","TimeZone":"Europe/London"}
        token_url = "https://api.bankthefood.org/api/auth/hello/"
        request = requests.post(token_url, json=request_payload, headers=headers, timeout=10)
        if request.json()["Status"] == "EXPIRED":
            request = requests.post(token_url, json=request_payload, headers=headers, timeout=10)
        token = request.json()["Data"]["Tokens"]["Token"]

        key_match = re.search(r"/(\d+)/", foodbank.shopping_list_url)
        if key_match:
            foodbank_key = key_match.group(1)

        request_payload = {
            "Key1":foodbank_key,
            "HTMLVersion":"1.0.6",
            "AppVersion":"1",
            "MainVersion":"1",
            "Platform":2,
            "AffiliateID":0,
            "Language":"EN",
            "Country":"GB",
            "Currency":"GBP",
            "TimeZone":"Europe/London"
        }
        headers["Authorization"] = "Bearer %s" % (token)

        request = requests.post("https://api.bankthefood.org/api/foodbank/GetWidgetFoodbank/", json=request_payload, headers=headers, timeout=10)

        if request.status_code == 200:
            foodbank_shoppinglist_html = request.text
            foodbank_shoppinglist_page = request.text

    response_schema = {
        "type": "object",
        "properties": {
            "needed": {
                "type": "array",
                "description": "A list of food items the food bank is requesting or has low stock of. Items should be in Title Case and not repeated.",
                "items": {
                    "type": "string"
                }
            },
            "excess": {
                "type": "array",
                "description": "A list of food items the food bank has an excess of. Items should be in Title Case and not repeated.",
                "items": {
                    "type": "string"
                }
            },
        },
        "required": ["needed", "excess"]
    }

    # Fetch the last published need now so we can prime the extraction prompt with it. The model is
    # told to reuse the previous wording for items that are still on the page, which stops cosmetic
    # re-wording drift (Tin vs Tinned, spelling, splitting) from registering as a change in the need
    # comparison below — without a separate judging call. Order/separator drift is handled there too
    # by need_items_key.
    try:
        last_published_need = FoodbankChange.objects.filter(foodbank = foodbank, published = True).latest("created")
    except FoodbankChange.DoesNotExist:
        last_published_need = None

    # Don't prime with placeholder records (e.g. a legacy "Facebook" need) — they aren't real lists.
    priming_need = last_published_need
    if priming_need and priming_need.change_text in ("Facebook", "Unknown", "Nothing"):
        priming_need = None

    need_prompt = render_to_string(
        "foodbank_need_prompt.txt",
        {
            "foodbank":foodbank,
            "scrape_type":scrape_type,
            "foodbank_page":foodbank_shoppinglist_page,
            "foodbank_html":foodbank_shoppinglist_html,
            "last_need":priming_need,
        }
    )

    # Extract needs from the rendered page via DeepSeek on OpenRouter. A fixed seed makes the call
    # reproducible (OpenRouter routes seeded requests stickily to one provider), so an unchanged page
    # yields the same extraction run-to-run instead of drifting between the ~18 providers' differing
    # quantizations. That lets the nonpertinent suppression below catch repeats without a second call.
    #
    # Don't swap this model without checking the provider really honours strict json_schema, and
    # doing it against this schema and the real prompt. OpenRouter's structured_outputs flag is not
    # reliable: qwen/qwen3.5-flash-02-23 advertises it, but Alibaba downgrades json_schema to
    # json_object and then rejects any prompt not containing the literal word "json" — a 400 on
    # every call. json_object alone would not guarantee the needed/excess keys this code indexes.
    need_check_kwargs = {
        "prompt": need_prompt,
        "temperature": 0,
        "model": "deepseek/deepseek-v4-flash",
        "response_schema": response_schema,
        "cred_name": "openrouter_liveneed",
        "seed": 1,
    }
    api_response = openrouter(**need_check_kwargs)
    if api_response.status_code != 200:
        # Retry once on a transient error so a single blip doesn't drop the food bank.
        sleep(60)
        api_response = openrouter(**need_check_kwargs)
    if api_response.status_code != 200:
        raise RuntimeError("OpenRouter need check failed: HTTP %s %s" % (api_response.status_code, api_response.text[:500]))

    response_json = api_response.json()

    usage = response_json.get("usage", {}) or {}
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    output_tokens = usage.get("completion_tokens", 0) or 0
    total_tokens = usage.get("total_tokens", 0) or 0

    need_content = response_json["choices"][0]["message"]["content"]
    try:
        need_response = json.loads(need_content)
    except (json.JSONDecodeError, TypeError):
        need_response = None

    if isinstance(need_response, dict):
        need_text = '\n'.join(need_response["needed"])
        need_text = clean_foodbank_need_text(need_text)
        excess_text = '\n'.join(need_response["excess"])
        excess_text = clean_foodbank_need_text(excess_text)
    else:
        need_text = ""
        excess_text = ""

    last_nonpublished_needs = FoodbankChange.objects.filter(foodbank = foodbank, published = False).order_by("-created")[:10]

    # Safety net: a completely empty extraction when the food bank previously had needs almost
    # always means a failed/blocked render (e.g. an anti-bot interstitial that slipped through),
    # not a genuine change. Don't wipe the published need on that — record a discrepancy and skip.
    if not need_text and not excess_text and last_published_need and (last_published_need.change_text or last_published_need.excess_change_text):
        website_discrepancy = FoodbankDiscrepancy(
            foodbank = foodbank,
            discrepancy_type = "website",
            discrepancy_text = "Empty needs extracted for %s despite an existing published need; skipped to avoid wiping it" % (foodbank.url),
            url = foodbank.url,
        )
        website_discrepancy.save()
        foodbank.last_need_check = timezone.now()
        foodbank.save(do_decache=False, do_geoupdate=False)
        crawl_item.finish = timezone.now()
        crawl_item.save()
        return {
            "foodbank": foodbank,
            "need_prompt": need_prompt,
            "is_nonpertinent": False,
            "is_change": False,
            "change_state": ["Empty extraction skipped"],
            "need_text": "",
            "excess_text": "",
            "last_published_need": last_published_need,
            "last_nonpublished_needs": last_nonpublished_needs,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    is_nonpertinent = False
    is_change = False
    change_state = []

    for last_nonpublished_need in last_nonpublished_needs:
        if need_items_key(need_text) == need_items_key(last_nonpublished_need.change_text) and need_items_key(excess_text) == need_items_key(last_nonpublished_need.excess_change_text):
            is_nonpertinent = True
            change_state.append("Nonpub same")

    if last_published_need is None:
        # No previous published need exists, treat any scraped need or excess as a change
        if need_text or excess_text:
            is_change = True
            change_state.append("First need")
    else:
        # Order- and separator-insensitive: priming keeps wording stable, and this stops a pure
        # reordering or a "/" vs "-" separator difference from registering as a change.
        if need_items_key(need_text) != need_items_key(last_published_need.change_text):
            is_change = True
            change_state.append("Last pub need change")
        if need_items_key(excess_text) != need_items_key(last_published_need.excess_change_text):
            is_change = True
            change_state.append("Last pub excess change")

    if is_change and not is_nonpertinent:
        foodbank_change = FoodbankChange(
            foodbank = foodbank,
            uri = foodbank.shopping_list_url,
            change_text = need_text,
            change_text_original = need_text,
            excess_change_text = excess_text,
            excess_change_text_original = excess_text,
            input_method = "ai",
        )
        foodbank_change.save()
        foodbank_change_content_type = ContentType.objects.get_for_model(foodbank_change)

        crawl_item.content_type = foodbank_change_content_type
        crawl_item.object_id = foodbank_change.id

    foodbank.last_need_check = timezone.now()
    foodbank.save(do_decache=False, do_geoupdate=False)

    crawl_item.finish = timezone.now()
    crawl_item.save()

    return {
        "foodbank":foodbank,
        "need_prompt":need_prompt,
        "is_nonpertinent":is_nonpertinent,
        "is_change":is_change,
        "change_state":change_state,
        "need_text":need_text,
        "excess_text":excess_text,
        "last_published_need":last_published_need,
        "last_nonpublished_needs":last_nonpublished_needs,
        "prompt_tokens":prompt_tokens,
        "output_tokens":output_tokens,
        "total_tokens":total_tokens,
    }


@task(queue_name="needcheck")
def do_foodbank_need_check_async(foodbank_slug, crawl_set_id=None):
    """Async task to check a single food bank's website for updated needs.

    Enqueued one-per-food-bank by the `needcheck` management command onto the
    "needcheck" queue, so the sweep is drained by the task worker rather than run
    inline.
    """
    from givefood.models import Foodbank, CrawlSet
    foodbank = Foodbank.objects.get(slug=foodbank_slug)
    crawl_set = CrawlSet.objects.filter(pk=crawl_set_id).first() if crawl_set_id is not None else None
    do_foodbank_need_check(foodbank, crawl_set)
    return True
