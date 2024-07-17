import csv
import json
import logging, requests

from datetime import datetime, timedelta, timezone

from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.apps import apps
from givefood.const.item_types import ITEM_CATEGORIES

from givefood.models import Foodbank, FoodbankChangeLine, FoodbankDiscrepancy, FoodbankDonationPoint, FoodbankLocation, FoodbankSubscriber, FoodbankChange, ParliamentaryConstituency
from givefood.const.general import FB_MC_KEY, LOC_MC_KEY
from givefood.func import chatgpt, htmlbodytext, mpid_from_name, oc_geocode, get_all_open_foodbanks, foodbank_article_crawl, get_place_id, pluscode
from django.template.loader import render_to_string


def precacher(request):

    all_locations = FoodbankLocation.objects.all()
    cache.set(LOC_MC_KEY, all_locations, 3600)

    all_foodbanks = Foodbank.objects.all()
    cache.set(FB_MC_KEY, all_foodbanks, 3600)

    return HttpResponse("OK")


def fire_oc_geocode(request):

    pass

#     foodbanks = Foodbank.objects.all()
#     for foodbank in foodbanks:
#         deferred.defer(do_oc_geocode, foodbank)

#     locations = FoodbankLocation.objects.all()
#     for location in locations:
#         deferred.defer(do_oc_geocode, location)

#     return HttpResponse("OK")


def do_oc_geocode(foodbank):

    foodbank.latt_long = oc_geocode(foodbank.full_address())
    foodbank.save()


def crawl_articles(request):

    foodbanks_with_rss = Foodbank.objects.filter(rss_url__isnull=False)

    for foodbank in foodbanks_with_rss:
        foodbank_article_crawl(foodbank)

    return HttpResponse("OK")


def discrepancy_check(request):

    foodbanks = Foodbank.objects.filter(is_closed = False).order_by("last_discrepancy_check", "edited")[:1]

    for foodbank in foodbanks:

        if "facebook.com" not in foodbank.url:

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
            }
            try:
                foodbank_page = requests.get(foodbank.url, headers=headers, verify=False)
            except requests.exceptions.Timeout:
                website_discrepancy = FoodbankDiscrepancy(
                    foodbank = foodbank,
                    discrepancy_type = "website",
                    discrepancy_text = "Website %s connection failed" % (foodbank.url),
                    url = foodbank.url,
                )
                
            if foodbank_page.status_code == 200:
                foodbank_page = htmlbodytext(foodbank_page.text)

                # DETAILS
                detail_prompt = render_to_string(
                    "foodbank_detail_prompt.txt",
                    {
                        "foodbank_page":foodbank_page,
                    }
                )
                detail_response = chatgpt(
                    prompt = detail_prompt,
                    temperature = 0.8,
                )
                detail_response = json.loads(detail_response)

                if detail_response["phone_number"] != foodbank.phone_number:
                    phone_discrepancy = FoodbankDiscrepancy(
                        foodbank = foodbank,
                        discrepancy_type = "phone",
                        discrepancy_text = "Phone number '%s' changed to '%s'" % (foodbank.phone_number, detail_response["phone_number"]),
                        url = foodbank.url,
                    )
                    phone_discrepancy.save()

                if detail_response["postcode"] != foodbank.postcode:
                    postcode_discrepancy = FoodbankDiscrepancy(
                        foodbank = foodbank,
                        discrepancy_type = "postcode",
                        discrepancy_text = "Postcode '%s' changed to '%s'" % (foodbank.postcode, detail_response["postcode"]),
                        url = foodbank.url,
                    )
                    postcode_discrepancy.save()
            else:
                website_discrepancy = FoodbankDiscrepancy(
                    foodbank = foodbank,
                    discrepancy_type = "website",
                    discrepancy_text = "Website %s returned HTTP code %s" % (foodbank.url, foodbank_page.status_code),
                    url = foodbank.url,
                )
                website_discrepancy.save()
                

            # EMAIL
            # if foodbank.email not in foodbank_page:
                # email_discrepancy = FoodbankDiscrepancy(
                #     foodbank = foodbank,
                #     discrepancy_type = "email",
                #     discrepancy_text = "Missing email %s" % foodbank.email,
                #     url = foodbank.url,
                # )
                # email_discrepancy.save()

            # SHOPPING LIST
            # foodbank_shoppinglist_page = requests.get(foodbank.shopping_list_url, headers=headers)
            # foodbank_shoppinglist_page = htmlbodytext(foodbank_shoppinglist_page.text)

            # detail_prompt = render_to_string(
            #     "foodbank_need_prompt.txt",
            #     {
            #         "foodbank_page":foodbank_shoppinglist_page,
            #     }
            # )
            # detail_response = chatgpt(
            #     prompt = detail_prompt,
            #     temperature = 0.8,
            # )
            # detail_response = json.loads(detail_response)

            # need_text = '\n'.join(detail_response["needed"])
            # excess_text = '\n'.join(detail_response["excess"])

            # if need_text != foodbank.latest_need().change_text or excess_text != foodbank.latest_need().excess_change_text:
            #     foodbank_change = FoodbankChange(
            #         foodbank = foodbank,
            #         uri = foodbank.shopping_list_url,
            #         change_text = need_text,
            #         change_text_original = need_text,
            #         excess_change_text = excess_text,
            #         excess_change_text_original = excess_text,
            #         input_method = "ai",
            #     )
            #     foodbank_change.save()

        foodbank.last_discrepancy_check = datetime.now()
        foodbank.save(do_decache=False, do_geoupdate=False)
    
    return HttpResponse("OK")


