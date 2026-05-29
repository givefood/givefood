#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid

from django.db import models
from django.core.validators import RegexValidator

from givefood.const.general import COUNTRIES_CHOICES, POSTCODE_REGEX


class TimestampedModel(models.Model):
    """Adds `created` (auto_now_add) and `modified` (auto_now) timestamps."""

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class CreatedModel(models.Model):
    """Adds a `created` (auto_now_add) timestamp only."""

    created = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        abstract = True


class EditableModel(models.Model):
    """Adds an `edited` timestamp for explicit user edits."""

    edited = models.DateTimeField(editable=False, null=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Adds a `uuid` identifier independent of the primary key."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class PhysicalPlace(models.Model):
    """
    A physical UK place: postal address, geocoded coordinates, and the
    administrative regions derived from the postcode. Postcode, geocoding
    and admin regions always travel together — concrete `save()` methods
    populate them from each other.

    Subclasses may override fields where their schema currently differs
    (e.g. `FoodbankLocation` makes `address` / `postcode` optional;
    `Foodbank` keeps `country` editable).
    """

    # Address
    address = models.TextField()
    postcode = models.CharField(max_length=9, validators=[
        RegexValidator(
            regex=POSTCODE_REGEX,
            message="Not a valid postcode",
            code="invalid_postcode",
        ),
    ])
    country = models.CharField(max_length=50, choices=COUNTRIES_CHOICES, editable=False)

    # Location
    lat_lng = models.CharField(max_length=50, verbose_name="Latitude, Longitude")
    latitude = models.FloatField(editable=False)
    longitude = models.FloatField(editable=False)
    place_id = models.CharField(max_length=1024, verbose_name="Place ID", null=True, blank=True)
    plus_code_compound = models.CharField(max_length=200, verbose_name="Plus Code (Compound)", null=True, blank=True, editable=False)
    plus_code_global = models.CharField(max_length=200, verbose_name="Plus Code (Global)", null=True, blank=True, editable=False)
    place_has_photo = models.BooleanField(default=False, editable=False)

    # Administrative regions (derived from postcode)
    county = models.CharField(max_length=75, null=True, blank=True, editable=False)
    district = models.CharField(max_length=75, null=True, blank=True, editable=False)
    ward = models.CharField(max_length=75, null=True, blank=True, editable=False)
    lsoa = models.CharField(max_length=75, null=True, blank=True, editable=False)
    msoa = models.CharField(max_length=75, null=True, blank=True, editable=False)

    # Political
    # related_name / related_query_name use the %(class)s placeholder so each
    # concrete subclass keeps the exact reverse accessor and query name Django
    # generated when this FK was declared separately on each model
    # (e.g. Foodbank -> `foodbank_set` accessor, `foodbank` query name).
    parliamentary_constituency = models.ForeignKey(
        "givefood.ParliamentaryConstituency",
        null=True, blank=True, editable=False,
        on_delete=models.DO_NOTHING,
        related_name="%(class)s_set",
        related_query_name="%(class)s",
    )
    parliamentary_constituency_name = models.CharField(max_length=50, null=True, blank=True, editable=False)
    parliamentary_constituency_slug = models.CharField(max_length=50, null=True, blank=True, editable=False)
    mp = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP", editable=False)
    mp_party = models.CharField(max_length=50, null=True, blank=True, verbose_name="MP's party", editable=False)
    mp_parl_id = models.IntegerField(verbose_name="MP's ID", null=True, blank=True, editable=False)

    class Meta:
        abstract = True
