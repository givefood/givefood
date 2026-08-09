#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from urllib.parse import quote_plus

from django.db import models
from django.template.defaultfilters import slugify

from givefood.const.general import COUNTRIES_CHOICES
from givefood.utils.geo import find_parlcons, geojson_dict


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
            "sameAs": "https://en.wikipedia.org/wiki/%s_(UK_Parliament_constituency)" % (quote_plus(self.name.replace(" ","_"))),
        }

        return schema_dict

    def schema_org_str(self):
        return json.dumps(self.schema_org(), indent=4, sort_keys=True)

    def boundary_geojson_dict(self):
        return geojson_dict(self.boundary_geojson)


    def foodbank_obj(self):
        # foodbank_queryset() selects the latest need and, in any language but
        # English, prefetches that need's translation. Without it the page
        # rendered one FoodbankChangeTranslation query per food bank, because
        # the template reaches through to get_change_text on each of them.
        from givefood.utils.geo import foodbank_queryset
        return foodbank_queryset().filter(parliamentary_constituency = self, is_closed = False)

    def location_obj(self):
        from django.db.models import Prefetch

        from givefood.models.foodbank import FoodbankLocation
        from givefood.utils.geo import foodbank_queryset

        # Prefetching the food bank rather than select_related-ing it costs two
        # extra queries but carries the translation prefetch with it, which
        # select_related cannot do. Two constant queries beat one per location.
        return FoodbankLocation.objects.filter(
            parliamentary_constituency = self, is_closed = False,
        ).prefetch_related(
            Prefetch("foodbank", queryset=foodbank_queryset())
        )

    def foodbanks(self):

        foodbanks = self.foodbank_obj()
        locations = self.location_obj()

        constituency_foodbanks = []
        for foodbank in foodbanks:
            constituency_foodbanks.append({
                "type":"organisation",
                "name":foodbank.name,
                "slug":foodbank.slug,
                "lat_lng":foodbank.lat_lng,
                "needs":foodbank.latest_need,
                "url":foodbank.url,
                "shopping_list_url":foodbank.shopping_list_url,
                "gf_url":"/needs/at/%s/" % (foodbank.slug),
                "phone_number":foodbank.phone_number,
                "contact_email":foodbank.contact_email,
                "facebook_page":foodbank.facebook_page,
            })

        for location in locations:
            constituency_foodbanks.append({
                "type":"location",
                "name":location.name,
                "foodbank_name":location.foodbank_name,
                "slug":location.slug,
                "lat_lng":location.lat_lng,
                "needs":location.latest_need(),
                "url":location.foodbank.url,
                "shopping_list_url":location.foodbank.shopping_list_url,
                "gf_url":"/needs/at/%s/%s/" % (location.foodbank_slug, location.slug),
                "phone_number":location.phone_or_foodbank_phone(),
                "contact_email":location.email_or_foodbank_email(),
                "facebook_page":location.foodbank.facebook_page,
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

        super(ParliamentaryConstituency, self).save(*args, **kwargs)

    class Meta:
        app_label = 'givefood'
        indexes = [
            # Constituency pages, their GeoJSON and the MP photo redirect all
            # get_object_or_404 on slug.
            models.Index(fields=['slug'], name='parlcon_slug_idx'),
        ]
