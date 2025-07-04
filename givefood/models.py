#!/usr/bin/env python
# -*- coding: utf-8 -*-

import html
import math
import hashlib, unicodedata, logging, json
from datetime import date, datetime, timedelta
from string import capwords
from urllib.parse import quote_plus
from furl import furl

from django.db import models
from django.core.validators import RegexValidator
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError
from django.urls import reverse, translate_url
from django.utils.translation import gettext as _
from django.utils.translation import get_language
from django.template.loader import render_to_string
from django.db.models import Max, Min

from requests import PreparedRequest

from givefood.settings import LANGUAGES

from givefood.const.general import DELIVERY_HOURS_CHOICES, COUNTRIES_CHOICES, DELIVERY_PROVIDER_CHOICES, DISCREPANCY_STATUS_CHOICES, DISCREPANCY_TYPES_CHOICES, FOODBANK_NETWORK_CHOICES, PACKAGING_WEIGHT_PC, QUERYSTRING_RUBBISH, TRUSSELL_TRUST_SCHEMA, IFAN_SCHEMA, NEED_INPUT_TYPES_CHOICES, DONT_APPEND_FOOD_BANK, POSTCODE_REGEX, NEED_LINE_TYPES_CHOICES, DONATION_POINT_COMPANIES_CHOICES, DAYS_OF_WEEK
from givefood.const.item_types import ITEM_GROUPS_CHOICES, ITEM_CATEGORIES_CHOICES, ITEM_CATEGORY_GROUPS
from givefood.func import gemini, geocode, get_calories, get_translation, parse_old_sainsburys_order_text, parse_tesco_order_text, parse_sainsburys_order_text, clean_foodbank_need_text, admin_regions_from_postcode, make_url_friendly, find_foodbanks, get_cred, diff_html, mp_contact_details, find_parlcons, decache, place_has_photo, pluscode, translate_need, validate_postcode