def cleanup_subs(request):

    unconfirmed_subscribers = FoodbankSubscriber.objects.filter(
        confirmed = False,
        created__lte = datetime.now()-timedelta(days=28),
    )

    for unconfirmed_subscriber in unconfirmed_subscribers:
        unconfirmed_subscriber.delete()

    return HttpResponse("OK")


def days_between_needs(request):

    number_of_needs = 5
    foodbanks = get_all_open_foodbanks()

    for foodbank in foodbanks:

        days_between_needs = 0

        needs = FoodbankChange.objects.filter(foodbank = foodbank).order_by("-created")[:number_of_needs]
        if len(needs) == number_of_needs:
            last_need_date = needs[number_of_needs-1].created
            days_since_earliest_sample_need = (last_need_date - datetime.now()).days
            days_between_needs = int(-days_since_earliest_sample_need / number_of_needs)

        foodbank.days_between_needs = days_between_needs
        foodbank.save(do_decache=False, do_geoupdate=False)


    return HttpResponse("OK")


def need_categorisation(request):

    needs = FoodbankChange.objects.filter(published=True, is_categorised__isnull = True).order_by("-created").exclude(change_text = "Facebook").exclude(change_text = "Unknown").exclude(change_text = "Nothing")[:500]
    for need in needs:
        change_text = need.change_text.split("\n")
        logging.info("Categorising need %s" % need)
        for line in change_text:
            new_category = item_categorisation(line)
            new_need_line = FoodbankChangeLine(
                item = line,
                category = new_category,
                need = need,
                type = "need",
            )
            new_need_line.save()
        
        if need.excess_change_text:
            change_text = need.excess_change_text.split("\n")
            for line in change_text:
                new_category = item_categorisation(line)
                new_need_line = FoodbankChangeLine(
                    item = line,
                    category = new_category,
                    need = need,
                    type = "excess",
                )
                new_need_line.save()

        need.is_categorised = True
        need.save()

    return HttpResponse("OK")
            

def item_categorisation(line):

    logging.info("Categorising %s" % line)

    try:
        prev_need_line = FoodbankChangeLine.objects.filter(item = line).latest("created")
        new_category = prev_need_line.category
        
    except FoodbankChangeLine.DoesNotExist:
        prompt = render_to_string(
            "categorisation_prompt.txt",
            {
                "item":line,
                "item_categories":ITEM_CATEGORIES,
            }
        )
        logging.info("Doing AI cat")
        ai_response = chatgpt(
            prompt = prompt,
            temperature = 0.1,
        )
        if ai_response in ITEM_CATEGORIES:
            new_category = ai_response
        else:
            new_category = "Other"
        logging.info("Got AI cat %s" % new_category)

    return new_category
    


