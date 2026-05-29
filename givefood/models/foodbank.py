#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import math
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus

import requests
from furl import furl
from requests import PreparedRequest

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Max, Min
from django.template.defaultfilters import slugify
from django.urls import reverse, translate_url
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from givefood.const.general import (
    COUNTRIES_CHOICES, DAYS_OF_WEEK, DONATION_POINT_COMPANIES_CHOICES,
    DONT_APPEND_FOOD_BANK, FOODBANK_NETWORK_CHOICES, IFAN_SCHEMA,
    PACKAGING_WEIGHT_PC, POSTCODE_REGEX, QUERYSTRING_RUBBISH, SITE_DOMAIN,
    TRUSSELL_TRUST_SCHEMA,
)
from givefood.models.base import (
    EditableModel, PhysicalPlace, TimestampedModel, UUIDModel,
)
from givefood.settings import LANGUAGES
from givefood.utils.cache import decache_async
from givefood.utils.geo import (
    admin_regions_from_postcode, find_foodbanks, geocode, geojson_dict,
    place_has_photo, pluscode, validate_postcode,
)


# Cache bank holidays JSON at module level to eliminate repeated file reads
_BANK_HOLIDAYS_CACHE = None


def _get_bank_holidays():
    """Load and cache bank holidays JSON data."""
    global _BANK_HOLIDAYS_CACHE
    if _BANK_HOLIDAYS_CACHE is None:
        with open("./givefood/data/bank-holidays.json") as f:
            _BANK_HOLIDAYS_CACHE = json.load(f)
    return _BANK_HOLIDAYS_CACHE


