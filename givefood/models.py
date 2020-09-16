#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib, difflib
from datetime import datetime

from google.appengine.api import memcache

from django.db import models
from django.template.defaultfilters import slugify

from const.general import DELIVERY_HOURS_CHOICES, COUNTRIES_CHOICES, DELIVERY_PROVIDER_CHOICES, FOODBANK_NETWORK_CHOICES, PACKAGING_WEIGHT_PC, FB_MC_KEY
from func import parse_order_text, clean_foodbank_need_text, admin_regions_from_postcode, mp_from_parlcon, geocode, make_url_friendly, find_foodbanks, mpid_from_name


class Foodbank(models.Model):

    name = models.CharField(max_length=50)
    alt_name = models.CharField(max_length=50, null=True, blank=True, help_text="E.g. Welsh version of the name")
    slug = models.CharField(max_length=50, editable=False)
    address = models.TextField()
    postcode = models.CharField(max_length=9)
    delivery_address = models.TextField(null=True, blank=True)
    latt_long = models.CharField(max_length=50, verbose_name="Latt,Long")
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES)
    network = models.CharField(max_length=50, choices=FOODBANK_NETWORK_CHOICES, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    charity_number = models.CharField(max_length=50,null=True, blank=True)
    charity_just_foodbank = models.BooleanField(default=False, verbose_name="Charity just foodbank", help_text="Tick this if the charity is purely used for the foodbank, rather than other uses such as a church")

    parliamentary_constituency = models.CharField(max_length=50, null=True, blank=True)
    parliamentary_constituency_slug = models.CharField(max_length=50, null=True, blank=True, editable=False)
    county = models.CharField(max_length=50, null=True, blank=True)
    district = models.CharField(max_length=50, null=True, blank=True)
    ward = models.CharField(max_length=50, null=True, blank=True)
    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP")
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party")
    mp_parl_id = models.IntegerField(verbose_name="MP's ID")

    facebook_page = models.CharField(max_length=50, null=True, blank=True)
    twitter_handle = models.CharField(max_length=50, null=True, blank=True)
    bankuet_slug = models.CharField(max_length=50, null=True, blank=True)

    contact_email = models.EmailField()
    notification_email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=20)
    secondary_phone_number = models.CharField(max_length=20, null=True, blank=True)

    url = models.URLField(max_length=200, verbose_name="URL")
    shopping_list_url = models.URLField(max_length=200, verbose_name="Shopping list URL")
    is_closed = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    last_order = models.DateField(editable=False, null=True)
    last_social_media_check = models.DateTimeField(editable=False, null=True)
    last_need = models.DateTimeField(editable=False, null=True)

    no_locations = models.IntegerField(editable=False, default=0)

    def __str__(self):
        return self.name

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
                return "https://www.charitycommissionni.org.uk/charity-details/?regId=%s" % (self.charity_number)
            if self.country == "Wales" or self.country == "England":
                return "https://beta.charitycommission.gov.uk/charity-details/?regId=%s" % (self.charity_number)

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

    def orders(self):
        return Order.objects.filter(foodbank = self).order_by("-delivery_datetime")

    def no_orders(self):
        return len(self.orders())

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
        self.slug = slugify(self.name)
        if not self.parliamentary_constituency:
            regions = admin_regions_from_postcode(self.postcode)
            self.parliamentary_constituency = regions.get("parliamentary_constituency", None)
            self.county = regions.get("county", None)
            self.ward = regions.get("ward", None)
            self.district = regions.get("district", None)
        if not self.mp:
            mp_details = mp_from_parlcon(self.parliamentary_constituency)
            self.mp = mp_details.get("mp")
            self.mp_party = mp_details.get("party")
        if not self.parliamentary_constituency_slug:
            self.parliamentary_constituency_slug = slugify(self.parliamentary_constituency)
        if not self.mp_parl_id:
            self.mp_parl_id = mpid_from_name(self.mp)
        self.no_locations = self.get_no_locations()
        super(Foodbank, self).save(*args, **kwargs)

        memcache.delete(FB_MC_KEY)


