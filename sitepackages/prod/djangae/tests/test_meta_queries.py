from django.db import models
from djangae.test import TestCase

from djangae.contrib import sleuth


class MetaQueryTestModel(models.Model):
    field1 = models.CharField(max_length=32)


class PrimaryKeyFilterTests(TestCase):

    def test_pk_in_with_slicing(self):
        i1 = MetaQueryTestModel.objects.create();

        self.assertFalse(
            MetaQueryTestModel.objects.filter(pk__in=[i1.pk])[9999:]
        )

        self.assertFalse(
            MetaQueryTestModel.objects.filter(pk__in=[i1.pk])[9999:10000]
        )

    def test_limit_correctly_applied_per_branch(self):
        MetaQueryTestModel.objects.create(field1="test")
        MetaQueryTestModel.objects.create(field1="test2")

        with sleuth.watch('google.appengine.api.datastore.Query.Run') as run_calls:

            list(MetaQueryTestModel.objects.filter(field1__in=["test", "test2"])[:1])

            self.assertEqual(1, run_calls.calls[0].kwargs['limit'])
            self.assertEqual(1, run_calls.calls[1].kwargs['limit'])

        with sleuth.watch('google.appengine.api.datastore.Query.Run') as run_calls:

            list(MetaQueryTestModel.objects.filter(field1__in=["test", "test2"])[1:2])

            self.assertEqual(2, run_calls.calls[0].kwargs['limit'])
            self.assertEqual(2, run_calls.calls[1].kwargs['limit'])