class Foodbank(models.Model):

    # Name
    name = models.CharField(max_length=100)
    alt_name = models.CharField(max_length=100, null=True, blank=True, help_text="E.g. Welsh version of the name")
    slug = models.CharField(max_length=100, editable=False)

    # Address
    address = models.TextField()
    postcode = models.CharField(max_length=9, validators=[
        RegexValidator(
            regex = POSTCODE_REGEX,
            message = "Not a valid postcode",
            code = "invalid_postcode",
        ),
    ])
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES)

    # Location
    latt_long = models.CharField(max_length=50, verbose_name="Latitude, Longitude")
    latitude = models.FloatField(editable=False)
    longitude = models.FloatField(editable=False)
    place_id = models.CharField(max_length=1024, verbose_name="Place ID", null=True, blank=True)
    plus_code_compound = models.CharField(max_length=200, verbose_name="Plus Code (Compound)", null=True, blank=True, editable=False)
    plus_code_global = models.CharField(max_length=200, verbose_name="Plus Code (Global)", null=True, blank=True, editable=False)
    place_has_photo = models.BooleanField(default=False, editable=False)
    county = models.CharField(max_length=75, null=True, blank=True, editable=False)
    district = models.CharField(max_length=75, null=True, blank=True, editable=False)
    ward = models.CharField(max_length=75, null=True, blank=True, editable=False)
    lsoa = models.CharField(max_length=75, null=True, blank=True, editable=False)
    msoa = models.CharField(max_length=75, null=True, blank=True, editable=False)

    # Etc
    delivery_address = models.TextField(null=True, blank=True)
    delivery_latt_long = models.CharField(max_length=50, verbose_name="Delivery latitude, longitude", editable=False, null=True, blank=True)
    network = models.CharField(max_length=50, choices=FOODBANK_NETWORK_CHOICES, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    # Charity 
    charity_number = models.CharField(max_length=50,null=True, blank=True)
    charity_just_foodbank = models.BooleanField(default=False, verbose_name="Charity just foodbank", help_text="Tick this if the charity is purely used for the foodbank, rather than other uses such as a church")
    charity_id = models.CharField(max_length=250, editable=False, null=True, blank=True)
    charity_name = models.CharField(max_length=250, editable=False, null=True, blank=True)
    charity_type = models.CharField(max_length=250, editable=False, null=True, blank=True)
    charity_reg_date = models.DateField(editable=False, null=True, blank=True)
    charity_postcode = models.CharField(max_length=9, editable=False, null=True, blank=True, validators=[
        RegexValidator(
            regex = POSTCODE_REGEX,
            message = "Not a valid charity postcode",
            code = "invalid_postcode",
        ),
    ])
    charity_website = models.URLField(max_length=500, editable=False, null=True, blank=True)
    charity_objectives = models.TextField(editable=False, null=True, blank=True)
    charity_purpose = models.TextField(editable=False, null=True, blank=True)

    # Political
    parliamentary_constituency = models.ForeignKey("ParliamentaryConstituency", null=True, blank=True, editable=False, on_delete=models.DO_NOTHING)
    parliamentary_constituency_name = models.CharField(max_length=50, null=True, blank=True, editable=False)
    parliamentary_constituency_slug = models.CharField(max_length=50, null=True, blank=True, editable=False)
    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP", editable=False)
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party", editable=False)
    mp_parl_id = models.IntegerField(verbose_name="MP's ID", null=True, blank=True, editable=False)

    # Social IDs
    facebook_page = models.CharField(max_length=50, null=True, blank=True)
    twitter_handle = models.CharField(max_length=50, null=True, blank=True)
    bankuet_slug = models.CharField(max_length=50, null=True, blank=True)
    fsa_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Food Standards Agency Business ID")
    hours_between_need_check = models.IntegerField(default=3, verbose_name="Hours between need checks", choices=((0,0),(3,3),(6,6),(12,12),(48,48)))

    # Food bank group
    foodbank_group = models.ForeignKey("FoodbankGroup", null=True, blank=True, on_delete=models.DO_NOTHING)
    foodbank_group_name = models.CharField(max_length=100, null=True, blank=True, editable=False)
    foodbank_group_slug = models.CharField(max_length=100, null=True, blank=True, editable=False)

    # Contact details
    contact_email = models.EmailField()
    notification_email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    secondary_phone_number = models.CharField(max_length=20, null=True, blank=True)
    delivery_phone_number = models.CharField(max_length=20, null=True, blank=True)

    # URLs
    url = models.URLField(max_length=200, verbose_name="URL")
    shopping_list_url = models.URLField(max_length=200, verbose_name="Shopping list URL")
    rss_url = models.URLField(max_length=200, verbose_name="RSS feed URL", null=True, blank=True)

    # Booleans
    address_is_administrative = models.BooleanField(default=False, verbose_name="Is the main address just used for administrative purposes?")
    is_closed = models.BooleanField(default=False)
    is_school = models.BooleanField(default=False)

    # Foodbank dates
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    edited = models.DateTimeField(editable=False, null=True)

    # Stored dates
    last_order = models.DateField(editable=False, null=True)
    last_social_media_check = models.DateTimeField(editable=False, null=True)
    last_need = models.DateTimeField(editable=False, null=True)
    last_rfi = models.DateTimeField(editable=False, null=True)
    last_crawl = models.DateTimeField(editable=False, null=True)
    last_discrepancy_check = models.DateTimeField(editable=False, null=True)
    last_need_check = models.DateTimeField(editable=False, null=True)
    latest_need = models.ForeignKey("FoodbankChange", null=True, blank=True, editable=False, on_delete=models.DO_NOTHING, related_name="latest_need")
    last_charity_check = models.DateTimeField(editable=False, null=True, blank=True)

    # Metadata
    no_locations = models.IntegerField(editable=False, default=0)
    no_donation_points = models.IntegerField(editable=False, default=0)
    days_between_needs = models.IntegerField(editable=False, default=0)
    footprint = models.IntegerField(editable=False, default=0)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name
    
    def clean(self):
        if self.phone_number:
            if self.phone_number == self.secondary_phone_number:
                raise ValidationError('Phone number and secondary phone number can not be the same')

    def days_between_needs_text(self):
        if self.days_between_needs == 0:
            return False
        if self.days_between_needs > 90:
            return "few months"
        if self.days_between_needs > 60:
            return "couple of months"
        if self.days_between_needs > 30:
            return "month or so"
        if self.days_between_needs > 14:
            return "couple of weeks"
        if self.days_between_needs > 7:
            return "week or so"
        return "week"
    
    def changefreq(self):
        if self.days_between_needs == 0:
            return "yearly"
        if self.days_between_needs > 90:
            return "yearly"
        if self.days_between_needs > 25:
            return "monthly"
        if self.days_between_needs > 6:
            return "weekly"
        return "daily"

    def schema_org(self, as_sub_property = False):

        needs = self.latest_need_text()
        seeks = []

        if needs != "Nothing" and needs != "Unknown" and needs != "Facebook":
            need_list = needs.splitlines()
            for need in need_list:
                seeks.append({
                    "itemOffered": {
                        "@type":"Product",
                        "name":need,
                    }
                })

        member_of = {}
        if self.network != "Independent":
            if self.network == "Trussell":
                member_of = TRUSSELL_TRUST_SCHEMA
            if self.network == "IFAN":
                member_of = IFAN_SCHEMA

        schema_dict = {
            "@type": "NGO",
            "name": self.full_name(),
            "alternateName": self.alt_name,
            "url": self.url,
            "email": self.contact_email,
            "telephone": self.phone_number,
            "address": {
                "@type": "PostalAddress",
                "postalCode": self.postcode,
                "addressCountry": self.country,
                "streetAddress": self.address,
            },
            "location": {
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": self.latt(),
                    "longitude": self.long(),
                },
            },
            "identifier": self.charity_number,
            "memberOf": member_of,
        }

        # sameAs
        schema_dict["sameAs"] = []
        schema_dict["sameAs"].append(self.url)
        if self.place_id:
            schema_dict["sameAs"].append("https://www.google.co.uk/maps/place/%s/" % quote_plus(self.plus_code_global))
        if self.charity_number:
            schema_dict["sameAs"].append(self.charity_register_url())
        if self.fsa_id:
            schema_dict["sameAs"].append(self.fsa_url())
        if self.facebook_page:
            schema_dict["sameAs"].append("https://www.facebook.com/%s" % self.facebook_page)
        if self.twitter_handle:
            schema_dict["sameAs"].append("https://x.com/%s" % self.twitter_handle)
        
        if not as_sub_property:
            schema_dict["@context"] = "https://schema.org"
            if seeks:
                schema_dict["seeks"] = seeks
        return schema_dict

    def schema_org_str(self):
        return json.dumps(self.schema_org(), indent=4, sort_keys=True)
    
    def full_name_en(self):
        current_language = get_language()
        if self.name in DONT_APPEND_FOOD_BANK:
            return self.name
        else:
            if current_language == "cy" or current_language == "gd":
                return "%s %s" % (_("Foodbank"), self.name)
            else:
                return "%s %s" % (self.name, _("Foodbank"))

    def full_name(self):
        current_language = get_language()
        if current_language == "cy":
            if self.alt_name:
                return self.alt_name
            else:
                return self.full_name_en()
        else:
            return self.full_name_en()
                

    def friendly_url(self):
        return make_url_friendly(self.url)

    def friendly_shopping_list_url(self):
        return make_url_friendly(self.shopping_list_url)
    
    def friendly_rss_url(self):
        if self.rss_url:
            return make_url_friendly(self.rss_url)
        else:
            return None

    def latt(self):
        return float(self.latt_long.split(",")[0])

    def long(self):
        return float(self.latt_long.split(",")[1])

    def full_address(self):
        return "%s\r\n%s" % (self.address, self.postcode)
    
    def delivery_latt(self):
        return float(self.delivery_latt_long.split(",")[0])
    
    def delivery_long(self):
        return float(self.delivery_latt_long.split(",")[1])

    def nearby(self):
        return find_foodbanks(self.latt_long, 10, True)

    def articles(self):
        return FoodbankArticle.objects.filter(foodbank = self).order_by("-published_date")[:20]

    def country_flag(self):
        if self.country == "Scotland":
            return "🏴󠁧󠁢󠁳󠁣󠁴󠁿"
        if self.country == "Northern Ireland":
            return "🇬🇧"
        if self.country == "Wales":
            return "🏴󠁧󠁢󠁷󠁬󠁳󠁿"
        if self.country == "England":
            return "🏴󠁧󠁢󠁥󠁮󠁧󠁿"

    def charity_register_url(self):
        if not self.charity_number:
            return None
        else:
            if self.country == "Scotland":
                return "https://www.oscr.org.uk/about-charities/search-the-register/charity-details?number=%s" % (self.charity_number)
            if self.country == "Northern Ireland":
                return "https://www.charitycommissionni.org.uk/charity-details/?regId=%s" % (self.charity_number.replace("NIC",""))
            if self.country == "Wales" or self.country == "England":
                return "https://register-of-charities.charitycommission.gov.uk/charity-details/?regid=%s&subid=0" % (self.charity_number)
            if self.country == "Isle of Man":
                return "https://www.gov.im/about-the-government/offices/attorney-generals-chambers/crown-office/charities/index-of-charities-registered-in-the-isle-of-man/"

    def fsa_url(self):
        if not self.fsa_id:
            return None
        else:
            return "https://ratings.food.gov.uk/business/%s" % self.fsa_id

    def network_url(self):
        if self.network == "Trussell":
            return "https://www.trussell.org.uk/"
        if self.network == "IFAN":
            return "https://www.foodaidnetwork.org.uk/"
        return False
    
    def needs(self):
        return FoodbankChange.objects.filter(foodbank = self).order_by("-created")

    def latest_need_text(self):
        latest_need = self.latest_need
        if latest_need:
            return latest_need.change_text
        else:
            return "Nothing"
    
    def need_irrelevant(self):
        cut_off = datetime.now() - timedelta(days=180)
        return self.last_need.replace(tzinfo=None) < cut_off

    def latest_need_id(self):

        latest_need = self.latest_need
        if latest_need:
            return latest_need.need_id
        else:
            return None

    def latest_need_date(self):
        latest_need = self.latest_need
        if latest_need:
            return latest_need.created
        else:
            return self.modified

    def latest_need_number(self):
        latest_need_text = self.latest_need_text()
        if latest_need_text == "Unknown":
            return 0
        if latest_need_text == "Nothing":
            return 0
        if latest_need_text == "Facebook":
            return 0
        return latest_need_text.count('\n')+1

    def has_needs(self):
        need_text = self.latest_need_text()
        if need_text == "Nothing" or need_text == "Unknown" or need_text == "Facebook":
            return False
        else:
            return True
        
    def charity_purpose_list(self):
        if not self.charity_purpose:
            return []
        else:
            return self.charity_purpose.splitlines()

    def orders(self):
        return Order.objects.filter(foodbank = self).order_by("-delivery_datetime")

    def no_orders(self):
        return Order.objects.filter(foodbank = self).count()

    def subscribers(self):
        return FoodbankSubscriber.objects.filter(foodbank = self)

    def number_subscribers(self):
        return FoodbankSubscriber.objects.filter(foodbank = self).count()
    
    def get_footprint(self):
        if self.no_locations == 0 and self.no_donation_points == 0:
            return 0
        
        # FB
        fb_max_lat = float(self.latitude)
        fb_min_lat = float(self.latitude)
        fb_max_lng = float(self.longitude)
        fb_min_lng = float(self.longitude)

        # Locations
        loc_max_lat = FoodbankLocation.objects.filter(foodbank = self).aggregate(Max('latitude'))['latitude__max']
        loc_min_lat = FoodbankLocation.objects.filter(foodbank = self).aggregate(Min('latitude'))['latitude__min']
        loc_max_lng = FoodbankLocation.objects.filter(foodbank = self).aggregate(Max('longitude'))['longitude__max']
        loc_min_lng = FoodbankLocation.objects.filter(foodbank = self).aggregate(Min('longitude'))['longitude__min']

        # Donation Points
        dp_max_lat = FoodbankDonationPoint.objects.filter(foodbank = self).aggregate(Max('latitude'))['latitude__max']
        dp_min_lat = FoodbankDonationPoint.objects.filter(foodbank = self).aggregate(Min('latitude'))['latitude__min']
        dp_max_lng = FoodbankDonationPoint.objects.filter(foodbank = self).aggregate(Max('longitude'))['longitude__max']
        dp_min_lng = FoodbankDonationPoint.objects.filter(foodbank = self).aggregate(Min('longitude'))['longitude__min']

        max_lat = max(x for x in [fb_max_lat, loc_max_lat, dp_max_lat] if x is not None)
        min_lat = min(x for x in [fb_min_lat, loc_min_lat, dp_min_lat] if x is not None)
        max_lng = max(x for x in [fb_max_lng, loc_max_lng, dp_max_lng] if x is not None)
        min_lng = min(x for x in [fb_min_lng, loc_min_lng, dp_min_lng] if x is not None)

        meters_per_degree_lat = 111_320  # meters per degree latitude
        avg_lat = (max_lat + min_lat) / 2
        meters_per_degree_lng = 40075000 * math.cos(math.radians(avg_lat)) / 360  # meters per degree longitude at avg_lat

        height_m = abs(max_lat - min_lat) * meters_per_degree_lat
        width_m = abs(max_lng - min_lng) * meters_per_degree_lng

        area_m2 = height_m * width_m
        return int(area_m2)
    

    def get_no_locations(self):
        if not self.pk:
            return 0
        else:
            return FoodbankLocation.objects.filter(foodbank = self).count()
        
    def get_no_donation_points(self):
        if not self.pk:
            return 0
        else:
            no_donation_points = FoodbankDonationPoint.objects.filter(foodbank = self).count()
            no_location_donation_points = FoodbankLocation.objects.filter(foodbank = self, is_donation_point = True).count()
            no_donation_points = no_donation_points + no_location_donation_points
            if self.delivery_address:
                no_donation_points = no_donation_points + 1
        
        return no_donation_points

    def total_weight(self):
        weight = Order.objects.filter(foodbank = self).aggregate(models.Sum('weight'))['weight__sum']
        if not weight:
            return 0
        else:
            return weight

    def total_weight_kg(self):
        return self.total_weight() / 1000

    def total_weight_kg_pkg(self):
        return self.total_weight_kg() * PACKAGING_WEIGHT_PC

    def total_cost(self):
        cost = Order.objects.filter(foodbank = self).aggregate(models.Sum('cost'))['cost__sum']
        if not cost:
            return 0
        else:
            return cost / 100

    def total_items(self):
        return Order.objects.filter(foodbank = self).aggregate(models.Sum('no_items'))['no_items__sum']

    def locations(self):
        return FoodbankLocation.objects.filter(foodbank = self).order_by("name")
    
    def location_donation_points(self):
        return FoodbankLocation.objects.filter(foodbank = self, is_donation_point = True).order_by("name")
    
    def donation_points(self):
        return FoodbankDonationPoint.objects.filter(foodbank = self).order_by("name")
    
    def donation_point_companies(self):
        companies = FoodbankDonationPoint.objects.filter(foodbank = self, company__isnull=False).values_list("company", flat=True).distinct()
        return sorted(companies)
    
    def get_absolute_url(self):
        return "/admin/foodbank/%s/" % (self.slug)

    def url_with_ref(self):
        added_params = {"ref":"givefood.org.uk"}
        req = PreparedRequest()
        req.prepare_url(self.url, added_params)
        return req.url

    def bankuet_url(self):
        if self.bankuet_slug:
            return "https://www.bankuet.co.uk/%s/?ref=givefood.org.uk" % (self.bankuet_slug)
        else:
            return None
        
    def articles_month(self):
        return FoodbankArticle.objects.filter(foodbank = self, published_date__gte = datetime.now() - timedelta(days=28)).order_by("-published_date")
    
    class Meta:
        app_label = 'givefood'

    def delete(self, *args, **kwargs):
        
        FoodbankHit.objects.filter(foodbank = self).delete()
        FoodbankChangeLine.objects.filter(foodbank = self).delete()
        FoodbankChange.objects.filter(foodbank = self).delete()
        FoodbankLocation.objects.filter(foodbank = self).delete()
        FoodbankArticle.objects.filter(foodbank = self).delete()
        FoodbankSubscriber.objects.filter(foodbank = self).delete()
        FoodbankDonationPoint.objects.filter(foodbank = self).delete()
        FoodbankDiscrepancy.objects.filter(foodbank = self).delete()
        
        super(Foodbank, self).delete(*args, **kwargs)


    def save(self, do_decache=True, do_geoupdate=True, *args, **kwargs):

        logging.info("Saving food bank %s" % self.name)

        # Slugify name
        self.slug = slugify(self.name)

        # LatLong
        self.latitude = self.latt_long.split(",")[0]
        self.longitude = self.latt_long.split(",")[1]

        # Footprint
        self.footprint = self.get_footprint()

        # Cleanup phone numbers
        if self.phone_number:
            self.phone_number = self.phone_number.replace(" ","")
        if self.secondary_phone_number:
            self.secondary_phone_number = self.secondary_phone_number.replace(" ","")

        if self.delivery_address:
            self.delivery_latt_long = geocode(self.delivery_address)
        else:
            self.delivery_latt_long = None

        if do_geoupdate:

            # Photo?
            if self.place_id:
                self.place_has_photo = place_has_photo(self.place_id)
            else:
                self.place_has_photo = False

            regions = admin_regions_from_postcode(self.postcode)
            self.county = regions.get("county", None)
            self.ward = regions.get("ward", None)
            self.district = regions.get("district", None)
            self.lsoa = regions.get("lsoa", None)
            self.msoa = regions.get("msoa", None)

            if self.foodbank_group:
                self.foodbank_group_name = self.foodbank_group.name
                self.foodbank_group_slug = self.foodbank_group.slug
            else:
                self.foodbank_group_name = None
                self.foodbank_group_slug = None

            try:
                parl_con = ParliamentaryConstituency.objects.get(name = regions.get("parliamentary_constituency", None))
                logging.info("Got parl_con %s" % parl_con)
                self.parliamentary_constituency = parl_con
                self.parliamentary_constituency_name = self.parliamentary_constituency.name
                self.parliamentary_constituency_slug = slugify(self.parliamentary_constituency_name)
                # self.mp = self.parliamentary_constituency.mp
                # self.mp_party = self.parliamentary_constituency.mp_party
                # self.mp_parl_id = self.parliamentary_constituency.mp_parl_id
            except ParliamentaryConstituency.DoesNotExist: 
                logging.info("Didn't get parl con %s" % regions.get("parliamentary_constituency", None))
                self.parliamentary_constituency = None

            pluscodes = pluscode(self.latt_long)
            self.plus_code_compound = pluscodes["compound"]
            self.plus_code_global = pluscodes["global"]

        # Cache number of locations & donation points
        self.no_locations = self.get_no_locations()
        self.no_donation_points = self.get_no_donation_points()

        # Cache last need date
        try:
            if self.pk:
                last_need = FoodbankChange.objects.filter(foodbank = self).latest("created")
                self.last_need = last_need.created
            else:
                self.last_need = None
        except FoodbankChange.DoesNotExist:
            self.last_need = None

        # Cache latest need
        try:
            if self.pk:
                need = FoodbankChange.objects.filter(foodbank = self, published = True).latest("created")
                self.latest_need = need
            else:
                self.latest_need = None
        except FoodbankChange.DoesNotExist:
            self.latest_need = None

        super(Foodbank, self).save(*args, **kwargs)

        if do_decache:

            # FB URLs
            foodbank_prefix = reverse("wfbn:foodbank", kwargs={"slug":self.slug})
            prefixes = []
            for language in LANGUAGES:
                prefixes.append(translate_url(foodbank_prefix, language[0]))

            # Individual URLs
            page_urls = [
                reverse("wfbn:index"),
                reverse("wfbn:rss"),
                reverse("wfbn:geojson"),
                reverse("api_foodbanks"),
            ]

            translated_urls = []
            for url in page_urls:
                for language in LANGUAGES:
                    translated_urls.append(translate_url(url, language[0]))

            prefixes.append(reverse("api2:foodbanks"))
            prefixes.append(reverse("api2:locations"))
            prefixes.append(reverse("api2:foodbank", kwargs={"slug":self.slug}))
            prefixes.append(reverse("api2:constituency", kwargs={"slug":self.parliamentary_constituency_slug}))

            api_urls = [
                reverse("sitemap"),
                "%s?format=csv" % (reverse("api_foodbanks")),
                reverse("api2:locations"),
                "%s?format=geojson" % (reverse("api2:donationpoints")),
                reverse("api_foodbank", kwargs={"slug":self.slug}),
                reverse("wfbn:constituency", kwargs={"slug":self.parliamentary_constituency_slug}),
                reverse("wfbn:constituency_geojson", kwargs={"parlcon_slug":self.parliamentary_constituency_slug}),
            ]

            urls = translated_urls + api_urls
            decache(urls, prefixes)