class FoodbankLocation(models.Model):

    foodbank = models.ForeignKey(Foodbank)
    foodbank_name = models.CharField(max_length=50, editable=False)
    foodbank_slug = models.CharField(max_length=50, editable=False)
    foodbank_network = models.CharField(max_length=50, editable=False)
    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=50, editable=False)
    address = models.TextField()
    postcode = models.CharField(max_length=9)
    latt_long = models.CharField(max_length=50, verbose_name="Latt,Long")
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    parliamentary_constituency = models.CharField(max_length=50, null=True, blank=True)
    parliamentary_constituency_slug = models.CharField(max_length=50, null=True, blank=True, editable=False)
    county = models.CharField(max_length=50, null=True, blank=True)
    district = models.CharField(max_length=50, null=True, blank=True)
    ward = models.CharField(max_length=50, null=True, blank=True)
    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP")
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party")
    mp_parl_id = models.IntegerField(verbose_name="MP's ID")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return "/admin/foodbank/%s/location/%s/edit/" % (self.foodbank.slug, self.slug)

    def latest_need(self):
        return self.foodbank.latest_need()

    def full_address(self):
        return "%s\r\n%s" % (self.address, self.postcode)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        self.foodbank_name = self.foodbank.name
        self.foodbank_slug = self.foodbank.slug
        self.foodbank_network = self.foodbank.network

        if not self.parliamentary_constituency:
            regions = admin_regions_from_postcode(self.postcode)
            self.parliamentary_constituency = regions.get("parliamentary_constituency", None)
            self.county = regions.get("county", None)
            self.ward = regions.get("ward", None)
            self.district = regions.get("district", None)
        if not self.mp:
            mp_details = mp_from_parlcon(self.parliamentary_constituency)
            self.mp = mp_details.get("mp")
            self.mp_party = mp_details.get("party")
        if not self.parliamentary_constituency_slug:
            self.parliamentary_constituency_slug = slugify(self.parliamentary_constituency)
        if self.mp_parl_id == None:
            self.mp_parl_id = mpid_from_name(self.mp)

        super(FoodbankLocation, self).save(*args, **kwargs)

        self.foodbank.save()


class Order(models.Model):

    order_id = models.CharField(max_length=50, editable=False)
    foodbank = models.ForeignKey(Foodbank)
    foodbank_name = models.CharField(max_length=50, editable=False)
    items_text = models.TextField()
    need = models.ForeignKey("FoodbankChange", null=True, blank=True)

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

    def save(self, *args, **kwargs):
        # Generate ID
        self.order_id = "gf-%s-%s" % (self.foodbank.slug,str(self.delivery_date))

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

        #denorm foodbank name
        self.foodbank_name = self.foodbank.name

        super(Order, self).save(*args, **kwargs)

        # Delete all the existing orderlines
        OrderLine.objects.filter(order = self).delete()

        order_lines = parse_order_text(self.items_text)

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

            line_cost = order_line.get("item_cost") * order_line.get("quantity")
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
        return OrderLine.objects.filter(order = self)


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


class FoodbankChange(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    need_id = models.CharField(max_length=8, editable=False)

    foodbank = models.ForeignKey(Foodbank, null=True, blank=True)
    foodbank_name = models.CharField(max_length=50, editable=False, null=True, blank=True)

    distill_id = models.CharField(max_length=250, null=True, blank=True)
    name = models.CharField(max_length=250, null=True, blank=True)
    uri = models.CharField(max_length=250, null=True, blank=True)
    change_text = models.TextField()
    published = models.BooleanField(default=False)

    def __str__(self):
        return "%s - %s (%s)" % (self.foodbank_name, self.created.strftime("%b %d %Y %H:%M:%S"), self.need_id)

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def no_items(self):
        return len(self.change_text.split('\n'))

    def input_method(self):
        if self.distill_id:
            return "scrape"
        else:
            return "typed"

    def change_list(self):
        return self.change_text.split("\n")

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
            d = difflib.unified_diff(last_need[0].change_list(), self.change_list(), lineterm='')
            return '\n'.join(d)

    def last_need_date(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return last_need[0].created

    def save(self, *args, **kwargs):

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        self.change_text = clean_foodbank_need_text(self.change_text)

        if not self.need_id:
            need_id = hashlib.sha256("%s%s" % (self.uri, datetime.now())).hexdigest()[:8]
            self.need_id = need_id

        super(FoodbankChange, self).save(*args, **kwargs)

        if self.foodbank:
            self.foodbank.last_need = self.created
            self.foodbank.save()


class ApiFoodbankSearch(models.Model):

    created = models.DateTimeField(auto_now_add=True, editable=False)
    query_type = models.CharField(max_length=8)
    query = models.CharField(max_length=255)
    nearest_foodbank = models.IntegerField()
    latt_long = models.CharField(max_length=50, verbose_name="Latt,Long", null=True, blank=True)

    def wfbn_url(self):
        return "https://www.givefood.org.uk/needs/?%s=%s" % (self.query_type, self.query)

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
    # country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES)

    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP")
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party")
    mp_parl_id = models.IntegerField(verbose_name="MP's ID")

    electorate = models.IntegerField(null=True, blank=True)
    boundary_geojson = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)
        super(ParliamentaryConstituency, self).save(*args, **kwargs)