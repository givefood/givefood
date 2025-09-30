import csv
from io import StringIO
import re
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
import requests

from givefood.const.general import BOT_USER_AGENT
from givefood.func import get_cred
from givefood.models import CharityYear, CrawlItem, Foodbank, CrawlSet


class Command(BaseCommand):

    help = 'Runs a specific view function from the command line.'

    def handle(self, *args, **options):

        crawl_set = CrawlSet(
            crawl_type = "charity",
        )
        crawl_set.save()

        ew_charities = Foodbank.objects.filter(country__in=["England", "Wales"], charity_number__isnull=False, is_closed=False)
        sc_charities = Foodbank.objects.filter(country="Scotland", charity_number__isnull=False, is_closed=False)
        ni_charities = Foodbank.objects.filter(country="Northern Ireland", charity_number__isnull=False, is_closed=False)

        ew_charity_api_key = get_cred("ew_charity_api_key")
        sc_charity_api_key = get_cred("scot_charity_api_key")
   
        for foodbank in ew_charities:
            
            self.stdout.write(f"Check E&W {foodbank.name}")

            url = "https://api.charitycommission.gov.uk/register/api/allcharitydetailsV2/%s/0" % foodbank.charity_number

            crawl_item = CrawlItem(
                foodbank = foodbank,
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

            deleted_charity_years = CharityYear.objects.filter(foodbank=foodbank).delete()

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
            
            foodbank.last_charity_check = datetime.now(timezone.utc)
            foodbank.save(do_decache=False, do_geoupdate=False)

            crawl_item.finish = datetime.now()
            crawl_item.save()

        for foodbank in sc_charities:
            self.stdout.write(f"Check SC {foodbank.name}")

            url = "https://oscrapi.azurewebsites.net/api/all_charities/?charitynumber=%s" % foodbank.charity_number

            crawl_item = CrawlItem(
                foodbank = foodbank,
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

            deleted_charity_years = CharityYear.objects.filter(foodbank=foodbank).delete()
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

            foodbank.last_charity_check = datetime.now(timezone.utc)
            foodbank.save(do_decache=False, do_geoupdate=False)

            crawl_item.finish = datetime.now()
            crawl_item.save()
            
        for foodbank in ni_charities:
            self.stdout.write(f"Check NI {foodbank.name}")
            reg_id = foodbank.charity_number.replace("NIC","")
            url = "https://www.charitycommissionni.org.uk/umbraco/api/CharityApi/ExportDetailsToCsv?regid=%s&subid=0" % (reg_id)

            crawl_item = CrawlItem(
                foodbank = foodbank,
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
                headers = next(csv_input)
                data_row = next(csv_input)
                data = dict(zip(headers, data_row))
                foodbank.charity_name = data.get("Charity name")
                foodbank.charity_reg_date = data.get("Date registered")
                foodbank.charity_website = data.get("Website")
                # Objectives and purposes are reversed in NI
                foodbank.charity_objectives = data.get("Charitable purposes")
                objectives = data.get("What the charity does")
                if objectives:
                    objectives = re.sub(r",(?!\s)", "\n", objectives)
                foodbank.charity_purpose = objectives
                foodbank.save()

            crawl_item.finish = datetime.now()
            crawl_item.save()

        crawl_set.finish = datetime.now()
        crawl_set.save()