class FoodbankLocation(models.Model):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False)
    foodbank_slug = models.CharField(max_length=100, editable=False)
    foodbank_network = models.CharField(max_length=50, editable=False)
    foodbank_phone_number = models.CharField(max_length=50, null=True, blank=True, editable=False)
    foodbank_email = models.EmailField(editable=False)
    is_closed = models.BooleanField(default=False)

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, editable=False)
    address = models.TextField()
    postcode = models.CharField(max_length=9, validators=[
        RegexValidator(
            regex = POSTCODE_REGEX,
            message = "Not a valid postcode",
            code = "invalid_postcode",
        ),
    ])

    is_donation_point = models.BooleanField(default=False)
    
    latt_long = models.CharField(max_length=50, verbose_name="Latitude, Longitude")
    latitude = models.FloatField(editable=False)
    longitude = models.FloatField(editable=False)

    place_id = models.CharField(max_length=1024, verbose_name="Place ID", null=True, blank=True)
    place_has_photo = models.BooleanField(default=False, editable=False)
    plus_code_compound = models.CharField(max_length=200, verbose_name="Plus Code (Compound)", null=True, blank=True, editable=False)
    plus_code_global = models.CharField(max_length=200, verbose_name="Plus Code (Global)", null=True, blank=True, editable=False)

    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, editable=False)

    phone_number = models.CharField(max_length=50, null=True, blank=True, help_text="If different to the main location")
    email = models.EmailField(null=True, blank=True, help_text="If different to the main location")

    parliamentary_constituency = models.ForeignKey("ParliamentaryConstituency", null=True, blank=True, editable=False, on_delete=models.DO_NOTHING)
    parliamentary_constituency_name = models.CharField(max_length=50, null=True, blank=True, editable=False)
    parliamentary_constituency_slug = models.CharField(max_length=50, null=True, blank=True, editable=False)
    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP", editable=False)
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party", editable=False)
    mp_parl_id = models.IntegerField(verbose_name="MP's ID", null=True, blank=True, editable=False)

    county = models.CharField(max_length=75, null=True, blank=True, editable=False)
    district = models.CharField(max_length=75, null=True, blank=True, editable=False)
    ward = models.CharField(max_length=75, null=True, blank=True, editable=False)
    lsoa = models.CharField(max_length=75, null=True, blank=True, editable=False)
    msoa = models.CharField(max_length=75, null=True, blank=True, editable=False)

    modified = models.DateTimeField(auto_now=True, editable=False)
    edited = models.DateTimeField(editable=False, null=True)

    class Meta:
       unique_together = ('foodbank', 'name',)
       app_label = 'givefood'

    def __str__(self):
        return self.name
    
    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/admin/foodbank/%s/location/%s/edit/" % (self.foodbank.slug, self.slug)
    
    def clean(self):
        if self.phone_number:
            if self.phone_number == self.foodbank.phone_number:
                raise ValidationError("Phone number can't be the same as the foodbank organisation's phone number")
            if self.phone_number == self.foodbank.secondary_phone_number:
                raise ValidationError("Phone number can't be the same as the foodbank organisation's secondary phone number")

    def schema_org(self, as_sub_property = False):

        needs = self.foodbank.latest_need_text()
        seeks = []

        if needs != "Nothing" and needs != "Unknown" and needs != "Facebook":
            need_list = needs.splitlines()
            for need in need_list:
                seeks.append({
                    "itemOffered": {
                        "@type":"Product",
                        "name":need,
                    }
                })

        member_of = {}
        if self.foodbank_network != "Independent":
            if self.foodbank_network == "Trussell":
                member_of = TRUSSELL_TRUST_SCHEMA
            if self.foodbank_network == "IFAN":
                member_of = IFAN_SCHEMA

        schema_dict = {
            "@context": "https://schema.org",
            "@type": "NGO",
            "name": self.full_name(),
            "url": self.foodbank.url,
            "email": self.email_or_foodbank_email(),
            "telephone": self.phone_or_foodbank_phone(),
            "address": {
                "@type": "PostalAddress",
                "postalCode": self.postcode,
                "addressCountry": self.country,
                "streetAddress": self.address,
            },
            "location": {
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": self.latt(),
                    "longitude": self.long(),
                },
            },
            "identifier":self.foodbank.charity_number,
            "memberOf":member_of,
            "parentOrganization":self.foodbank.schema_org(as_sub_property = True)
        }
        if not as_sub_property:
            schema_dict["@context"] = "https://schema.org"
            if seeks:
                schema_dict["seeks"] = seeks
        return schema_dict

    def schema_org_str(self):
        return json.dumps(self.schema_org(), indent=4, sort_keys=True)

    def full_name(self):
        return "%s, %s" % (self.name, self.foodbank.full_name())
        
    def phone_or_foodbank_phone(self):
        if self.phone_number:
            return self.phone_number
        else:
            return self.foodbank_phone_number

    def email_or_foodbank_email(self):
        if self.email:
            return self.email
        else:
            return self.foodbank_email

    def latest_need(self):
        return self.foodbank.latest_need

    def full_address(self):
        return "%s\r\n%s" % (self.address, self.postcode)

    def latt(self):
        return float(self.latt_long.split(",")[0])

    def long(self):
        return float(self.latt_long.split(",")[1])

    def delete(self, *args, **kwargs):

        super(FoodbankLocation, self).delete(*args, **kwargs)
        # Resave the parent food bank
        self.foodbank.save(do_geoupdate=False)

    def save(self, do_geoupdate=True, do_foodbank_resave=True, *args, **kwargs):

        logging.info("Saving food bank location %s" % self.name)

        # Slugify name
        self.slug = slugify(self.name)

        # LatLong
        self.latitude = self.latt_long.split(",")[0]
        self.longitude = self.latt_long.split(",")[1]

        # Cache foodbank details
        self.foodbank_name = self.foodbank.name
        self.foodbank_slug = self.foodbank.slug
        self.foodbank_network = self.foodbank.network
        self.foodbank_phone_number = self.foodbank.phone_number
        self.foodbank_email = self.foodbank.contact_email
        self.is_closed = self.foodbank.is_closed

        # Cleanup phone number
        if self.phone_number:
            self.phone_number = self.phone_number.replace(" ","")

        if do_geoupdate:

            # Photo?
            if self.place_id:
                self.place_has_photo = place_has_photo(self.place_id)
            else:
                self.place_has_photo = False

            # Update politics
            regions = admin_regions_from_postcode(self.postcode)
            self.country = regions.get("country", None)
            self.county = regions.get("county", None)
            self.ward = regions.get("ward", None)
            self.district = regions.get("district", None)
            self.lsoa = regions.get("lsoa", None)
            self.msoa = regions.get("msoa", None)

            try:
                parl_con = ParliamentaryConstituency.objects.get(name = regions.get("parliamentary_constituency", None))
                logging.info("Got parl_con %s" % parl_con)
                self.parliamentary_constituency = parl_con
                self.parliamentary_constituency_name = self.parliamentary_constituency.name
                self.parliamentary_constituency_slug = slugify(self.parliamentary_constituency_name)
                # self.mp = self.parliamentary_constituency.mp
                # self.mp_party = self.parliamentary_constituency.mp_party
                # self.mp_parl_id = self.parliamentary_constituency.mp_parl_id
            except ParliamentaryConstituency.DoesNotExist: 
                logging.info("Didn't get parl con %s" % regions.get("parliamentary_constituency", None))
                self.parliamentary_constituency = None

            pluscodes = pluscode(self.latt_long)
            self.plus_code_compound = pluscodes["compound"]
            self.plus_code_global = pluscodes["global"]

        super(FoodbankLocation, self).save(*args, **kwargs)

        # Resave the parent food bank
        if do_foodbank_resave:
            self.foodbank.save(do_geoupdate=False)


