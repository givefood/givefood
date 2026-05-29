#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from string import capwords

from requests import PreparedRequest

from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse, translate_url

from givefood.models.base import TimestampedModel
from givefood.models.foodbank import Foodbank
from givefood.settings import LANGUAGES
from givefood.utils.cache import decache_async


class FoodbankArticle(TimestampedModel):

    foodbank = models.ForeignKey(Foodbank, null=True, blank=True, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    published_date = models.DateTimeField(editable=False)
    title = models.CharField(max_length=250)
    url = models.CharField(max_length=250, unique=True)
    featured = models.BooleanField(default=False)

    def url_with_ref(self):
        added_params = {"ref":"givefood.org.uk"}
        req = PreparedRequest()
        req.prepare_url(self.url, added_params)
        return req.url

    def title_captialised(self):
        # List of words that should not be capitalized (preserve original case)
        no_cap_words = ['UK', 'AGM', 'CEO', 'NI', 'GCK', 'BBC', 'COVID', 'MP', 'NHS', 'ID', 'TV', 'UN', 'FC', 'UHT']

        result = capwords(self.title)

        # Replace capitalized acronyms with their correct form (whole words only)
        for word in no_cap_words:
            result = re.sub(r'\b' + re.escape(word.capitalize()) + r'\b', word, result)

        # Remove trailing period
        result = result.rstrip('.')

        # Replace multiple consecutive spaces with a single space
        while '  ' in result:
            result = result.replace('  ', ' ')

        return result

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def save(self, *args, **kwargs):

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        # Check if featured field is changing
        old_featured = None
        if self.pk:
            try:
                old_instance = FoodbankArticle.objects.get(pk=self.pk)
                old_featured = old_instance.featured
            except FoodbankArticle.DoesNotExist:
                pass

        super(FoodbankArticle, self).save(*args, **kwargs)

        # If featured status changed, decache the homepage
        if old_featured is not None and old_featured != self.featured:
            index_url = reverse("index")
            urls = [index_url]
            for language in LANGUAGES:
                urls.append(translate_url(index_url, language[0]))
            decache_async.enqueue(urls)

    def __str__(self):
        return "%s - %s" % (self.title, self.foodbank_name)

    class Meta:
        app_label = 'givefood'
        indexes = [
            models.Index(fields=['foodbank', '-published_date']),
        ]
