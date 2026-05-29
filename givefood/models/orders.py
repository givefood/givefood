#!/usr/bin/env python
# -*- coding: utf-8 -*-

import html
from datetime import datetime

from django.db import models
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.urls import reverse

from givefood.const.general import (
    COUNTRIES_CHOICES, DELIVERY_HOURS_CHOICES, DELIVERY_PROVIDER_CHOICES,
    PACKAGING_WEIGHT_PC,
)
from givefood.const.item_types import (
    ITEM_CATEGORIES, ITEM_CATEGORIES_CHOICES, ITEM_CATEGORY_GROUPS,
    ITEM_GROUPS_CHOICES,
)
from givefood.models.base import TimestampedModel
from givefood.models.foodbank import Foodbank
from givefood.utils.ai import gemini
from givefood.utils.cache import decache_async
from givefood.utils.text import get_calories


class Order(TimestampedModel):

    order_id = models.CharField(max_length=100, editable=False)
    foodbank = models.ForeignKey(Foodbank, null=True, blank=True, on_delete=models.SET_NULL)
    items_text = models.TextField()
    need = models.ForeignKey("FoodbankChange", null=True, blank=True, on_delete=models.DO_NOTHING)
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, editable=False)
    order_group = models.ForeignKey("OrderGroup", null=True, blank=True, on_delete=models.DO_NOTHING)

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
       # Note: unique_together allows multiple NULL values, so multiple unassigned orders
       # with the same delivery_date and delivery_provider are permitted. This is intentional
       # as unassigned orders are distinguished by their order_id which includes a timestamp.
       unique_together = ('foodbank', 'delivery_date', 'delivery_provider')
       app_label = 'givefood'
       indexes = [
           models.Index(fields=['foodbank', '-delivery_datetime']),
       ]

    def __str__(self):
        return self.order_id

    def foodbank_name_slug(self):
        if self.foodbank:
            return self.foodbank.slug
        return "unassigned"

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
        # Save first to get an ID if this is a new order
        is_new = self.pk is None

        # For new unassigned orders, use a temporary unique order_id
        if is_new and not self.foodbank:
            import uuid as uuid_module
            self.order_id = f"temp-order-{uuid_module.uuid4()}"
        elif self.foodbank:
            # Generate ID for assigned orders
            self.order_id = f"gf-{self.foodbank.slug}-{slugify(self.delivery_provider)}-{self.delivery_date}"

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

        # Denorm country
        if self.foodbank:
            self.country = self.foodbank.country
        else:
            self.country = ""

        super(Order, self).save(*args, **kwargs)

        # Delete all the existing orderlines
        order_lines = OrderLine.objects.filter(order = self).delete()

        # Parse the order text
        prompt = render_to_string(
            "admin/prompts/orderline_prompt.txt",
            {
                "items_text":self.items_text,
            }
        )
        order_lines = gemini(
            prompt = prompt,
            temperature = 1,
            response_mime_type= "application/json",
            response_schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "integer"},
                        "item_cost": {"type": "integer"},
                        "weight": {"type": "integer"},
                    },
                    "required": ["name", "quantity", "item_cost", "weight"]
                }
            }
        )

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

        # Update order_id for new unassigned orders now that we have a pk
        if is_new and not self.foodbank:
            provider_slug = slugify(self.delivery_provider) if self.delivery_provider else "none"
            self.order_id = f"gf-unassigned-{self.pk}-{provider_slug}-{self.delivery_date}"
            # Use update to avoid recursive save calls
            Order.objects.filter(pk=self.pk).update(order_id=self.order_id)

        # Update last order date on foodbank
        if do_foodbank_save and self.foodbank:
            self.foodbank.last_order = Order.objects.filter(foodbank = self.foodbank).order_by("-delivery_date")[0].delivery_date
            self.foodbank.save(do_geoupdate=False)

        # Decache OrderGroup public pages if this order belongs to a public OrderGroup
        if self.order_group and self.order_group.public:
            urls = [
                reverse("managed_donation", kwargs={"slug": self.order_group.slug, "key": self.order_group.key}),
                reverse("managed_donation_geojson", kwargs={"slug": self.order_group.slug, "key": self.order_group.key}),
                reverse("managed_donation_items", kwargs={"slug": self.order_group.slug, "key": self.order_group.key}),
            ]
            decache_async.enqueue(urls)

    def lines(self):
        return OrderLine.objects.filter(order = self).order_by("-weight")


class OrderLine(models.Model):

    order = models.ForeignKey(Order, on_delete=models.DO_NOTHING)

    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    item_cost = models.PositiveIntegerField() #pence
    line_cost = models.PositiveIntegerField()

    weight = models.PositiveIntegerField(editable=False,null=True)
    calories = models.PositiveIntegerField(editable=False,null=True)

    category = models.CharField(max_length=250, choices=ITEM_CATEGORIES_CHOICES, editable=False)
    group = models.CharField(max_length=250, choices=ITEM_GROUPS_CHOICES, editable=False)

    delivery_date = models.DateField(editable=False)

    def save(self, *args, **kwargs):
        from givefood.models.needs import FoodbankChangeLine
        self.delivery_date = self.order.delivery_date
        if self.quantity:
            self.item_cost = self.line_cost // self.quantity
        if not self.category:
            try:
                prev_line = OrderLine.objects.filter(name=self.name).exclude(category="").latest("id")
                self.category = prev_line.category
            except OrderLine.DoesNotExist:
                try:
                    prev_need_line = FoodbankChangeLine.objects.filter(item=self.name).exclude(category="").latest("created")
                    self.category = prev_need_line.category
                except FoodbankChangeLine.DoesNotExist:
                    prompt = render_to_string(
                        "categorisation_prompt.txt",
                        {
                            "item": self.name,
                            "item_categories": ITEM_CATEGORIES,
                        }
                    )
                    ai_response = gemini(
                        prompt=prompt,
                        temperature=0.1,
                    )
                    if ai_response in ITEM_CATEGORIES:
                        self.category = ai_response
                    else:
                        self.category = "Other"
            if not self.group:
                self.group = ITEM_CATEGORY_GROUPS.get(self.category, "Other")
        super(OrderLine, self).save(*args, **kwargs)

    def weight_kg(self):
        return self.weight/1000

    def natural_cost(self):
        return float(self.line_cost/100)

    class Meta:
        app_label = 'givefood'


class OrderItem(models.Model):

    name = models.CharField(max_length=100, unique=True)
    slug = models.CharField(max_length=100, editable=False)
    calories = models.PositiveIntegerField(help_text="Per 100g")

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


class OrderGroup(TimestampedModel):

    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, editable=False)
    public = models.BooleanField(default=False)
    key = models.CharField(max_length=8, null=True, blank=True)

    def orders(self):
        return Order.objects.select_related('foodbank').filter(order_group = self).order_by("delivery_datetime")

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)
        super(OrderGroup, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'givefood'