class FoodbankDonationPoint(models.Model):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False)
    foodbank_slug = models.CharField(max_length=100, editable=False)
    foodbank_network = models.CharField(max_length=50, editable=False)
    is_closed = models.BooleanField(default=False)

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, editable=False)
    address = models.TextField()
    postcode = models.CharField(max_length=9, validators=[
        RegexValidator(
            regex = POSTCODE_REGEX,
            message = "Not a valid postcode",
            code = "invalid_postcode",
        ),
    ])
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    opening_hours = models.TextField(null=True, blank=True)
    wheelchair_accessible = models.BooleanField(null=True, blank=True)
    url = models.URLField(max_length=1024, verbose_name="URL", null=True, blank=True)
    in_store_only = models.BooleanField(default=False)
    company = models.CharField(max_length=100, null=True, blank=True, choices=DONATION_POINT_COMPANIES_CHOICES)
    notes = models.TextField(null=True, blank=True, help_text="These notes are public")

    latt_long = models.CharField(max_length=50, verbose_name="Latitude, Longitude")
    latitude = models.FloatField(editable=False)
    longitude = models.FloatField(editable=False)

    place_id = models.CharField(max_length=1024, verbose_name="Place ID", null=True, blank=True)
    place_has_photo = models.BooleanField(default=False, editable=False)
    plus_code_compound = models.CharField(max_length=200, verbose_name="Plus Code (Compound)", null=True, blank=True, editable=False)
    plus_code_global = models.CharField(max_length=200, verbose_name="Plus Code (Global)", null=True, blank=True, editable=False)

    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, editable=False)

    parliamentary_constituency = models.ForeignKey("ParliamentaryConstituency", null=True, blank=True, editable=False, on_delete=models.DO_NOTHING)
    parliamentary_constituency_name = models.CharField(max_length=50, null=True, blank=True, editable=False)
    parliamentary_constituency_slug = models.CharField(max_length=50, null=True, blank=True, editable=False)
    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP", editable=False)
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party", editable=False)
    mp_parl_id = models.IntegerField(verbose_name="MP's ID", null=True, blank=True, editable=False)

    county = models.CharField(max_length=75, null=True, blank=True, editable=False)
    district = models.CharField(max_length=75, null=True, blank=True, editable=False)
    ward = models.CharField(max_length=75, null=True, blank=True, editable=False)
    lsoa = models.CharField(max_length=75, null=True, blank=True, editable=False)
    msoa = models.CharField(max_length=75, null=True, blank=True, editable=False)

    modified = models.DateTimeField(auto_now=True, editable=False)
    edited = models.DateTimeField(editable=False, null=True)

    class Meta:
       unique_together = ('foodbank', 'name',)
       app_label = 'givefood'

    def __str__(self):
        return self.name
    
    def __unicode__(self):
        return self.name
    
    def url_with_ref(self):
        if self.url:
            url = furl(self.url)
            url.remove(QUERYSTRING_RUBBISH)
            url.add({"ref":"givefood.org.uk"})
            return url.url
        else:
            return False
    
    def friendly_url(self):
        return make_url_friendly(self.url)

    def full_address(self):
        return "%s\r\n%s" % (self.address, self.postcode)
    
    def latt(self):
        return float(self.latt_long.split(",")[0])

    def long(self):
        return float(self.latt_long.split(",")[1])
    
    def schema_org(self):

        needs = self.foodbank.latest_need_text()
        seeks = []

        if needs != "Nothing" and needs != "Unknown" and needs != "Facebook":
            need_list = needs.splitlines()
            for need in need_list:
                seeks.append({
                    "itemOffered": {
                        "@type":"Product",
                        "name":need,
                    }
                })

        schema_dict = {
            "@context": "https://schema.org",
            "@type": "Place",
            "name": self.name,
            "url": self.url,
            "telephone": self.phone_number,
            "isAccessibleForFree": self.wheelchair_accessible,
            "address": {
                "@type": "PostalAddress",
                "postalCode": self.postcode,
                "addressCountry": self.country,
                "streetAddress": self.address,
            },
            "location": {
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": self.latt(),
                    "longitude": self.long(),
                },
            }
        }

        if seeks:
            schema_dict["seeks"] = seeks

        return schema_dict

    def schema_org_str(self):
        return json.dumps(self.schema_org(), indent=4, sort_keys=True)
    
    def opening_hours_days(self):

        if not self.opening_hours:
            return False

        opening_hours = self.opening_hours
        for day_of_week in DAYS_OF_WEEK:
            opening_hours = opening_hours.replace(day_of_week, _(day_of_week))
        opening_hours = opening_hours.replace("Closed", _("Closed"))

        days = opening_hours.split("\n")
        
        bank_holidays = json.load(open("./givefood/data/bank-holidays.json"))

        if self.country == "England":
            bank_holidays = bank_holidays["england-and-wales"]
        if self.country == "Wales":
            bank_holidays = bank_holidays["england-and-wales"]
        if self.country == "Scotland":
            bank_holidays = bank_holidays["scotland"]
        if self.country == "Northern Ireland":
            bank_holidays = bank_holidays["northern-ireland"]
        if not bank_holidays:
            bank_holidays = {}

        bank_holidays = bank_holidays.get("events", None)
        if bank_holidays:
            for idx, holiday in enumerate(bank_holidays):
                bank_holidays[idx]["date"] = datetime.strptime(holiday["date"], "%Y-%m-%d").date()

        today = date.today()
        day_dates = []
        for day_offset in range(7):
            day_date = today + timedelta(days=day_offset)
            day_dates.append(day_date)

        relative_days = []

        for idx, day_date in enumerate(day_dates):
            day_of_week = day_date.weekday()
            relative_days.append({
                "text": days[day_of_week],
                "date": day_date,
                "is_closed": "Closed" in days[day_of_week],
            })
            if bank_holidays:
                relative_days[idx]["holiday"] = next((holiday for holiday in bank_holidays if holiday["date"] == day_date), None)

        return relative_days
        
    def clean(self):
        if self.postcode:
            lat_lngs = []
            for location in self.foodbank.locations():
                lat_lngs.append(location.latt_long)
            lat_lngs.append(self.foodbank.latt_long)
            lat_lngs.append(self.foodbank.delivery_latt_long)

            if self.latt_long in lat_lngs:
                raise ValidationError("Location can't be the same as the food bank or one of it's locations")

            if not validate_postcode(self.postcode):
                raise ValidationError("Invalid postcode")
        

    def delete(self, *args, **kwargs):

        super(FoodbankDonationPoint, self).delete(*args, **kwargs)
        # Resave the parent food bank
        self.foodbank.save(do_geoupdate=False)
    
    def save(self, do_geoupdate=True, do_foodbank_resave=True, do_photo_update=True, *args, **kwargs):

        # Slugify name
        self.slug = slugify(self.name)

        # LatLong
        self.latitude = self.latt_long.split(",")[0]
        self.longitude = self.latt_long.split(",")[1]

        # Photo?
        if do_photo_update:
            if self.place_id:
                self.place_has_photo = place_has_photo(self.place_id)
            else:
                self.place_has_photo = False

        # Cleanup phone number
        if self.phone_number:
            self.phone_number = self.phone_number.replace(" ","")

        # Cache foodbank details
        self.foodbank_name = self.foodbank.name
        self.foodbank_slug = self.foodbank.slug
        self.foodbank_network = self.foodbank.network
        self.is_closed = self.foodbank.is_closed

        if do_geoupdate:
            # Update politics
            regions = admin_regions_from_postcode(self.postcode)
            self.country = regions.get("country", None)
            self.county = regions.get("county", None)
            self.ward = regions.get("ward", None)
            self.district = regions.get("district", None)
            self.lsoa = regions.get("lsoa", None)
            self.msoa = regions.get("msoa", None)

            try:
                parl_con = ParliamentaryConstituency.objects.get(name = regions.get("parliamentary_constituency", None))
                logging.info("Got parl_con %s" % parl_con)
                self.parliamentary_constituency = parl_con
                self.parliamentary_constituency_name = self.parliamentary_constituency.name
                self.parliamentary_constituency_slug = slugify(self.parliamentary_constituency_name)
                # self.mp = self.parliamentary_constituency.mp
                # self.mp_party = self.parliamentary_constituency.mp_party
                # self.mp_parl_id = self.parliamentary_constituency.mp_parl_id
            except ParliamentaryConstituency.DoesNotExist: 
                logging.info("Didn't get parl con %s" % regions.get("parliamentary_constituency", None))
                self.parliamentary_constituency = None

            pluscodes = pluscode(self.latt_long)
            self.plus_code_compound = pluscodes["compound"]
            self.plus_code_global = pluscodes["global"]

        super(FoodbankDonationPoint, self).save(*args, **kwargs)
        
        # Resave the parent food bank
        if do_foodbank_resave:
            self.foodbank.save(do_geoupdate=False)


