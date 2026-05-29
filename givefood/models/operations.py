#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import models

from givefood.models.base import CreatedModel, TimestampedModel
from givefood.models.foodbank import Foodbank


class CharityYear(CreatedModel):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    date = models.DateField()
    income = models.IntegerField(null=True, blank=True, help_text="Income in pounds")
    expenditure = models.IntegerField(null=True, blank=True, help_text="Expenditure in pounds")


class GfCredential(CreatedModel):

    cred_name = models.CharField(max_length=50)
    cred_value = models.TextField()

    class Meta:
        app_label = 'givefood'


class Dump(CreatedModel):

    dump_type = models.CharField(max_length=50)
    dump_format = models.CharField(max_length=10)
    the_dump = models.TextField()
    row_count = models.PositiveIntegerField(null=True, blank=True)
    size = models.PositiveIntegerField(null=True, blank=True)

    def file_name(self):
        return "%s-%s.%s" % (self.dump_type, self.created.strftime("%Y%m%d"), self.dump_format)

    def save(self, *args, **kwargs):

        self.size = len(self.the_dump.encode('utf-8'))
        super(Dump, self).save(*args, **kwargs)


class SlugRedirect(TimestampedModel):

    old_slug = models.CharField(max_length=200, unique=True, db_index=True)
    new_slug = models.CharField(max_length=200, db_index=True)

    class Meta:
        app_label = 'givefood'

    def __str__(self):
        return f"{self.old_slug} -> {self.new_slug}"
