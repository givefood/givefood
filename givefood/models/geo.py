#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.contrib.postgres.indexes import GinIndex, OpClass
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Upper
from django.template.defaultfilters import slugify

from givefood.const.general import POSTCODE_REGEX
from givefood.models.base import TimestampedModel


class Place(TimestampedModel):

    checked = models.DateTimeField(null=True, blank=True)

    gbpnid = models.IntegerField(unique=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    lat_lng = models.CharField(max_length=100, null=True, blank=True)
    histcounty = models.CharField(max_length=100, null=True, blank=True)
    adcounty = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    uniauth = models.CharField(max_length=100, null=True, blank=True)
    police = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    type = models.CharField(max_length=100, null=True, blank=True)
    county = models.CharField(max_length=100, null=True, blank=True)

    population = models.IntegerField(null=True, blank=True)

    name_slug = models.CharField(max_length=100, editable=False)
    county_slug = models.CharField(max_length=100, editable=False)

    def __str__(self):
        return "%s - %s" % (self.gbpnid, self.name)

    def lat(self):
        return float(self.lat_lng.split(",")[0])

    def lng(self):
        return float(self.lat_lng.split(",")[1])

    def save(self, *args, **kwargs):

        self.name_slug = slugify(self.name)
        if self.uniauth:
            self.county = self.uniauth
            self.county_slug = slugify(self.uniauth)
        else:
            self.county = self.adcounty
            self.county_slug = slugify(self.adcounty)

        super(Place, self).save(*args, **kwargs)

    class Meta:
        app_label = 'givefood'
        indexes = [
            models.Index(fields=['-population', 'name']),
            # Optimizes istartswith queries: UPPER(name) LIKE 'PREFIX%'
            models.Index(
                OpClass(Upper('name'), name='text_pattern_ops'),
                name='place_name_upper_like',
            ),
            # Optimizes icontains queries: UPPER(name) LIKE '%SUBSTR%' (requires pg_trgm)
            GinIndex(
                OpClass(Upper('name'), name='gin_trgm_ops'),
                name='place_name_upper_trgm',
            ),
        ]


class PlacePhoto(TimestampedModel):

    place_id = models.CharField(max_length=1024, null=True, blank=True)
    photo_ref= models.CharField(max_length=1024, unique=True)
    html_attributions = models.TextField()
    blob = models.BinaryField()

    def __str__(self):
        return self.place_id

    class Meta:
        app_label = 'givefood'


class Postcode(models.Model):
    """
    UK postcode with geographic and administrative boundary information.
    Data sourced from postcodes.csv containing 2.7m rows.
    """

    postcode = models.CharField(max_length=9, unique=True, db_index=True, validators=[
        RegexValidator(
            regex=POSTCODE_REGEX,
            message="Not a valid postcode",
            code="invalid_postcode",
        ),
    ])
    postcode_normalized = models.CharField(max_length=9, blank=True, db_index=True, editable=False)
    lat_lng = models.CharField(max_length=100, verbose_name="Latitude, Longitude")
    county = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    ward = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=50)
    region = models.CharField(max_length=100, null=True, blank=True)
    lsoa = models.CharField(max_length=20, null=True, blank=True, verbose_name="LSOA Code")
    msoa = models.CharField(max_length=20, null=True, blank=True, verbose_name="MSOA Code")
    police = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        app_label = 'givefood'
        indexes = [
            # Optimizes startswith queries: postcode_normalized LIKE 'PREFIX%'
            # Default db_index btree doesn't support LIKE on non-C collation.
            models.Index(
                OpClass('postcode_normalized', name='text_pattern_ops'),
                name='postcode_norm_like',
            ),
        ]

    def __str__(self):
        return self.postcode

    def save(self, *args, **kwargs):
        # Auto-populate normalized postcode on save
        self.postcode_normalized = self.postcode.upper().replace(' ', '')
        super().save(*args, **kwargs)
