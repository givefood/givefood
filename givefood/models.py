#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

from django.db import models
from django.template.defaultfilters import slugify

from const.general import DELIVERY_HOURS_CHOICES, COUNTRIES_CHOICES, DELIVERY_PROVIDER_CHOICES, FOODBANK_NETWORK_CHOICES, PACKAGING_WEIGHT_PC
from func import parse_order_text


class Foodbank(models.Model):

    name = models.CharField(max_length=50)
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

    facebook_page = models.CharField(max_length=50, null=True, blank=True)
    twitter_handle = models.CharField(max_length=50, null=True, blank=True)

    contact_email = models.EmailField()
    notification_email = models.EmailField()
    phone_number = models.CharField(max_length=20)

    url = models.URLField(max_length=200, verbose_name="URL")
    shopping_list_url = models.URLField(max_length=200, verbose_name="Shopping list URL")
    is_closed = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    last_order = models.DateField(editable=False, null=True)
    last_social_media_check = models.DateTimeField(editable=False, null=True)

    def __str__(self):
        return self.name

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


    def orders(self):
        return Order.objects.filter(foodbank = self).order_by("-delivery_datetime")

    def no_orders(self):
        return len(self.orders())

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

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Foodbank, self).save(*args, **kwargs)


class Order(models.Model):

    order_id = models.CharField(max_length=50, editable=False)
    foodbank = models.ForeignKey(Foodbank)
    foodbank_name = models.CharField(max_length=50, editable=False)
    items_text = models.TextField()

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
    foodbank = models.ForeignKey(Foodbank, null=True, blank=True)
    distill_id = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    uri = models.CharField(max_length=250)
    change_text = models.TextField()
    post_text = models.TextField()
