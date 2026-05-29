#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unicodedata
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils.translation import get_language

from givefood.const.general import (
    DISCREPANCY_STATUS_CHOICES, DISCREPANCY_TYPES_CHOICES,
    NEED_INPUT_TYPES_CHOICES, NEED_LINE_TYPES_CHOICES,
)
from givefood.const.item_types import (
    ITEM_CATEGORIES_CHOICES, ITEM_CATEGORY_GROUPS, ITEM_GROUPS_CHOICES,
)
from givefood.models.base import TimestampedModel
from givefood.models.foodbank import Foodbank
from givefood.settings import LANGUAGES, LANGUAGES_SKIP_TRANSLATE
from givefood.utils.general import translate_need_async
from givefood.utils.text import clean_foodbank_need_text, diff_html


class FoodbankDiscrepancy(TimestampedModel):

    foodbank = models.ForeignKey(Foodbank, null=True, blank=True, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)
    need = models.ForeignKey("FoodbankChange", null=True, blank=True, on_delete=models.DO_NOTHING)

    url = models.URLField(null=True, blank=True)
    discrepancy_type = models.CharField(max_length=50, choices=DISCREPANCY_TYPES_CHOICES)
    discrepancy_text = models.TextField()
    status = models.CharField(max_length=10, choices=DISCREPANCY_STATUS_CHOICES, default="New")

    def foodbank_slug(self):
        return slugify(self.foodbank_name)

    def save(self, *args, **kwargs):

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        super(FoodbankDiscrepancy, self).save(*args, **kwargs)


