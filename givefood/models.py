#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib, unicodedata, logging, json
from datetime import datetime, timedelta

from google.appengine.api import memcache
from google.appengine.ext import deferred

from django.db import models
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError

from const.general import DELIVERY_HOURS_CHOICES, COUNTRIES_CHOICES, DELIVERY_PROVIDER_CHOICES, FOODBANK_NETWORK_CHOICES, PACKAGING_WEIGHT_PC, FB_MC_KEY
from const.general import TRUSSELL_TRUST_SCHEMA, IFAN_SCHEMA
from func import parse_tesco_order_text, parse_sainsburys_order_text, clean_foodbank_need_text, admin_regions_from_postcode, mp_from_parlcon, geocode, make_url_friendly, find_foodbanks, mpid_from_name, get_cred, diff_html, mp_contact_details, find_parlcons


class Foodbank(models.Model):

    name = models.CharField(max_length=100)
    alt_name = models.CharField(max_length=100, null=True, blank=True, help_text="E.g. Welsh version of the name")
    slug = models.CharField(max_length=100, editable=False)
    address = models.TextField()
    postcode = models.CharField(max_length=9)
    delivery_address = models.TextField(null=True, blank=True)
    latt_long = models.CharField(max_length=50, verbose_name="Latitude, Longitude")
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES)
    network = models.CharField(max_length=50, choices=FOODBANK_NETWORK_CHOICES, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    charity_number = models.CharField(max_length=50,null=True, blank=True)
    charity_just_foodbank = models.BooleanField(default=False, verbose_name="Charity just foodbank", help_text="Tick this if the charity is purely used for the foodbank, rather than other uses such as a church")

    parliamentary_constituency = models.ForeignKey("ParliamentaryConstituency", null=True, blank=True, editable=False)
    parliamentary_constituency_name = models.CharField(max_length=50, null=True, blank=True, editable=False)
    parliamentary_constituency_slug = models.CharField(max_length=50, null=True, blank=True, editable=False)
    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP", editable=False)
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party", editable=False)
    mp_parl_id = models.IntegerField(verbose_name="MP's ID", null=True, blank=True, editable=False)

    county = models.CharField(max_length=50, null=True, blank=True, editable=False)
    district = models.CharField(max_length=50, null=True, blank=True, editable=False)
    ward = models.CharField(max_length=50, null=True, blank=True, editable=False)
    lsoa = models.CharField(max_length=50, null=True, blank=True, editable=False)
    msoa = models.CharField(max_length=50, null=True, blank=True, editable=False)

    facebook_page = models.CharField(max_length=50, null=True, blank=True)
    twitter_handle = models.CharField(max_length=50, null=True, blank=True)
    bankuet_slug = models.CharField(max_length=50, null=True, blank=True)

    contact_email = models.EmailField()
    notification_email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    secondary_phone_number = models.CharField(max_length=20, null=True, blank=True)
    delivery_phone_number = models.CharField(max_length=20, null=True, blank=True)

    url = models.URLField(max_length=200, verbose_name="URL")
    shopping_list_url = models.URLField(max_length=200, verbose_name="Shopping list URL")
    rss_url = models.URLField(max_length=200, verbose_name="RSS feed URL", null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    last_order = models.DateField(editable=False, null=True)
    last_social_media_check = models.DateTimeField(editable=False, null=True)
    last_need = models.DateTimeField(editable=False, null=True)

    no_locations = models.IntegerField(editable=False, default=0)

    class Search:
         fields = [
             "name",
         ]

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

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
            if self.network == "Trussell Trust":
                member_of = TRUSSELL_TRUST_SCHEMA
            if self.network == "IFAN":
                member_of = IFAN_SCHEMA

        schema_dict = {
            "@type": "NGO",
            "name": "%s Food Bank" % (self.name),
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
        if not as_sub_property:
            schema_dict["@context"] = "https://schema.org"
            if seeks:
                schema_dict["seeks"] = seeks
        return schema_dict

    def schema_org_str(self):
        return json.dumps(self.schema_org(), indent=4, sort_keys=True)

    def friendly_url(self):
        return make_url_friendly(self.url)

    def friendly_shopping_list_url(self):
        return make_url_friendly(self.shopping_list_url)

    def latt(self):
        return float(self.latt_long.split(",")[0])

    def long(self):
        return float(self.latt_long.split(",")[1])

    def full_address(self):
        return "%s\r\n%s" % (self.address, self.postcode)

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

    def needs(self):
        return FoodbankChange.objects.filter(foodbank = self).order_by("-created")

    def latest_need(self):
        try:
            need = FoodbankChange.objects.filter(foodbank = self, published = True).latest("created")
            return need
        except FoodbankChange.DoesNotExist:
            return None

    def latest_need_text(self):
        latest_need = self.latest_need()
        if latest_need:
            return latest_need.change_text
        else:
            return "Nothing"
    
    def need_irrelevant(self):
        cut_off = datetime.now() - timedelta(days=180)
        return self.last_need.replace(tzinfo=None) < cut_off

    def latest_need_id(self):

        latest_need = self.latest_need()
        if latest_need:
            return latest_need.need_id
        else:
            return None

    def latest_need_date(self):
        latest_need = self.latest_need()
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
        return latest_need_text.count('\n')+1

    def has_needs(self):
        need_text = self.latest_need_text()
        if need_text == "Nothing" or need_text == "Unknown":
            return False
        else:
            return True

    def orders(self):
        return Order.objects.filter(foodbank = self).order_by("-delivery_datetime")

    def no_orders(self):
        return len(self.orders())

    def subscribers(self):
        return FoodbankSubscriber.objects.filter(foodbank = self)

    def no_subscribers(self):
        return len(self.subscribers())

    def get_no_locations(self):
        return len(self.locations())

    def total_weight(self):
        total_weight = float(0)
        orders = self.orders()
        for order in orders:
            total_weight = total_weight + order.weight
        return total_weight

    def total_weight_kg(self):
        return self.total_weight() / 1000

    def total_weight_kg_pkg(self):
        return self.total_weight_kg() * PACKAGING_WEIGHT_PC

    def total_cost(self):
        total_cost = float(0)
        orders = self.orders()
        for order in orders:
            total_cost = total_cost + order.cost
        return total_cost / 100

    def total_items(self):
        total_items = 0
        orders = self.orders()
        for order in orders:
            total_items = total_items + order.no_items
        return total_items

    def locations(self):
        return FoodbankLocation.objects.filter(foodbank = self).order_by("name")

    def get_absolute_url(self):
        return "/admin/foodbank/%s/" % (self.slug)

    def bankuet_url(self):
        if self.bankuet_slug:
            return "https://www.bankuet.co.uk/%s/?utm_source=givefood_org_uk&utm_medium=search&utm_campaign=needs" % (self.bankuet_slug)
        else:
            return None

    def save(self, *args, **kwargs):

        logging.info("Saving food bank %s" % self.name)

        # Slugify name
        self.slug = slugify(self.name)

        # Cleanup phone numbers
        if self.phone_number:
            self.phone_number = self.phone_number.replace(" ","")
        if self.secondary_phone_number:
            self.secondary_phone_number = self.secondary_phone_number.replace(" ","")

        # Update politics
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
            self.mp = self.parliamentary_constituency.mp
            self.mp_party = self.parliamentary_constituency.mp_party
            self.mp_parl_id = self.parliamentary_constituency.mp_parl_id
        except ParliamentaryConstituency.DoesNotExist: 
            logging.info("Didn't get parl con %s" % regions.get("parliamentary_constituency", None))
            self.parliamentary_constituency = None

        # Cache number of locations
        self.no_locations = self.get_no_locations()

        # Cache last need date
        try:
            last_need = FoodbankChange.objects.filter(foodbank = self).latest("created")
            self.last_need = last_need.created
        except FoodbankChange.DoesNotExist:
            self.last_need = None

        super(Foodbank, self).save(*args, **kwargs)

        # Delete the now stale memcache entry
        memcache.delete(FB_MC_KEY)


class FoodbankLocation(models.Model):

    foodbank = models.ForeignKey(Foodbank)
    foodbank_name = models.CharField(max_length=100, editable=False)
    foodbank_slug = models.CharField(max_length=100, editable=False)
    foodbank_network = models.CharField(max_length=50, editable=False)
    foodbank_phone_number = models.CharField(max_length=20, null=True, blank=True, editable=False)
    foodbank_email = models.EmailField(editable=False)

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, editable=False)
    address = models.TextField()
    postcode = models.CharField(max_length=9)
    latt_long = models.CharField(max_length=50, verbose_name="Latt,Long")
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, editable=False)

    phone_number = models.CharField(max_length=20, null=True, blank=True, help_text="If different to the main location")
    email = models.EmailField(null=True, blank=True, help_text="If different to the main location")

    parliamentary_constituency = models.ForeignKey("ParliamentaryConstituency", null=True, blank=True, editable=False)
    parliamentary_constituency_name = models.CharField(max_length=50, null=True, blank=True, editable=False)
    parliamentary_constituency_slug = models.CharField(max_length=50, null=True, blank=True, editable=False)
    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP", editable=False)
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party", editable=False)
    mp_parl_id = models.IntegerField(verbose_name="MP's ID", null=True, blank=True, editable=False)

    county = models.CharField(max_length=50, null=True, blank=True, editable=False)
    district = models.CharField(max_length=50, null=True, blank=True, editable=False)
    ward = models.CharField(max_length=50, null=True, blank=True, editable=False)
    lsoa = models.CharField(max_length=50, null=True, blank=True, editable=False)
    msoa = models.CharField(max_length=50, null=True, blank=True, editable=False)

    class Meta:
       unique_together = ('foodbank', 'name',)

    def __str__(self):
        return self.name
    
    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/admin/foodbank/%s/location/%s/edit/" % (self.foodbank.slug, self.slug)

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
            if self.foodbank_network == "Trussell Trust":
                member_of = TRUSSELL_TRUST_SCHEMA
            if self.foodbank_network == "IFAN":
                member_of = IFAN_SCHEMA

        schema_dict = {
            "@context": "https://schema.org",
            "@type": "NGO",
            "name": "%s Food Bank" % (self.full_name()),
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
        return "%s, %s" % (self.name, self.foodbank_name)
        
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
        return self.foodbank.latest_need()

    def full_address(self):
        return "%s\r\n%s" % (self.address, self.postcode)

    def latt(self):
        return float(self.latt_long.split(",")[0])

    def long(self):
        return float(self.latt_long.split(",")[1])

    def save(self, *args, **kwargs):

        logging.info("Saving food bank location %s" % self.name)

        # Slugify name
        self.slug = slugify(self.name)

        # Cache foodbank details
        self.foodbank_name = self.foodbank.name
        self.foodbank_slug = self.foodbank.slug
        self.foodbank_network = self.foodbank.network
        self.foodbank_phone_number = self.foodbank.phone_number
        self.foodbank_email = self.foodbank.contact_email

        # Cleanup phone number
        if self.phone_number:
            self.phone_number = self.phone_number.replace(" ","")

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
            self.mp = self.parliamentary_constituency.mp
            self.mp_party = self.parliamentary_constituency.mp_party
            self.mp_parl_id = self.parliamentary_constituency.mp_parl_id
        except ParliamentaryConstituency.DoesNotExist: 
            logging.info("Didn't get parl con %s" % regions.get("parliamentary_constituency", None))
            self.parliamentary_constituency = None

        super(FoodbankLocation, self).save(*args, **kwargs)

        # Resave the parent food bank, to update location count
        self.foodbank.save()


class Order(models.Model):

    order_id = models.CharField(max_length=50, editable=False)
    foodbank = models.ForeignKey(Foodbank)
    foodbank_name = models.CharField(max_length=100, editable=False)
    items_text = models.TextField()
    need = models.ForeignKey("FoodbankChange", null=True, blank=True)
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, editable=False)
    order_group = models.ForeignKey("OrderGroup", null=True, blank=True)

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
    cost = models.PositiveIntegerField(editable=False) #pence
    no_lines = models.PositiveIntegerField(editable=False)
    no_items = models.PositiveIntegerField(editable=False)

    class Meta:
       unique_together = ('foodbank', 'delivery_date',)

    def __str__(self):
        return self.order_id

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def delivery_hour_end(self):
        return self.delivery_hour + 1

    def natural_cost(self):
        return float(self.cost/100)

    def weight_kg(self):
        return self.weight/1000

    def weight_kg_pkg(self):
        return self.weight_kg() * PACKAGING_WEIGHT_PC

    def delete(self, *args, **kwargs):

        OrderLine.objects.filter(order = self).delete()
        super(Order, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        # Generate ID
        self.order_id = "gf-%s-%s-%s" % (self.foodbank.slug,slugify(self.delivery_provider),str(self.delivery_date))

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

        #denorm foodbank name & country
        self.foodbank_name = self.foodbank.name
        self.country = self.foodbank.country

        super(Order, self).save(*args, **kwargs)

        # Delete all the existing orderlines
        OrderLine.objects.filter(order = self).delete()

        if self.delivery_provider == "Tesco" or self.delivery_provider == "Costco" or self.delivery_provider == "Pedal Me":
            order_lines = parse_tesco_order_text(self.items_text)
        elif self.delivery_provider == "Sainsbury's":
            order_lines = parse_sainsburys_order_text(self.items_text)


        order_weight = 0
        order_calories = 0
        order_cost = 0
        order_items = 0

        for order_line in order_lines:

            line_calories = 0
            line_weight = 0
            line_cost = 0

            line_weight = order_line.get("weight") * order_line.get("quantity")
            order_weight = order_weight + line_weight

            if order_line.get("calories"):
                line_calories = order_line.get("calories")
                order_calories = order_calories + line_calories

            if self.delivery_provider == "Tesco":
                line_cost = order_line.get("item_cost") * order_line.get("quantity")
            elif self.delivery_provider == "Sainsbury's":
                line_cost = order_line.get("item_cost")
            
            order_cost = order_cost + line_cost

            order_items = order_items + order_line.get("quantity")

            new_order_line = OrderLine(
                foodbank = self.foodbank,
                order = self,
                name = order_line.get("name"),
                quantity = order_line.get("quantity"),
                item_cost = order_line.get("item_cost"),
                line_cost = line_cost,
                weight = line_weight,
                calories = order_line.get("calories"),
            )
            new_order_line.save()

        self.weight = order_weight
        self.calories = order_calories
        self.cost = order_cost
        self.no_lines = len(order_lines)
        self.no_items = order_items

        super(Order, self).save(*args, **kwargs)

        # Update last order date on foodbank
        self.foodbank.last_order = self.delivery_datetime
        self.foodbank.save()

    def lines(self):
        return OrderLine.objects.filter(order = self).order_by("-weight")


class OrderLine(models.Model):

    foodbank = models.ForeignKey(Foodbank)
    order = models.ForeignKey(Order)

    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    item_cost = models.PositiveIntegerField() #pence
    line_cost = models.PositiveIntegerField()

    weight = models.PositiveIntegerField(editable=False,null=True)
    calories = models.PositiveIntegerField(editable=False,null=True)

    def weight_kg(self):
        return self.weight/1000


class OrderItem(models.Model):

    name = models.CharField(max_length=100, unique=True)
    slug = models.CharField(max_length=100, editable=False)
    calories = models.PositiveIntegerField(help_text="Per 100g")
    tesco_image_id = models.CharField(max_length=100, null=True, blank=True)
    sainsburys_image_id = models.CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)
        super(OrderItem, self).save(*args, **kwargs)


class OrderGroup(models.Model):

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, editable=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    def orders(self):
        return Order.objects.filter(order_group = self).order_by("-delivery_datetime")

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)
        super(OrderGroup, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class FoodbankArticle(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    foodbank = models.ForeignKey(Foodbank, null=True, blank=True)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    published_date = models.DateTimeField(editable=False)
    title = models.CharField(max_length=250)
    url = models.CharField(max_length=250, unique=True)

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def save(self, *args, **kwargs):

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        super(FoodbankArticle, self).save(*args, **kwargs)



class FoodbankChange(models.Model):

    # This is known on the frontend as a 'need'

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    need_id = models.CharField(max_length=8, editable=False)

    foodbank = models.ForeignKey(Foodbank, null=True, blank=True)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    distill_id = models.CharField(max_length=250, null=True, blank=True)
    name = models.CharField(max_length=250, null=True, blank=True)
    uri = models.CharField(max_length=250, null=True, blank=True)
    change_text = models.TextField(verbose_name="Shopping List")
    change_text_original = models.TextField(null=True, blank=True)
    published = models.BooleanField(default=False)
    tweet_sent = models.DateTimeField(null=True, blank=True, editable=False)

    input_method = models.CharField(max_length=10)

    class Search:
         fields = [
             "change_text",
         ]

    def clean(self):
        if self.foodbank == None and self.published == True:
            raise ValidationError('Need to set a food bank to publish need')

    def __str__(self):
        return "%s - %s (%s)" % (self.foodbank_name, self.created.strftime("%b %d %Y %H:%M:%S"), self.need_id)

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def no_items(self):
        if self.change_text == "Unknown" or self.change_text == "Nothing":
            return 0
        else:
            return len(self.change_text.split('\n'))

    def set_input_method(self):
        if self.distill_id:
            return "scrape"
        else:
            return "typed"

    def change_list(self):
        return self.change_text.split("\n")

    def clean_change_text(self):
        if self.change_text:
            return unicodedata.normalize('NFKD', self.change_text).encode('ascii', 'ignore')
        else:
            return None

    def last_need(self):

        last_need = FoodbankChange.objects.filter(
            foodbank = self.foodbank,
            created__lt = self.created,
        ).order_by("-created")[:1]

        return last_need

    def diff_from_last(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].change_list(),
                self.change_list()
            )


    def last_need_date(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return last_need[0].created

    def save(self, *args, **kwargs):

        if not self.input_method:
            self.input_method = self.set_input_method()

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        self.change_text = clean_foodbank_need_text(self.change_text)

        if not self.need_id:
            need_id = hashlib.sha256("%s%s" % (self.uri, datetime.now())).hexdigest()[:8]
            self.need_id = need_id

        super(FoodbankChange, self).save(*args, **kwargs)

        if self.foodbank:
            deferred.defer(self.foodbank.save)


class ApiFoodbankSearch(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    query_type = models.CharField(max_length=8)
    query = models.CharField(max_length=255)
    nearest_foodbank = models.IntegerField()
    latt_long = models.CharField(max_length=50, verbose_name="Latt,Long", null=True, blank=True)

    admin_district = models.CharField(max_length=50, null=True, blank=True)
    admin_ward = models.CharField(max_length=50, null=True, blank=True)
    lsoa = models.CharField(max_length=50, null=True, blank=True)
    msoa = models.CharField(max_length=50, null=True, blank=True)
    parliamentary_constituency = models.CharField(max_length=50, null=True, blank=True)

    def wfbn_url(self):
        if self.query_type == "latt_long":
            query_type == "lat_lng"
        else:
            query_type = "address"

        return "https://www.givefood.org.uk/needs/?%s=%s" % (query_type, self.query)

    def latt(self):
        if self.latt_long:
            return float(self.latt_long.split(",")[0])
        else:
            return

    def long(self):
        if self.latt_long:
            return float(self.latt_long.split(",")[1])
        else:
            return

    def save(self, *args, **kwargs):

        if not self.latt_long:
            if self.query_type == "lattlong":
                self.latt_long = self.query
            else:
                self.latt_long = geocode(self.query)

        super(ApiFoodbankSearch, self).save(*args, **kwargs)


class ParliamentaryConstituency(models.Model):

    name = models.CharField(max_length=50, null=True, blank=True)
    slug = models.CharField(max_length=50, editable=False)
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, null=True, blank=True)

    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP")
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party")
    mp_parl_id = models.IntegerField(verbose_name="MP's ID")

    mp_display_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="MP Display Name", editable=False)
    mp_synopsis = models.TextField(null=True, blank=True, editable=False)
    mp_twitter_handle = models.CharField(max_length=50, null=True, blank=True)
    mp_website = models.URLField(max_length=250, null=True, blank=True, editable=False)
    
    centroid = models.CharField(max_length=50)

    # Parlimentary details
    email_parl = models.EmailField(null=True, blank=True)
    address_parl = models.TextField(null=True, blank=True, editable=False)
    postcode_parl = models.CharField(max_length=9, null=True, blank=True, editable=False)
    lat_lng_parl= models.CharField(max_length=50, verbose_name="Lat,Lng", null=True, blank=True, editable=False)
    phone_parl = models.CharField(max_length=20, null=True, blank=True, editable=False)

    # Constituency details
    email_con = models.EmailField(null=True, blank=True, editable=False)
    address_con = models.TextField(null=True, blank=True, editable=False)
    postcode_con = models.CharField(max_length=9, null=True, blank=True, editable=False)
    lat_lng_con = models.CharField(max_length=50, verbose_name="Lat,Lng", null=True, blank=True, editable=False)
    phone_con = models.CharField(max_length=20, null=True, blank=True, editable=False)

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

    def schema_org(self):

        contains_place = []

        for foodbank in self.foodbank_obj():
            contains_place.append(foodbank.schema_org(as_sub_property = True))
        
        for location in self.location_obj():
            contains_place.append(location.schema_org(as_sub_property = True))

        schema_dict = {
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
        return Foodbank.objects.filter(parliamentary_constituency = self)

    def location_obj(self):
        return FoodbankLocation.objects.filter(parliamentary_constituency = self)

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
                "needs":foodbank.latest_need(),
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


    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)

        # Get MP contact details
        contact_details = mp_contact_details(self.mp_parl_id)

        self.mp_display_name = contact_details.get("display_name", None)

        self.website = contact_details.get("website", None)
        self.mp_twitter_handle = contact_details.get("twitter", None)
        self.mp_synopsis = contact_details.get("synopsis", None)
        
        if not self.email_parl:
            self.email_parl = contact_details.get("email_parl", None)
        self.address_parl = contact_details.get("address_parl", None)
        self.postcode_parl = contact_details.get("postcode_parl", None)
        self.lat_lng_parl = contact_details.get("lat_lng_parl", None)
        self.phone_parl = contact_details.get("phone_parl", None)

        self.email_con = contact_details.get("email_con", None)
        self.address_con = contact_details.get("address_con", None)
        self.postcode_con = contact_details.get("postcode_con", None)
        self.lat_lng_con = contact_details.get("lat_lng_con", None)
        self.phone_con = contact_details.get("phone_con", None)

        # Cleanup phone numbers
        if self.phone_parl:
            self.phone_parl = self.phone_parl.replace(" ","")
        if self.phone_con:
            self.phone_con = self.phone_con.replace(" ","")

        # Resave denormed data
        foodbanks = Foodbank.objects.filter(parliamentary_constituency = self) 
        for foodbank in foodbanks:
            deferred.defer(foodbank.save)

        locations = FoodbankLocation.objects.filter(parliamentary_constituency = self)
        for location in locations:
            deferred.defer(location.save)
        
        super(ParliamentaryConstituency, self).save(*args, **kwargs)


class GfCredential(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    cred_name = models.CharField(max_length=50)
    cred_value = models.CharField(max_length=255)


class FoodbankSubscriber(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    last_contacted = models.DateTimeField(editable=False, null=True, blank=True)
    foodbank = models.ForeignKey(Foodbank)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)
    email = models.EmailField()
    confirmed = models.BooleanField(default=False)

    sub_key = models.CharField(max_length=16, editable=False)
    unsub_key = models.CharField(max_length=16, editable=False)

    class Meta:
       unique_together = ('email', 'foodbank',)

    def foodbank_slug(self):
        return slugify(self.foodbank_name)

    def save(self, *args, **kwargs):

        # Ensure email address is lowercase
        self.email = self.email.lower()

        # Generate sub and unsub keys
        if not self.sub_key:
            salt = get_cred("salt")
            self.sub_key = hashlib.sha256("sub-%s-%s" % (datetime.now(), salt)).hexdigest()[:16]
            self.unsub_key = hashlib.sha256("unsub-%s-%s" % (datetime.now(), salt)).hexdigest()[:16]

        # Denorm food bank name
        self.foodbank_name = self.foodbank.name
        
        super(FoodbankSubscriber, self).save(*args, **kwargs)


class ConstituencySubscriber(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    last_contacted = models.DateTimeField(editable=False, null=True, blank=True)
    email = models.EmailField()
    name = models.CharField(max_length=100, null=True, blank=True)
    parliamentary_constituency = models.ForeignKey(ParliamentaryConstituency)
    parliamentary_constituency_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    def save(self, *args, **kwargs):

        # Ensure email address is lowercase
        self.email = self.email.lower()

        # Denorm food bank name
        self.parliamentary_constituency_name = self.parliamentary_constituency.name
        
        super(ConstituencySubscriber, self).save(*args, **kwargs)