class Foodbank(TimestampedModel, EditableModel, UUIDModel, PhysicalPlace):

    # Name
    name = models.CharField(max_length=100)
    alt_name = models.CharField(max_length=100, null=True, blank=True, help_text="E.g. Welsh version of the name")
    slug = models.CharField(max_length=100, editable=False)

    # Overrides PhysicalPlace.country to keep this field editable on Foodbank
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES)

    # Etc
    delivery_address = models.TextField(null=True, blank=True)
    delivery_lat_lng = models.CharField(max_length=50, verbose_name="Delivery latitude, longitude", editable=False, null=True, blank=True)
    network = models.CharField(max_length=50, choices=FOODBANK_NETWORK_CHOICES, null=True, blank=True)
    network_id = models.CharField(max_length=100, null=True, blank=True)
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

    # Social IDs
    facebook_page = models.CharField(max_length=50, null=True, blank=True)
    bankuet_slug = models.CharField(max_length=50, null=True, blank=True)
    fsa_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Food Standards Agency Business ID")

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
    news_url = models.URLField(max_length=200, verbose_name="News URL", null=True, blank=True)
    donation_points_url = models.URLField(max_length=200, verbose_name="Donation points URL", null=True, blank=True)
    locations_url = models.URLField(max_length=200, verbose_name="Locations URL", null=True, blank=True)
    contacts_url = models.URLField(max_length=200, verbose_name="Contacts URL", null=True, blank=True)

    # Booleans
    address_is_administrative = models.BooleanField(default=False, verbose_name="Is the main address just used for administrative purposes?")
    is_closed = models.BooleanField(default=False)
    is_school = models.BooleanField(default=False)

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

    # Map bounds (precomputed bounding box for all locations/donation points)
    bounds_north = models.FloatField(editable=False, null=True, blank=True, help_text="Northern boundary latitude")
    bounds_south = models.FloatField(editable=False, null=True, blank=True, help_text="Southern boundary latitude")
    bounds_east = models.FloatField(editable=False, null=True, blank=True, help_text="Eastern boundary longitude")
    bounds_west = models.FloatField(editable=False, null=True, blank=True, help_text="Western boundary longitude")

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
                    "@type": "Demand",
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

        address_dict = {
            "@type": "PostalAddress",
            "postalCode": self.postcode,
            "addressCountry": self.country,
            "streetAddress": self.address,
        }
        if self.district:
            address_dict["addressLocality"] = self.district

        schema_dict = {
            "@type": "NGO",
            "@id": "%s%s" % (SITE_DOMAIN, reverse("wfbn:foodbank", kwargs={"slug": self.slug})),
            "additionalType": "https://www.wikidata.org/wiki/Q113603",
            "name": self.full_name(),
            "alternateName": self.alt_name,
            "url": self.url,
            "email": self.contact_email,
            "telephone": self.phone_number,
            "address": address_dict,
            "location": {
                "@type": "Place",
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": self.latt(),
                    "longitude": self.long(),
                },
            },
            "identifier": self.charity_number,
            "memberOf": member_of,
        }

        if self.parliamentary_constituency_name:
            schema_dict["areaServed"] = {
                "@type": "AdministrativeArea",
                "name": self.parliamentary_constituency_name,
            }

        # sameAs
        schema_dict["sameAs"] = []
        schema_dict["sameAs"].append(self.url)
        schema_dict["sameAs"].append("%s%s" % (SITE_DOMAIN, reverse("uuid_redir", kwargs={"pk": self.uuid})))
        if self.place_id:
            schema_dict["sameAs"].append("https://www.google.co.uk/maps/place/%s/" % quote_plus(self.plus_code_global))
        if self.charity_number:
            schema_dict["sameAs"].append(self.charity_register_url())
        if self.fsa_id:
            schema_dict["sameAs"].append(self.fsa_url())
        if self.facebook_page:
            schema_dict["sameAs"].append("https://www.facebook.com/%s" % self.facebook_page)

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

    def latt(self):
        return float(self.lat_lng.split(",")[0])

    def long(self):
        return float(self.lat_lng.split(",")[1])

    def full_address(self):
        return "%s\r\n%s" % (self.address, self.postcode)

    def delivery_latt(self):
        return float(self.delivery_lat_lng.split(",")[0])

    def delivery_long(self):
        return float(self.delivery_lat_lng.split(",")[1])

    def has_service_area(self):
        if self.no_locations == 0:
            return False
        locations = FoodbankLocation.objects.filter(foodbank = self).exclude(boundary_geojson__isnull = True).exclude(boundary_geojson = '').count()
        if locations == 0:
            return False
        return True

    def nearby(self):
        return find_foodbanks(self.lat_lng, 10, True)

    def articles(self):
        from givefood.models.articles import FoodbankArticle
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

    CHARITY_DETAIL_COUNTRIES = {"England", "Wales", "Scotland", "Northern Ireland"}

    def has_charity_details(self):
        return self.country in self.CHARITY_DETAIL_COUNTRIES

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
        from givefood.models.needs import FoodbankChange
        return FoodbankChange.objects.filter(foodbank = self).order_by("-created")

    def latest_need_text(self):
        latest_need = self.latest_need
        if latest_need:
            return latest_need.change_text
        else:
            return "Nothing"

    def need_irrelevant(self):
        cut_off = timezone.now() - timedelta(days=180)
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
        from givefood.models.orders import Order
        return Order.objects.filter(foodbank = self).order_by("-delivery_datetime")

    def no_orders(self):
        from givefood.models.orders import Order
        return Order.objects.filter(foodbank = self).count()

    def subscribers(self):
        from givefood.models.subscribers import FoodbankSubscriber
        return FoodbankSubscriber.objects.filter(foodbank = self)

    def webpush_subscribers(self):
        from givefood.models.subscribers import WebPushSubscription
        return WebPushSubscription.objects.filter(foodbank = self)

    def mobile_subscribers(self):
        from givefood.models.subscribers import MobileSubscriber
        return MobileSubscriber.objects.filter(foodbank = self)

    def number_subscribers(self):
        from givefood.models.subscribers import FoodbankSubscriber
        return FoodbankSubscriber.objects.filter(foodbank = self).count()

    def crawl_items(self):
        from givefood.models.analytics import CrawlItem
        return CrawlItem.objects.filter(foodbank = self).order_by("-finish")[:100]

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

    def get_bounds(self):
        """
        Calculate the bounding box for all foodbank locations and donation points.
        Returns a tuple of (north, south, east, west) latitudes/longitudes.
        """
        # FB coordinates as base
        fb_lat = float(self.latitude)
        fb_lng = float(self.longitude)

        # If the foodbank hasn't been saved yet, there can't be any related locations/donation points
        # Django also prevents filtering by unsaved model instances
        if not self.pk:
            return (fb_lat, fb_lat, fb_lng, fb_lng)

        # Locations
        loc_max_lat = FoodbankLocation.objects.filter(foodbank=self).aggregate(Max('latitude'))['latitude__max']
        loc_min_lat = FoodbankLocation.objects.filter(foodbank=self).aggregate(Min('latitude'))['latitude__min']
        loc_max_lng = FoodbankLocation.objects.filter(foodbank=self).aggregate(Max('longitude'))['longitude__max']
        loc_min_lng = FoodbankLocation.objects.filter(foodbank=self).aggregate(Min('longitude'))['longitude__min']

        # Donation Points
        dp_max_lat = FoodbankDonationPoint.objects.filter(foodbank=self).aggregate(Max('latitude'))['latitude__max']
        dp_min_lat = FoodbankDonationPoint.objects.filter(foodbank=self).aggregate(Min('latitude'))['latitude__min']
        dp_max_lng = FoodbankDonationPoint.objects.filter(foodbank=self).aggregate(Max('longitude'))['longitude__max']
        dp_min_lng = FoodbankDonationPoint.objects.filter(foodbank=self).aggregate(Min('longitude'))['longitude__min']

        north = max(x for x in [fb_lat, loc_max_lat, dp_max_lat] if x is not None)
        south = min(x for x in [fb_lat, loc_min_lat, dp_min_lat] if x is not None)
        east = max(x for x in [fb_lng, loc_max_lng, dp_max_lng] if x is not None)
        west = min(x for x in [fb_lng, loc_min_lng, dp_min_lng] if x is not None)

        return (north, south, east, west)


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
        from givefood.models.orders import Order
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
        from givefood.models.orders import Order
        cost = Order.objects.filter(foodbank = self).aggregate(models.Sum('cost'))['cost__sum']
        if not cost:
            return 0
        else:
            return cost / 100

    def total_items(self):
        from givefood.models.orders import Order
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
        from givefood.models.articles import FoodbankArticle
        return FoodbankArticle.objects.filter(foodbank = self, published_date__gte = timezone.now() - timedelta(days=28)).order_by("-published_date")

    class Meta:
        app_label = 'givefood'

    def delete(self, *args, **kwargs):

        from givefood.models.analytics import CrawlItem, FoodbankHit
        from givefood.models.articles import FoodbankArticle
        from givefood.models.needs import (
            FoodbankChange, FoodbankChangeLine, FoodbankDiscrepancy,
        )
        from givefood.models.operations import CharityYear
        from givefood.models.orders import Order
        from givefood.models.subscribers import FoodbankSubscriber

        FoodbankHit.objects.filter(foodbank = self).delete()
        FoodbankChangeLine.objects.filter(foodbank = self).delete()
        FoodbankChange.objects.filter(foodbank = self).delete()
        FoodbankLocation.objects.filter(foodbank = self).delete()
        FoodbankArticle.objects.filter(foodbank = self).delete()
        FoodbankSubscriber.objects.filter(foodbank = self).delete()
        FoodbankDonationPoint.objects.filter(foodbank = self).delete()
        FoodbankDiscrepancy.objects.filter(foodbank = self).delete()
        CharityYear.objects.filter(foodbank = self).delete()
        CrawlItem.objects.filter(foodbank = self).delete()

        # Unassign orders from this foodbank
        Order.objects.filter(foodbank = self).update(foodbank=None)

        super(Foodbank, self).delete(*args, **kwargs)


    def save(self, do_decache=True, do_geoupdate=True, *args, **kwargs):

        from givefood.models.needs import FoodbankChange
        from givefood.models.political import ParliamentaryConstituency

        logging.info("Saving food bank %s" % self.name)

        # Slugify name
        self.slug = slugify(self.name)

        # LatLong
        self.latitude = self.lat_lng.split(",")[0]
        self.longitude = self.lat_lng.split(",")[1]

        # Footprint
        self.footprint = self.get_footprint()

        # Map bounds
        bounds = self.get_bounds()
        self.bounds_north = bounds[0]
        self.bounds_south = bounds[1]
        self.bounds_east = bounds[2]
        self.bounds_west = bounds[3]

        # Cleanup phone numbers
        if self.phone_number:
            self.phone_number = self.phone_number.replace(" ","")
        if self.secondary_phone_number:
            self.secondary_phone_number = self.secondary_phone_number.replace(" ","")

        if self.delivery_address:
            self.delivery_lat_lng = geocode(self.delivery_address)
        else:
            self.delivery_lat_lng = None

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

            pluscodes = pluscode(self.lat_lng, self.district)
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
                reverse("index"),
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

            # Markdown URLs
            prefixes.append(reverse("wfbn-md:md_foodbank", kwargs={"slug":self.slug}))

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
            urls.append(reverse("md_index"))
            decache_async.enqueue(urls, prefixes)


