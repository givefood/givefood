#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import timedelta

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from givefood.const.general import CRAWL_TYPE_ICON_DEFAULT, CRAWL_TYPE_ICONS
from givefood.models.foodbank import Foodbank


class FoodbankHit(models.Model):

    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    day = models.DateField()
    hits = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'givefood'
        constraints = [
            # The hit counter upserts against this. hits is carried along so
            # the same index still answers the per-food-bank totals without
            # touching the heap.
            models.UniqueConstraint(
                fields=['foodbank', 'day'],
                include=['hits'],
                name='foodbankhit_foodbank_day_uniq',
            ),
        ]


class CrawlSet(models.Model):

    start = models.DateTimeField(auto_now_add=True, editable=False)
    finish = models.DateTimeField(null=True, blank=True, editable=False)
    crawl_type = models.CharField(max_length=50) # need, article, charity, discrepancy

    def crawl_type_icon(self):
        return CRAWL_TYPE_ICONS.get(self.crawl_type, CRAWL_TYPE_ICON_DEFAULT)

    def time_taken(self):
        """Return the time taken for this crawl set, rounded to the nearest second."""
        if self.finish:
            return timedelta(seconds=round((self.finish - self.start).total_seconds()))
        return None

    def item_count(self):
        return CrawlItem.objects.filter(crawl_set=self).count()

    def object_count(self):
        return CrawlItem.objects.filter(crawl_set=self, object_id__isnull=False).count()


class CrawlItem(models.Model):

    crawl_set = models.ForeignKey(CrawlSet, on_delete=models.DO_NOTHING, null=True, blank=True)
    crawl_type = models.CharField(max_length=50) # need, article, charity, discrepancy
    start = models.DateTimeField(auto_now_add=True, editable=False)
    finish = models.DateTimeField(null=True, blank=True, editable=False)
    foodbank = models.ForeignKey(Foodbank, on_delete=models.DO_NOTHING)
    url = models.URLField(max_length=2000, null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.DO_NOTHING, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    def crawl_type_icon(self):
        return CRAWL_TYPE_ICONS.get(self.crawl_type, CRAWL_TYPE_ICON_DEFAULT)

    def time_taken_ms(self):
        if self.finish:
            return int((self.finish - self.start).total_seconds() * 1000)
        return None

    def object_class_name(self):
        return self.content_object.__class__.__name__

    class Meta:
        app_label = 'givefood'
        indexes = [
            models.Index(fields=['foodbank', '-finish']),
            # The food bank admin page lists a food bank's crawls newest first
            # by start, which the -finish index cannot order. Without this one
            # Postgres reads every crawl row that food bank has ever had --
            # thousands of heap blocks -- to hand back the newest hundred.
            models.Index(fields=['foodbank', '-start'],
                         name='crawlitem_foodbank_start_idx'),
        ]