class Order(models.Model):

    order_id = models.CharField(max_length=100, editable=False)
    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False)
    items_text = models.TextField()
    need = models.ForeignKey("FoodbankChange", null=True, blank=True, on_delete=models.DO_NOTHING)
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, editable=False)
    order_group = models.ForeignKey("OrderGroup", null=True, blank=True, on_delete=models.DO_NOTHING)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    notification_email_sent = models.DateTimeField(null=True, blank=True, editable=False)
    source_url = models.URLField(null=True, blank=True, verbose_name="Source URL", help_text="Optional URL of a tweet, facebook post etc where the food need came from")

    delivery_date = models.DateField()
    delivery_hour = models.IntegerField(choices=DELIVERY_HOURS_CHOICES)
    delivery_datetime = models.DateTimeField(editable=False)

    delivery_provider = models.CharField(max_length=50, choices=DELIVERY_PROVIDER_CHOICES, null=True, blank=True)
    delivery_provider_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Delivery provider ID")

    weight = models.PositiveIntegerField(editable=False)
    calories = models.PositiveIntegerField(editable=False)
    cost = models.PositiveIntegerField(editable=False) # Pence, the cost when ordered
    actual_cost = models.PositiveIntegerField(null=True, blank=True, verbose_name="Delivered cost", help_text="In pence") # Pence, the cost when delivered
    no_lines = models.PositiveIntegerField(editable=False)
    no_items = models.PositiveIntegerField(editable=False)

    class Meta:
       unique_together = ('foodbank', 'delivery_date', 'delivery_provider')
       app_label = 'givefood'

    def __str__(self):
        return self.order_id

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def delivery_hour_end(self):
        return self.delivery_hour + 1

    def natural_cost(self):
        return float(self.cost/100)
    
    def natural_actual_cost(self):
        if self.actual_cost:
            return float(self.actual_cost/100)
        else:
            return None

    def weight_kg(self):
        return self.weight/1000

    def weight_kg_pkg(self):
        return self.weight_kg() * PACKAGING_WEIGHT_PC

    def delete(self, *args, **kwargs):

        # Delete all the existing orderlines
        order_lines = OrderLine.objects.filter(order = self)
        for order_line in order_lines:
            order_line.delete()
        super(Order, self).delete(*args, **kwargs)

    def save(self, do_foodbank_save = True, *args, **kwargs):
        # Generate ID
        self.order_id = "gf-%s-%s-%s" % (
            self.foodbank.slug,
            slugify(self.delivery_provider),
            str(self.delivery_date)
        )

        # Store delivery_datetime
        self.delivery_datetime = datetime(
            self.delivery_date.year,
            self.delivery_date.month,
            self.delivery_date.day,
            self.delivery_hour,
            0,
        )

        self.weight = 0
        self.calories = 0
        self.cost = 0
        self.no_lines = 0
        self.no_items = 0

        # Denorm foodbank name & country
        self.foodbank_name = self.foodbank.name
        self.country = self.foodbank.country

        super(Order, self).save(*args, **kwargs)

        # Delete all the existing orderlines
        order_lines = OrderLine.objects.filter(order = self).delete()

        # Parse the order text
        prompt = render_to_string(
            "admin/orderline_prompt.txt",
            {
                "items_text":self.items_text,
            }
        )
        order_lines = gemini(
            prompt = prompt,
            temperature = 0.1,
        )
        order_lines = json.loads(order_lines)

        # Order aggregated stats
        order_weight = 0
        order_calories = 0
        order_cost = 0
        order_items = 0

        for order_line in order_lines:

            line_weight = 0
            line_cost = 0

            line_weight = order_line["weight"] * order_line["quantity"]
            line_cost = order_line["item_cost"] * order_line["quantity"]
            order_line["name"] = html.unescape(order_line["name"])

            try:
                order_line["calories"] = get_calories(order_line["name"], order_line["weight"], order_line["quantity"])
            except OrderLine.DoesNotExist:
                order_line["calories"] = 0
            
            order_cost = order_cost + line_cost
            order_items = order_items + order_line["quantity"]
            order_calories = order_calories + order_line["calories"]
            order_weight = order_weight + line_weight

            new_order_line = OrderLine(
                foodbank = self.foodbank,
                order = self,
                name = order_line.get("name"),
                quantity = order_line["quantity"],
                item_cost = order_line["item_cost"],
                line_cost = line_cost,
                weight = line_weight,
                calories = order_line["calories"],
            )
            new_order_line.save()

        # Order aggregated stats
        self.weight = order_weight
        self.calories = order_calories
        self.cost = order_cost
        self.no_lines = len(order_lines)
        self.no_items = order_items

        super(Order, self).save(*args, **kwargs)

        # Update last order date on foodbank
        if do_foodbank_save:
            self.foodbank.last_order = Order.objects.filter(foodbank = self.foodbank).order_by("-delivery_date")[0].delivery_date
            self.foodbank.save(do_geoupdate=False)

    def lines(self):
        return OrderLine.objects.filter(order = self).order_by("-weight")