class FoodbankLocation(EditableModel, UUIDModel, PhysicalPlace):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False)
    foodbank_slug = models.CharField(max_length=100, editable=False)
    foodbank_network = models.CharField(max_length=50, editable=False)
    foodbank_phone_number = models.CharField(max_length=50, null=True, blank=True, editable=False)
    foodbank_email = models.EmailField(editable=False)
    is_closed = models.BooleanField(default=False)

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, editable=False)

    # Overrides PhysicalPlace.address / postcode to keep them optional on FoodbankLocation
    address = models.TextField(null=True, blank=True)
    postcode = models.CharField(max_length=9, null=True, blank=True, validators=[
        RegexValidator(
            regex = POSTCODE_REGEX,
            message = "Not a valid postcode",
            code = "invalid_postcode",
        ),
    ])

    is_donation_point = models.BooleanField(default=False)
    is_mobile = models.BooleanField(default=False)

    boundary_geojson = models.TextField(null=True, blank=True)

    phone_number = models.CharField(max_length=50, null=True, blank=True, help_text="If different to the main location")
    email = models.EmailField(null=True, blank=True, help_text="If different to the main location")

    modified = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
       unique_together = ('foodbank', 'name',)
       app_label = 'givefood'
       indexes = [
           models.Index(fields=['foodbank', 'name']),
       ]

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
                    "@type": "Demand",
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
            "@id": "%s%s" % (SITE_DOMAIN, reverse("wfbn:foodbank_location", kwargs={"slug": self.foodbank_slug, "locslug": self.slug})),
            "name": self.full_name(),
            "url": self.foodbank.url,
            "email": self.email_or_foodbank_email(),
            "telephone": self.phone_or_foodbank_phone(),
            "location": {
                "@type": "Place",
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

        # Only add address if we have address or postcode
        if self.address or self.postcode:
            address_dict = {
                "@type": "PostalAddress",
                "addressCountry": self.country,
            }
            if self.postcode:
                address_dict["postalCode"] = self.postcode
            if self.address:
                address_dict["streetAddress"] = self.address
            if self.district:
                address_dict["addressLocality"] = self.district
            schema_dict["address"] = address_dict

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
        if self.address and self.postcode:
            return "%s\r\n%s" % (self.address, self.postcode)
        elif self.address:
            return self.address
        elif self.postcode:
            return self.postcode
        else:
            return ""

    def latt(self):
        return float(self.lat_lng.split(",")[0])

    def long(self):
        return float(self.lat_lng.split(",")[1])

    def boundary_geojson_dict(self):
        return geojson_dict(self.boundary_geojson)

    def is_area(self):
        return bool(self.boundary_geojson)

    def delete(self, *args, **kwargs):

        super(FoodbankLocation, self).delete(*args, **kwargs)
        # Resave the parent food bank
        self.foodbank.save(do_geoupdate=False)

    def save(self, do_geoupdate=True, do_foodbank_resave=True, *args, **kwargs):

        from givefood.models.political import ParliamentaryConstituency

        logging.info("Saving food bank location %s" % self.name)

        # Slugify name
        self.slug = slugify(self.name)

        # LatLong
        self.latitude = self.lat_lng.split(",")[0]
        self.longitude = self.lat_lng.split(",")[1]

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

            # Update politics - only if postcode is provided
            if self.postcode:
                regions = admin_regions_from_postcode(self.postcode)
                self.country = regions.get("country", None) or self.foodbank.country
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
            else:
                # If no postcode, set country from foodbank
                self.country = self.foodbank.country

            pluscodes = pluscode(self.lat_lng, self.district)
            self.plus_code_compound = pluscodes["compound"]
            self.plus_code_global = pluscodes["global"]

        super(FoodbankLocation, self).save(*args, **kwargs)

        # Resave the parent food bank
        if do_foodbank_resave:
            self.foodbank.save(do_geoupdate=False)


class FoodbankDonationPoint(EditableModel, UUIDModel, PhysicalPlace):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False)
    foodbank_slug = models.CharField(max_length=100, editable=False)
    foodbank_network = models.CharField(max_length=50, editable=False)
    is_closed = models.BooleanField(default=False)

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, editable=False)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    opening_hours = models.TextField(null=True, blank=True)
    wheelchair_accessible = models.BooleanField(null=True, blank=True)
    url = models.URLField(max_length=1024, verbose_name="URL", null=True, blank=True)
    in_store_only = models.BooleanField(default=False)

    company = models.CharField(max_length=100, null=True, blank=True, choices=DONATION_POINT_COMPANIES_CHOICES)
    company_slug = models.CharField(max_length=100, null=True, blank=True, editable=False)
    store_id = models.CharField(max_length=64, null=True, blank=True, help_text="The company's store ID")

    notes = models.TextField(null=True, blank=True, help_text="These notes are public")

    modified = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
       unique_together = ('foodbank', 'name',)
       app_label = 'givefood'
       indexes = [
           models.Index(fields=['foodbank', 'name']),
       ]

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

    def full_address(self):
        return "%s\r\n%s" % (self.address, self.postcode)

    def latt(self):
        return float(self.lat_lng.split(",")[0])

    def long(self):
        return float(self.lat_lng.split(",")[1])

    def schema_org(self):

        needs = self.foodbank.latest_need_text()
        seeks = []

        if needs != "Nothing" and needs != "Unknown" and needs != "Facebook":
            need_list = needs.splitlines()
            for need in need_list:
                seeks.append({
                    "@type": "Demand",
                    "itemOffered": {
                        "@type":"Product",
                        "name":need,
                    }
                })

        address_dict = {
            "@type": "PostalAddress",
            "postalCode": self.postcode,
            "addressCountry": self.country,
            "streetAddress": self.address,
        }
        if self.district:
            address_dict["addressLocality"] = self.district

        schema_dict = {
            "@context": "https://schema.org",
            "@type": "Place",
            "name": self.name,
            "url": self.url,
            "telephone": self.phone_number,
            "isAccessibleForFree": self.wheelchair_accessible,
            "address": address_dict,
            "location": {
                "@type": "Place",
                "geo": {
                    "@type": "GeoCoordinates",
                    "latitude": self.latt(),
                    "longitude": self.long(),
                },
            },
            "parentOrganization": self.foodbank.schema_org(as_sub_property = True),
        }

        if self.opening_hours:
            schema_org_days = {
                "Monday": "https://schema.org/Monday",
                "Tuesday": "https://schema.org/Tuesday",
                "Wednesday": "https://schema.org/Wednesday",
                "Thursday": "https://schema.org/Thursday",
                "Friday": "https://schema.org/Friday",
                "Saturday": "https://schema.org/Saturday",
                "Sunday": "https://schema.org/Sunday",
            }
            hours_specs = []
            days = self.opening_hours.split("\n")
            for day_text in days:
                day_parts = day_text.split(": ", 1)
                if len(day_parts) < 2:
                    continue
                day_name = day_parts[0].strip()
                hours = day_parts[1].strip()
                if "Closed" in hours or day_name not in schema_org_days:
                    continue
                time_parts = re.split(r"\s*[–—\-]\s*", hours)
                if len(time_parts) != 2:
                    continue
                try:
                    open_time = datetime.strptime(time_parts[0].strip(), "%I:%M %p").strftime("%H:%M")
                    close_time = datetime.strptime(time_parts[1].strip(), "%I:%M %p").strftime("%H:%M")
                except ValueError:
                    continue
                hours_specs.append({
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": schema_org_days[day_name],
                    "opens": open_time,
                    "closes": close_time,
                })
            if hours_specs:
                schema_dict["openingHoursSpecification"] = hours_specs

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

        bank_holidays_data = _get_bank_holidays()

        bank_holidays = None
        if self.country == "England":
            bank_holidays = bank_holidays_data["england-and-wales"]
        elif self.country == "Wales":
            bank_holidays = bank_holidays_data["england-and-wales"]
        elif self.country == "Scotland":
            bank_holidays = bank_holidays_data["scotland"]
        elif self.country == "Northern Ireland":
            bank_holidays = bank_holidays_data["northern-ireland"]

        if not bank_holidays:
            bank_holidays = {}

        bank_holidays = bank_holidays.get("events", None)
        if bank_holidays:
            for idx, holiday in enumerate(bank_holidays):
                if not isinstance(holiday["date"], date):
                    bank_holidays[idx]["date"] = datetime.strptime(holiday["date"], "%Y-%m-%d").date()

        today = date.today()
        day_dates = []
        for day_offset in range(7):
            day_date = today + timedelta(days=day_offset)
            day_dates.append(day_date)

        relative_days = []

        for idx, day_date in enumerate(day_dates):
            day_of_week = day_date.weekday()
            day_text = days[day_of_week]
            day_parts = day_text.split(": ", 1)
            day_name = day_parts[0] if len(day_parts) > 1 else day_text
            hours = day_parts[1] if len(day_parts) > 1 else ""
            relative_days.append({
                "text": day_text,
                "day_name": day_name,
                "hours": hours,
                "date": day_date,
                "is_closed": "Closed" in day_text,
                "is_today": day_date == today,
            })
            if bank_holidays:
                relative_days[idx]["holiday"] = next((holiday for holiday in bank_holidays if holiday["date"] == day_date), None)

        return relative_days

    @property
    def is_open(self):

        if not self.opening_hours:
            return None

        now = timezone.now()
        day_of_week = now.weekday()
        days = self.opening_hours.split("\n")
        day_text = days[day_of_week]

        if "Closed" in day_text:
            return False

        day_parts = day_text.split(": ", 1)
        if len(day_parts) < 2:
            return None

        hours = day_parts[1]
        time_parts = re.split(r"\s*[–—\-]\s*", hours)
        if len(time_parts) != 2:
            return None

        try:
            open_time = datetime.strptime(time_parts[0].strip(), "%I:%M %p").time()
            close_time = datetime.strptime(time_parts[1].strip(), "%I:%M %p").time()
        except ValueError:
            return None

        current_time = now.time()
        if close_time <= open_time:
            return current_time >= open_time
        return open_time <= current_time < close_time

    def clean(self):
        if self.postcode:
            lat_lngs = []
            for location in self.foodbank.locations():
                lat_lngs.append(location.lat_lng)
            lat_lngs.append(self.foodbank.lat_lng)
            lat_lngs.append(self.foodbank.delivery_lat_lng)

            if self.lat_lng in lat_lngs:
                raise ValidationError("Location can't be the same as the food bank or one of it's locations")

            if not validate_postcode(self.postcode):
                raise ValidationError("Invalid postcode")


    def delete(self, *args, **kwargs):

        super(FoodbankDonationPoint, self).delete(*args, **kwargs)
        # Resave the parent food bank
        self.foodbank.save(do_geoupdate=False)

    def save(self, do_geoupdate=True, do_foodbank_resave=True, do_photo_update=True, *args, **kwargs):

        from givefood.models.political import ParliamentaryConstituency

        # Slugify
        self.slug = slugify(self.name)
        if self.company:
            self.company_slug = slugify(self.company)

        # LatLong
        self.latitude = self.lat_lng.split(",")[0]
        self.longitude = self.lat_lng.split(",")[1]

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

        # Populate store id
        if self.company == "Tesco" and self.url:
            match = re.search(r'stc\*(\d+)', self.url)
            if match:
                self.store_id = match.group(1)
            else:
                self.store_id = None
        if self.company == "Sainsbury's" and self.url:
            match = re.search(r'/(\d+)/', self.url)
            if match:
                self.store_id = match.group(1)
            else:
                self.store_id = None

        if self.company == "Asda" and self.url:
            page_request = requests.get(self.url)
            if page_request.status_code == 200:
                page_html = page_request.text
                match = re.search(r'id":"(\d+)",', page_html)
                if match:
                    self.store_id = match.group(1)
                else:
                    self.store_id = None

        if self.company == "Waitrose" and self.url:
            match = re.search(r'utm_content=(\d+)', self.url)
            if match:
                self.store_id = match.group(1)
            else:
                self.store_id = None

        if self.company == "Morrisons" and self.url:
            match = re.search(r'/(\d+)', self.url)
            if match:
                self.store_id = match.group(1)
            else:
                self.store_id = None

        if do_geoupdate:
            # Update politics
            regions = admin_regions_from_postcode(self.postcode)
            self.country = regions.get("country", None) or self.foodbank.country
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

            pluscodes = pluscode(self.lat_lng, self.district)
            self.plus_code_compound = pluscodes["compound"]
            self.plus_code_global = pluscodes["global"]

        super(FoodbankDonationPoint, self).save(*args, **kwargs)

        # Decache donation points API
        decache_async.enqueue(prefixes=["/api/3/donationpoints/"])

        # Resave the parent food bank
        if do_foodbank_resave:
            self.foodbank.save(do_geoupdate=False)
