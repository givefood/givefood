#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib

from django.db import models
from django.template.defaultfilters import slugify
from django.utils import timezone

from givefood.models.base import CreatedModel
from givefood.models.foodbank import Foodbank, FoodbankDonationPoint
from givefood.models.political import ParliamentaryConstituency
from givefood.utils.cache import get_cred


class FoodbankSubscriber(CreatedModel):

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
        indexes = [
            models.Index(fields=['foodbank', 'confirmed']),
        ]

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

            sub_key_str = "sub-%s-%s" % (timezone.now(), salt)
            sub_key_str = sub_key_str.encode('utf-8')

            unsub_key_str = "unsub-%s-%s" % (timezone.now(), salt)
            unsub_key_str = unsub_key_str.encode('utf-8')

            self.sub_key = hashlib.sha256(sub_key_str).hexdigest()[:16]
            self.unsub_key = hashlib.sha256(unsub_key_str).hexdigest()[:16]

        # Denorm food bank name
        self.foodbank_name = self.foodbank.name

        super(FoodbankSubscriber, self).save(*args, **kwargs)


class ConstituencySubscriber(CreatedModel):

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


class WebPushSubscription(CreatedModel):
    """
    Stores web push notification subscriptions for food banks.
    Uses VAPID (Voluntary Application Server Identification) standard.
    """

    foodbank = models.ForeignKey(Foodbank, on_delete=models.CASCADE, related_name='webpush_subscriptions')

    # Browser push subscription data
    endpoint = models.URLField(max_length=2000)
    p256dh = models.CharField(max_length=200, help_text="User public encryption key")
    auth = models.CharField(max_length=50, help_text="Auth secret for encryption")

    # Browser info (optional)
    browser = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        app_label = 'givefood'
        unique_together = ('foodbank', 'endpoint')
        indexes = [
            models.Index(fields=['foodbank', '-created']),
        ]

    def __str__(self):
        return f"WebPush: {self.foodbank.name} - {self.endpoint[:50]}..."


class MobileSubscriber(CreatedModel):

    device_id = models.CharField(max_length=250)
    platform = models.CharField(max_length=10)
    timezone = models.CharField(max_length=100)
    locale = models.CharField(max_length=50)
    app_version = models.CharField(max_length=50)
    os_version = models.CharField(max_length=50)
    device_model = models.CharField(max_length=100)
    sub_type = models.CharField(max_length=25)

    foodbank = models.ForeignKey(Foodbank, on_delete=models.CASCADE)
    donationpoint = models.ForeignKey(FoodbankDonationPoint, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        app_label = 'givefood'
        indexes = [
            models.Index(fields=['foodbank', '-created']),
        ]


class WhatsappSubscriber(CreatedModel):
    """
    Stores WhatsApp subscriptions for food bank need notifications.
    Users subscribe by sending "subscribe foodbank-slug" to the WhatsApp number.
    """

    phone_number = models.CharField(max_length=20, help_text="WhatsApp phone number in international format")
    foodbank = models.ForeignKey(Foodbank, on_delete=models.CASCADE, related_name='whatsapp_subscriptions')
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    last_notified = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        app_label = 'givefood'
        unique_together = ('phone_number', 'foodbank')
        indexes = [
            models.Index(fields=['foodbank', '-created']),
        ]

    def __str__(self):
        return f"WhatsApp: {self.phone_number} - {self.foodbank_name}"

    def save(self, *args, **kwargs):
        # Denorm food bank name
        if self.foodbank:
            self.foodbank_name = self.foodbank.name
        super(WhatsappSubscriber, self).save(*args, **kwargs)