class OrderLine(models.Model):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    order = models.ForeignKey(Order, on_delete=models.DO_NOTHING)

    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    item_cost = models.PositiveIntegerField() #pence
    line_cost = models.PositiveIntegerField()

    weight = models.PositiveIntegerField(editable=False,null=True)
    calories = models.PositiveIntegerField(editable=False,null=True)

    def weight_kg(self):
        return self.weight/1000

    class Meta:
        app_label = 'givefood'


class OrderItem(models.Model):

    name = models.CharField(max_length=100, unique=True)
    slug = models.CharField(max_length=100, editable=False)
    calories = models.PositiveIntegerField(help_text="Per 100g")
    tesco_image_id = models.CharField(max_length=100, null=True, blank=True)
    sainsburys_image_id = models.CharField(max_length=100, null=True, blank=True)

    def orders(self):
        order_lines = OrderLine.objects.filter(name = self.name)
        orders = []
        for order_line in order_lines:
            orders.append(order_line.order)
        orders = list(set(orders))
        return orders

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)
        super(OrderItem, self).save(*args, **kwargs)

    class Meta:
        app_label = 'givefood'


class OrderGroup(models.Model):

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, editable=False)
    public = models.BooleanField(default=False)
    key = models.CharField(max_length=8, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    def orders(self):
        return Order.objects.filter(order_group = self).order_by("delivery_datetime")

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)
        super(OrderGroup, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'givefood'


class FoodbankArticle(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    foodbank = models.ForeignKey(Foodbank, null=True, blank=True, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    published_date = models.DateTimeField(editable=False)
    title = models.CharField(max_length=250)
    url = models.CharField(max_length=250, unique=True)

    def url_with_ref(self):
        added_params = {"ref":"givefood.org.uk"}
        req = PreparedRequest()
        req.prepare_url(self.url, added_params)
        return req.url

    def title_captialised(self):
        return capwords(self.title).replace("Uk","UK")

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def save(self, *args, **kwargs):

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        super(FoodbankArticle, self).save(*args, **kwargs)

    def __str__(self):
        return "%s - %s" % (self.title, self.foodbank_name)
    
    class Meta:
        app_label = 'givefood'


class FoodbankGroup(models.Model):

    name = models.CharField(max_length=100, null=True, blank=True)
    slug = models.CharField(max_length=100, editable=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    def foodbanks(self):
        return Foodbank.objects.filter(foodbank_group = self).order_by("name")

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)
        super(FoodbankGroup, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.name

    class Meta:
        app_label = 'givefood'


class FoodbankDiscrepancy(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    
    foodbank = models.ForeignKey(Foodbank, null=True, blank=True, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)
    need = models.ForeignKey("FoodbankChange", null=True, blank=True, on_delete=models.DO_NOTHING)

    url = models.URLField(null=True, blank=True)
    discrepancy_type = models.CharField(max_length=50, choices=DISCREPANCY_TYPES_CHOICES)
    discrepancy_text = models.TextField()
    status = models.CharField(max_length=10, choices=DISCREPANCY_STATUS_CHOICES, default="New")

    def foodbank_slug(self):
        return slugify(self.foodbank_name)

    def save(self, *args, **kwargs):

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        super(FoodbankDiscrepancy, self).save(*args, **kwargs)


class FoodbankChange(models.Model):

    # This is known on the frontend as a 'need'

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    need_id = models.CharField(max_length=8, editable=False)

    foodbank = models.ForeignKey(Foodbank, null=True, blank=True, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    distill_id = models.CharField(max_length=250, null=True, blank=True)
    name = models.CharField(max_length=250, null=True, blank=True)
    uri = models.CharField(max_length=250, null=True, blank=True)

    change_text = models.TextField(verbose_name="Shopping List")
    change_text_original = models.TextField(null=True, blank=True)

    excess_change_text = models.TextField(verbose_name="Excess Items", null=True, blank=True)
    excess_change_text_original = models.TextField(null=True, blank=True)

    published = models.BooleanField(default=False)
    nonpertinent = models.BooleanField(default=False, editable=False)
    tweet_sent = models.DateTimeField(null=True, blank=True, editable=False)

    input_method = models.CharField(max_length=10, choices=NEED_INPUT_TYPES_CHOICES)
    is_categorised = models.BooleanField(default=False, editable=False)

    def clean(self):
        if self.foodbank == None and self.published == True:
            raise ValidationError('Need to set a food bank to publish need')

    def __str__(self):
        return "%s - %s (%s)" % (self.foodbank_name, self.created.strftime("%b %d %Y %H:%M:%S"), self.need_id)

    def created_without_microseconds(self):
        return self.created.replace(microsecond=0)

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def no_items(self):
        if self.change_text == "Unknown" or self.change_text == "Nothing":
            return 0
        else:
            return len(self.change_text.split('\n'))
    
    def categorised_items(self):
        return FoodbankChangeLine.objects.filter(need = self)

    def no_items_categorised(self):
        return len(self.categorised_items())

    def total_items(self):
        return len(self.change_list()) + len(self.excess_list())

    def set_input_method(self):
        if self.distill_id:
            return "scrape"
        else:
            return "typed"
    
    def input_method_human(self):
        if self.input_method == "scrape":
            return "Scraped"
        if self.input_method == "typed":
            return "Typed"
        if self.input_method == "user":
            return "User"
        if self.input_method == "ai":
            return "AI"

    def input_method_emoji(self):
        if self.input_method == "scrape":
            return "🕷️"
        if self.input_method == "typed":
            return "⌨️"
        if self.input_method == "user":
            return "🧑"
        if self.input_method == "ai":
            return "🤖"

    def change_list(self):
        return self.change_text.split("\n")

    def excess_list(self):
        if self.excess_change_text:
            return self.excess_change_text.split("\n")
        else:
            return []

    def clean_change_text(self):
        if self.change_text:
            return unicodedata.normalize('NFKD', self.change_text).encode('ascii', 'ignore')
        else:
            return None

    def last_need(self):

        last_need = FoodbankChange.objects.filter(
            foodbank = self.foodbank,
            created__lt = self.created,
            published = True,
        ).order_by("-created")[:1]

        return last_need

    def diff_from_pub(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].change_list(),
                self.change_list()
            )

    def diff_from_pub_excess(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].excess_list(),
                self.excess_list()
            )

    def last_need_date(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return last_need[0].created
        
    def last_nonpert_need(self):

        last_need = FoodbankChange.objects.filter(
            foodbank = self.foodbank,
            created__lt = self.created,
            nonpertinent = True,
        ).order_by("-created")[:1]

        return last_need
    
    def diff_from_nonpert(self):
        last_need = self.last_nonpert_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].change_list(),
                self.change_list()
            )

    def diff_from_nonpert_excess(self):
        last_need = self.last_nonpert_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].excess_list(),
                self.excess_list()
            )
        
    def get_text(self, text_type = "change"):

        current_language = get_language()
        if self.change_text in ["Facebook", "Unknown", "Nothing"]:
            return self.change_text
        if current_language == "en":
            if text_type == "change":
                return self.change_text
            if text_type == "excess":
                return self.excess_change_text
        else:
            tranlated_text = FoodbankChangeTranslation.objects.get(need = self, language = current_language)
            if text_type == "change":
                return tranlated_text.change_text
            if text_type == "excess":
                return tranlated_text.excess_change_text

    def get_change_text(self):
        return self.get_text("change")

    def get_excess_text(self):
        return self.get_text("excess")
    
    def get_excess_text_list(self):
        return self.get_excess_text().split("\n")

    def save(self, do_translate=False, do_foodbank_save=True, *args, **kwargs):

        if not self.input_method:
            self.input_method = self.set_input_method()

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        self.change_text = clean_foodbank_need_text(self.change_text)
        if self.excess_change_text:
            self.excess_change_text = clean_foodbank_need_text(self.excess_change_text)

        if not self.need_id:
            str_to_hash = "%s%s" % (self.uri, datetime.now())
            str_to_hash = str_to_hash.encode('utf-8')
            need_id = hashlib.sha256(str_to_hash).hexdigest()[:8]
            self.need_id = need_id

        super(FoodbankChange, self).save(*args, **kwargs)

        if self.foodbank and self.published and do_foodbank_save:
            self.foodbank.save(do_geoupdate=False)
        
        if self.published and do_translate:
            for language in LANGUAGES:
                language_code = language[0]
                if language_code != "en":
                    translate_need(language_code, self)
    
    def delete(self, *args, **kwargs):

        FoodbankChangeLine.objects.filter(need = self).delete()
        FoodbankChangeTranslation.objects.filter(need = self).delete()
        super(FoodbankChange, self).delete(*args, **kwargs)
        if self.foodbank:
            if self.published:
                self.foodbank.save(do_geoupdate=False)
            else:
                self.foodbank.save(do_geoupdate=False, do_decache=False)

    class Meta:
        app_label = 'givefood'


class FoodbankChangeTranslation(models.Model):

    need = models.ForeignKey(FoodbankChange, editable=False, on_delete=models.DO_NOTHING)
    foodbank = models.ForeignKey(Foodbank, editable=False, on_delete=models.DO_NOTHING)
    language = models.CharField(max_length = 2)
    change_text = models.TextField()
    excess_change_text = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.foodbank = self.need.foodbank
        super(FoodbankChangeTranslation, self).save(*args, **kwargs)

    class Meta:
        app_label = 'givefood'



class FoodbankChangeLine(models.Model):
    
    need = models.ForeignKey(FoodbankChange, editable=False, on_delete=models.DO_NOTHING)
    foodbank = models.ForeignKey(Foodbank, editable=False, on_delete=models.DO_NOTHING)
    item = models.CharField(max_length=250)
    type = models.CharField(max_length=250, choices=NEED_LINE_TYPES_CHOICES)
    category = models.CharField(max_length=250, choices=ITEM_CATEGORIES_CHOICES)
    group = models.CharField(max_length=250, choices=ITEM_GROUPS_CHOICES, editable=False)
    created = models.DateTimeField(editable=False)

    def save(self, *args, **kwargs):
        self.foodbank = self.need.foodbank
        self.group = ITEM_CATEGORY_GROUPS[self.category]
        self.created = self.need.created
        super(FoodbankChangeLine, self).save(*args, **kwargs)
    
    def __str__(self):
        return "%s - %s" % (self.foodbank, self.item)

    class Meta:
        app_label = 'givefood'


class ParliamentaryConstituency(models.Model):

    name = models.CharField(max_length=50, null=True, blank=True)
    slug = models.CharField(max_length=50, editable=False)
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, null=True, blank=True)

    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP")
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party")
    mp_parl_id = models.IntegerField(verbose_name="MP's ID")
    mp_display_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="MP Display Name", editable=False)
    email = models.EmailField(null=True, blank=True)
    
    centroid = models.CharField(max_length=50)
    latitude = models.FloatField(editable=False)
    longitude = models.FloatField(editable=False)

    boundary_geojson = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def nearby(self):
        return find_parlcons(self.centroid, 5, True)

    def latt(self):
        return float(self.centroid.split(",")[0])

    def long(self):
        return float(self.centroid.split(",")[1])
    
    def mp_photo_url(self):
        return "https://photos.givefood.org.uk/2024-mp/%s.jpg" % (self.mp_parl_id)

    def schema_org(self):

        contains_place = []

        for foodbank in self.foodbank_obj():
            contains_place.append(foodbank.schema_org(as_sub_property = True))
        
        for location in self.location_obj():
            contains_place.append(location.schema_org(as_sub_property = True))

        schema_dict = {
            "@context": "https://schema.org",
            "@type": "AdministrativeArea",
            "name": self.name,
            "containsPlace": contains_place,
            "sameAs": "https://en.wikipedia.org/wiki/%s_(UK_Parliament_constituency)" % (self.name.replace(" ","_")),
        }

        return schema_dict

    def schema_org_str(self):
        return json.dumps(self.schema_org(), indent=4, sort_keys=True)
    
    def boundary_geojson_dict(self):
        boundary_geojson = self.boundary_geojson.strip()
        # remove last char if a comma
        if boundary_geojson[-1:] == ",":
            boundary_geojson = boundary_geojson[:-1]
        else:
            boundary_geojson = boundary_geojson
        return json.loads(boundary_geojson)


    def foodbank_obj(self):
        return Foodbank.objects.select_related("latest_need").filter(parliamentary_constituency = self, is_closed = False)

    def location_obj(self):
        return FoodbankLocation.objects.filter(parliamentary_constituency = self, is_closed = False)

    def foodbanks(self):

        foodbanks = self.foodbank_obj()
        locations = self.location_obj()

        constituency_foodbanks = []
        for foodbank in foodbanks:
            constituency_foodbanks.append({
                "type":"organisation",
                "name":foodbank.name,
                "slug":foodbank.slug,
                "lat_lng":foodbank.latt_long,
                "needs":foodbank.latest_need,
                "url":foodbank.url,
                "shopping_list_url":foodbank.shopping_list_url,
                "gf_url":"/needs/at/%s/" % (foodbank.slug),
            })

        for location in locations:
            constituency_foodbanks.append({
                "type":"location",
                "name":location.name,
                "foodbank_name":location.foodbank_name,
                "slug":location.slug,
                "lat_lng":location.latt_long,
                "needs":location.latest_need(),
                "url":location.foodbank.url,
                "shopping_list_url":location.foodbank.shopping_list_url,
                "gf_url":"/needs/at/%s/%s/" % (location.foodbank_slug, location.slug)
            })

        return constituency_foodbanks

    def foodbank_names(self):

        foodbanks = self.foodbanks()
        foodbank_names = set()

        for foodbank in foodbanks:
            foodbank_names.add(foodbank.get("name"))

        return foodbank_names


    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)

        # LatLong
        self.latitude = self.centroid.split(",")[0]
        self.longitude = self.centroid.split(",")[1]

        # Get MP contact details
        # contact_details = mp_contact_details(self.mp_parl_id)

        # self.mp_display_name = contact_details.get("display_name", None)

        # self.website = contact_details.get("website", None)
        # self.mp_twitter_handle = contact_details.get("twitter", None)
        # self.mp_synopsis = contact_details.get("synopsis", None)
        
        # if not self.email_parl:
        #     self.email_parl = contact_details.get("email_parl", None)
        # self.address_parl = contact_details.get("address_parl", None)
        # self.postcode_parl = contact_details.get("postcode_parl", None)
        # self.lat_lng_parl = contact_details.get("lat_lng_parl", None)
        # self.phone_parl = contact_details.get("phone_parl", None)

        # self.email_con = contact_details.get("email_con", None)
        # self.address_con = contact_details.get("address_con", None)
        # self.postcode_con = contact_details.get("postcode_con", None)
        # self.lat_lng_con = contact_details.get("lat_lng_con", None)
        # self.phone_con = contact_details.get("phone_con", None)

        # # Cleanup phone numbers
        # if self.phone_parl:
        #     self.phone_parl = self.phone_parl.replace(" ","")
        # if self.phone_con:
        #     self.phone_con = self.phone_con.replace(" ","")

        # Resave denormed data
        # foodbanks = Foodbank.objects.filter(parliamentary_constituency = self) 
        # for foodbank in foodbanks:
        #     foodbank.save()

        # locations = FoodbankLocation.objects.filter(parliamentary_constituency = self)
        # for location in locations:
        #     location.save()
        
        super(ParliamentaryConstituency, self).save(*args, **kwargs)

    class Meta:
        app_label = 'givefood'


