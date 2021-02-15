# encoding: utf-8

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from google.appengine.api import datastore_errors

from djangae.contrib import sleuth
from djangae.fields import CharField, ComputedCollationField
from djangae.test import TestCase


@python_2_unicode_compatible
class CCollationModel(models.Model):
    field1 = CharField()
    field1_order = ComputedCollationField('field1')

    field2 = models.TextField()
    field2_order = ComputedCollationField('field2')

    def __str__(self):
        return self.field1


class ComputedCollationFieldTests(TestCase):

    def test_unicode(self):
        instance = CCollationModel(field1=u"A unicode string")
        try:
            instance.save()
        except TypeError:
            self.fail("Error saving unicode value")

    def test_basic_usage(self):
        instance1 = CCollationModel.objects.create(field1=u"Đavid")
        instance2 = CCollationModel.objects.create(field1=u"Łukasz")
        instance3 = CCollationModel.objects.create(field1=u"Anna")
        instance4 = CCollationModel.objects.create(field1=u"Ăna")
        instance5 = CCollationModel.objects.create(field1=u"Anja")
        instance6 = CCollationModel.objects.create(field1=u"ᚠera")

        results = CCollationModel.objects.order_by("field1_order")

        self.assertEqual(results[0], instance4)
        self.assertEqual(results[1], instance5)
        self.assertEqual(results[2], instance3)
        self.assertEqual(results[3], instance1)
        self.assertEqual(results[4], instance2)
        self.assertEqual(results[5], instance6)

    def test_really_long_string(self):
        long_string = "".join(["A"] * 1501)
        instance1 = CCollationModel.objects.create(field2=long_string)

        with sleuth.watch("djangae.fields.language.logger.warn") as warn:
            try:
                instance1.save()
                self.assertTrue(warn.called)
            except datastore_errors.BadRequestError:
                self.fail("Threw bad request when saving collation key")