def resaver(request):

    # models = [
    #     # "ParliamentaryConstituency",
    #     # "FoodbankGroup",
    #     # "Foodbank",
    #     # "FoodbankLocation", 
    #     "FoodbankDonationPoint",
    #     # "FoodbankChange",
    #     # "OrderGroup",
    #     # "OrderItem",
    #     # "Order",
    #     # "OrderLine",
    #     # "FoodbankArticle",
    #     # "GfCredential",
    #     # "FoodbankSubscriber",
    #     # "ConstituencySubscriber",
    #     # "Place",
    # ]

    # for model in models:
    #     model_class = apps.get_model("givefood", model)
    #     instances = model_class.objects.all()
    #     for instance in instances:
    #         logging.info("Resaving %s %s" % (model, instance))
    #         instance.save()

    for foodbank in Foodbank.objects.all():
        foodbank.save(do_decache=False)
    for location in FoodbankLocation.objects.all():
        location.save(do_foodbank_resave=False)
    for donationpoint in FoodbankDonationPoint.objects.all():
        donationpoint.save(do_foodbank_resave=False)

    return HttpResponse("OK")


def pluscodes(request):

    foodbanks = Foodbank.objects.filter(plus_code_global__isnull=True)
    for foodbank in foodbanks:
        pluscodes = pluscode(foodbank.latt_long)
        foodbank.plus_code_compound = pluscodes["compound"]
        foodbank.plus_code_global = pluscodes["global"]
        foodbank.save(do_decache=False, do_geoupdate=False)

    locations = FoodbankLocation.objects.filter(plus_code_global__isnull=True)
    for location in locations:
        pluscodes = pluscode(location.latt_long)
        location.plus_code_compound = pluscodes["compound"]
        location.plus_code_global = pluscodes["global"]
        location.save(do_geoupdate=False)

    return HttpResponse("OK")


def place_ids(request):

    foodbanks = Foodbank.objects.filter(place_id__isnull=True)
    for foodbank in foodbanks:
        address = "%s %s %s" % (
            foodbank.full_name(),
            foodbank.address,
            foodbank.postcode,
        )
        place_id = get_place_id(address)
        foodbank.place_id = place_id
        foodbank.save(do_decache=False, do_geoupdate=False)

    locations = FoodbankLocation.objects.filter(place_id__isnull=True)
    for location in locations:
        address = "%s %s %s" % (
            location.name,
            location.address,
            location.postcode,
        )
        place_id = get_place_id(address)
        location.place_id = place_id
        location.save(do_geoupdate=False, do_foodbank_resave=False)

    return HttpResponse("OK")


def load_mps(request):

    logging.warn("Loading MPs")

    with open('./givefood/data/2024_mps.csv', 'r') as file:
        reader = csv.reader(file)
        mps = {}
        for row in reader:
            name = "%s %s" % (row[0], row[1])
            mp_parl_id = mpid_from_name(name)
            logging.warning(name)

            parl_con = ParliamentaryConstituency.objects.get(name=row[5])
            parl_con.mp = name
            parl_con.mp_party = row[4]
            parl_con.mp_parl_id = mp_parl_id
            parl_con.mp_display_name = row[2]
            parl_con.email = row[6]
            parl_con.save()

            if mp_parl_id:                
                image_url = "https://members-api.parliament.uk/api/Members/%s/Thumbnail" % mp_parl_id
                image_response = requests.get(image_url)
                image_response.raise_for_status()
                print("Got image %s" % mp_parl_id)
                file_name = "./givefood/static/img/photos/2024-mp/%s.jpg" % mp_parl_id
                file = open(file_name, 'a+b')
                file.write(image_response.content)
                file.close()
                print("Wrote image %s" % mp_parl_id)

    return HttpResponse("OK")