class GfCredential(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    cred_name = models.CharField(max_length=50)
    cred_value = models.CharField(max_length=255)

    class Meta:
        app_label = 'givefood'


class FoodbankSubscriber(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    last_contacted = models.DateTimeField(editable=False, null=True, blank=True)
    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)
    email = models.EmailField()
    confirmed = models.BooleanField(default=False)

    sub_key = models.CharField(max_length=16, editable=False)
    unsub_key = models.CharField(max_length=16, editable=False)

    class Meta:
        unique_together = ('email', 'foodbank',)
        app_label = 'givefood'

    def foodbank_slug(self):
        return slugify(self.foodbank_name)
    
    def __str__(self):
        return "%s - %s" % (self.email, self.foodbank_name)

    def save(self, *args, **kwargs):

        # Ensure email address is lowercase
        self.email = self.email.lower()

        # Generate sub and unsub keys
        if not self.sub_key:
            salt = get_cred("salt")

            sub_key_str = "sub-%s-%s" % (datetime.now(), salt)
            sub_key_str = sub_key_str.encode('utf-8')

            unsub_key_str = "unsub-%s-%s" % (datetime.now(), salt)
            unsub_key_str = unsub_key_str.encode('utf-8')

            self.sub_key = hashlib.sha256(sub_key_str).hexdigest()[:16]
            self.unsub_key = hashlib.sha256(unsub_key_str).hexdigest()[:16]

        # Denorm food bank name
        self.foodbank_name = self.foodbank.name
        
        super(FoodbankSubscriber, self).save(*args, **kwargs)


class ConstituencySubscriber(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    last_contacted = models.DateTimeField(editable=False, null=True, blank=True)
    email = models.EmailField()
    name = models.CharField(max_length=100, null=True, blank=True)
    parliamentary_constituency = models.ForeignKey(ParliamentaryConstituency, on_delete=models.DO_NOTHING)
    parliamentary_constituency_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    def save(self, *args, **kwargs):

        # Ensure email address is lowercase
        self.email = self.email.lower()

        # Denorm food bank name
        self.parliamentary_constituency_name = self.parliamentary_constituency.name
        
        super(ConstituencySubscriber, self).save(*args, **kwargs)

    class Meta:
        app_label = 'givefood'


class FoodbankHit(models.Model):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    day = models.DateField()
    hits = models.PositiveIntegerField(default=0)


class Place(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    checked = models.DateTimeField(null=True, blank=True)

    gbpnid = models.IntegerField(unique=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    latt_long = models.CharField(max_length=100, null=True, blank=True)
    histcounty = models.CharField(max_length=100, null=True, blank=True)
    adcounty = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    uniauth = models.CharField(max_length=100, null=True, blank=True)
    police = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    type = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return "%s - %s" % (self.gbpnid, self.name)

    def lat(self):
        return float(self.latt_long.split(",")[0])
    
    def lng(self):
        return float(self.latt_long.split(",")[1])

    class Meta:
        app_label = 'givefood'


class PlacePhoto(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    place_id = models.CharField(max_length=1024, null=True, blank=True)
    photo_ref= models.CharField(max_length=1024, unique=True)
    html_attributions = models.TextField()
    blob = models.BinaryField()

    def __str__(self):
        return self.place_id

    class Meta:
        app_label = 'givefood'


class Changelog(models.Model):

    date = models.DateField()
    change = models.TextField()

    class Meta:
        app_label = 'givefood'

    def save(self, *args, **kwargs):

        super(Changelog, self).save(*args, **kwargs)
        decache([reverse("colophon")])

    def delete(self, *args, **kwargs):

        super(Changelog, self).delete(*args, **kwargs)
        decache([reverse("colophon")])


class CharityYear(models.Model):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    date = models.DateField()
    income = models.IntegerField(null=True, blank=True, help_text="Income in pounds")
    expenditure = models.IntegerField(null=True, blank=True, help_text="Expenditure in pounds")