class FoodbankChange(TimestampedModel):

    # This is known on the frontend as a 'need'

    need_id = models.UUIDField(default=uuid.uuid4, editable=False)
    need_id_str = models.CharField(max_length=36, editable=False)

    foodbank = models.ForeignKey(Foodbank, null=True, blank=True, on_delete=models.DO_NOTHING)
    foodbank_name = models.CharField(max_length=100, editable=False, null=True, blank=True)

    distill_id = models.CharField(max_length=250, null=True, blank=True)
    name = models.CharField(max_length=250, null=True, blank=True)
    uri = models.CharField(max_length=250, null=True, blank=True)

    change_text = models.TextField(verbose_name="Shopping List")
    change_text_original = models.TextField(null=True, blank=True)

    excess_change_text = models.TextField(verbose_name="Excess Items", null=True, blank=True)
    excess_change_text_original = models.TextField(null=True, blank=True)

    published = models.BooleanField(default=False)
    nonpertinent = models.BooleanField(default=False, editable=False)
    notified = models.DateTimeField(null=True, blank=True, editable=False)

    input_method = models.CharField(max_length=10, choices=NEED_INPUT_TYPES_CHOICES)
    is_categorised = models.BooleanField(default=False, editable=False)

    def clean(self):
        if self.foodbank == None and self.published == True:
            raise ValidationError('Need to set a food bank to publish need')

    def need_id_short(self):
        return str(self.need_id)[:7]

    def __str__(self):
        return "%s - %s (%s)" % (self.foodbank_name, self.created.strftime("%b %d %Y %H:%M:%S"), self.need_id_short())

    def created_without_microseconds(self):
        return self.created.replace(microsecond=0)

    def foodbank_name_slug(self):
        return slugify(self.foodbank_name)

    def no_items(self):
        if self.change_text == "Unknown" or self.change_text == "Nothing":
            return 0
        else:
            return len(self.change_text.split('\n'))

    def categorised_items(self):
        return FoodbankChangeLine.objects.filter(need = self)

    def no_items_categorised(self):
        return len(self.categorised_items())

    def total_items(self):
        return len(self.change_list()) + len(self.excess_list())

    def set_input_method(self):
        if self.distill_id:
            return "scrape"
        else:
            return "typed"

    def input_method_human(self):
        if self.input_method == "scrape":
            return "Scraped"
        if self.input_method == "typed":
            return "Typed"
        if self.input_method == "user":
            return "User"
        if self.input_method == "ai":
            return "AI"

    def input_method_emoji(self):
        if self.input_method == "scrape":
            return '<span class="mdi mdi-spider"></span>'
        if self.input_method == "typed":
            return '<span class="mdi mdi-keyboard"></span>'
        if self.input_method == "user":
            return '<span class="mdi mdi-account"></span>'
        if self.input_method == "ai":
            return '<span class="mdi mdi-robot"></span>'

    def change_list(self):
        return self.change_text.split("\n")

    def excess_list(self):
        if self.excess_change_text:
            return self.excess_change_text.split("\n")
        else:
            return []

    def clean_change_text(self):
        if self.change_text:
            return unicodedata.normalize('NFKD', self.change_text).encode('ascii', 'ignore')
        else:
            return None

    def last_need(self):

        last_need = FoodbankChange.objects.filter(
            foodbank = self.foodbank,
            created__lt = self.created,
            published = True,
        ).order_by("-created")[:1]

        return last_need

    def diff_from_pub(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].change_list(),
                self.change_list()
            )

    def diff_from_pub_excess(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].excess_list(),
                self.excess_list()
            )

    def last_need_date(self):
        last_need = self.last_need()
        if not last_need:
            return None
        else:
            return last_need[0].created

    def last_nonpert_need(self):

        last_need = FoodbankChange.objects.filter(
            foodbank = self.foodbank,
            created__lt = self.created,
            nonpertinent = True,
        ).order_by("-created")[:1]

        return last_need

    def diff_from_nonpert(self):
        last_need = self.last_nonpert_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].change_list(),
                self.change_list()
            )

    def diff_from_nonpert_excess(self):
        last_need = self.last_nonpert_need()
        if not last_need:
            return None
        else:
            return diff_html(
                last_need[0].excess_list(),
                self.excess_list()
            )

    def get_text(self, text_type = "change"):

        current_language = get_language()
        if self.change_text in ["Facebook", "Unknown", "Nothing"]:
            the_text = self.change_text
        if current_language == "en":
            if text_type == "change":
                the_text = self.change_text
            if text_type == "excess":
                the_text = self.excess_change_text
        else:
            # Check for prefetched translations first to avoid N+1 queries
            translated_text = None
            prefetched = getattr(self, '_prefetched_objects_cache', {})
            if 'foodbankchangetranslation_set' in prefetched:
                for translation in prefetched['foodbankchangetranslation_set']:
                    if translation.language == current_language:
                        translated_text = translation
                        break
            else:
                try:
                    translated_text = FoodbankChangeTranslation.objects.get(need = self, language = current_language)
                except FoodbankChangeTranslation.DoesNotExist:
                    pass

            if translated_text:
                if text_type == "change":
                    the_text = translated_text.change_text
                if text_type == "excess":
                    the_text = translated_text.excess_change_text

            if not translated_text or not the_text:
                if text_type == "change":
                    the_text = self.change_text
                if text_type == "excess":
                    the_text = self.excess_change_text

        if not the_text:
            return ""

        # Remove empty lines
        non_empty_lines = [line for line in the_text.splitlines() if line.strip()]
        the_text = "\n".join(non_empty_lines)
        return the_text

    def get_change_text(self):
        return self.get_text("change")

    def get_excess_text(self):
        return self.get_text("excess")

    def get_excess_text_list(self):
        return self.get_excess_text().split("\n")

    def get_absolute_url(self):
        return reverse("gfadmin:need", args=[self.need_id])

    def crawl_set(self):
        from givefood.models.analytics import CrawlItem
        content_type = ContentType.objects.get_for_model(self)
        crawl_item = CrawlItem.objects.filter(content_type = content_type, object_id = self.id).first()
        if crawl_item:
            return crawl_item.crawl_set
        else:
            return None

    def translation_count(self):
        return FoodbankChangeTranslation.objects.filter(need = self).count()

    def save(self, do_translate=None, do_foodbank_save=True, *args, **kwargs):

        self.need_id_str = str(self.need_id)

        if not self.input_method:
            self.input_method = self.set_input_method()

        if self.foodbank:
            self.foodbank_name = self.foodbank.name

        self.change_text = clean_foodbank_need_text(self.change_text)
        if self.excess_change_text:
            self.excess_change_text = clean_foodbank_need_text(self.excess_change_text)

        super(FoodbankChange, self).save(*args, **kwargs)

        if self.foodbank and self.published and do_foodbank_save:
            self.foodbank.save(do_geoupdate=False)

        # Translation behavior:
        # - If do_translate is None (default), automatically translate when published=True
        # - If do_translate is explicitly True, always translate when published=True
        # - If do_translate is explicitly False, never translate (used for bulk operations)
        # This ensures translations are triggered whenever a need is published,
        # whether via form save or the publish button.
        if do_translate is None:
            do_translate = self.published

        if self.published and do_translate:
            for language in LANGUAGES:
                language_code = language[0]
                if language_code != "en" and language_code not in LANGUAGES_SKIP_TRANSLATE:
                    translate_need_async.enqueue(language_code, self.need_id_str)

    def delete(self, *args, **kwargs):

        FoodbankChangeLine.objects.filter(need = self).delete()
        FoodbankChangeTranslation.objects.filter(need = self).delete()
        super(FoodbankChange, self).delete(*args, **kwargs)
        if self.foodbank:
            if self.published:
                self.foodbank.save(do_geoupdate=False)
            else:
                self.foodbank.save(do_geoupdate=False, do_decache=False)

    class Meta:
        app_label = 'givefood'
        indexes = [
            models.Index(fields=['foodbank', '-created']),
            models.Index(fields=['published', 'foodbank']),
        ]


class FoodbankChangeTranslation(models.Model):

    need = models.ForeignKey(FoodbankChange, editable=False, on_delete=models.DO_NOTHING)
    foodbank = models.ForeignKey(Foodbank, editable=False, on_delete=models.DO_NOTHING)
    language = models.CharField(max_length = 2)
    change_text = models.TextField()
    excess_change_text = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.foodbank = self.need.foodbank
        super(FoodbankChangeTranslation, self).save(*args, **kwargs)

    class Meta:
        app_label = 'givefood'



class FoodbankChangeLine(models.Model):

    need = models.ForeignKey(FoodbankChange, editable=False, on_delete=models.DO_NOTHING)
    foodbank = models.ForeignKey(Foodbank, editable=False, on_delete=models.DO_NOTHING)
    item = models.CharField(max_length=250)
    type = models.CharField(max_length=250, choices=NEED_LINE_TYPES_CHOICES)
    category = models.CharField(max_length=250, choices=ITEM_CATEGORIES_CHOICES)
    group = models.CharField(max_length=250, choices=ITEM_GROUPS_CHOICES, editable=False)
    created = models.DateTimeField(editable=False)

    def save(self, *args, **kwargs):
        self.foodbank = self.need.foodbank
        self.group = ITEM_CATEGORY_GROUPS[self.category]
        self.created = self.need.created
        super(FoodbankChangeLine, self).save(*args, **kwargs)

    def __str__(self):
        return "%s - %s" % (self.foodbank, self.item)

    class Meta:
        app_label = 'givefood'
