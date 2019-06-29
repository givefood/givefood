from django.db import models
from djangae.contrib import sleuth
from djangae.test import TestCase, inconsistent_db
from djangae.utils import get_next_available_port
from djangae.db.consistency import ensure_instance_consistent, ensure_instances_consistent


class AvailablePortTests(TestCase):

    def test_get_next_available_port(self):
        url = "127.0.0.1"
        port = 8081
        self.assertEquals(8081, get_next_available_port(url, port))
        with sleuth.switch("djangae.utils.port_is_open",
                lambda *args, **kwargs: False if args[1] < 8085 else True):
            self.assertEquals(8085, get_next_available_port(url, port))


class EnsureCreatedModel(models.Model):
    field1 = models.IntegerField()

    class Meta:
        app_label = "djangae"

    def __unicode__(self):
        return u"PK: {}, field1 {}".format(self.pk, self.field1)


class EnsureCreatedTests(TestCase):

    def test_basic_usage(self):
        for i in xrange(5):
            EnsureCreatedModel.objects.create(
                pk=i + 1,
                field1=i
            )

        with inconsistent_db():
            new_instance = EnsureCreatedModel.objects.create(
                pk=7,
                field1=3
            )

            qs = EnsureCreatedModel.objects.all()
            self.assertEqual(5, len(qs)) # Make sure we don't get the new instance
            self.assertEqual(6, len(ensure_instance_consistent(qs, new_instance.pk))) # Make sure we do
            self.assertEqual(5, len(ensure_instance_consistent(qs[:5], new_instance.pk))) # Make sure slicing returns the right number
            self.assertEqual(3, len(ensure_instance_consistent(qs[2:5], new_instance.pk))) # Make sure slicing returns the right number

            evaled = [ x for x in ensure_instance_consistent(qs.order_by("field1"), new_instance.pk) ]
            self.assertEqual(new_instance, evaled[4]) # Make sure our instance is correctly positioned

            evaled = [ x for x in ensure_instance_consistent(qs.order_by("-field1"), new_instance.pk) ]
            self.assertEqual(new_instance, evaled[1], evaled) # Make sure our instance is correctly positioned

            evaled = [ x for x in ensure_instance_consistent(qs.order_by("-field1"), new_instance.pk)[:2] ]
            self.assertEqual(new_instance, evaled[1], evaled) # Make sure our instance is correctly positioned

            another_instance = EnsureCreatedModel.objects.create(
                pk=8,
                field1=3
            )

            self.assertEqual(5, len(qs)) # Make sure we don't get the new instance
            self.assertEqual(7, len(ensure_instances_consistent(qs, [new_instance.pk, another_instance.pk]))) # Make sure we do

            instance_id = another_instance.pk
            another_instance.delete()

            self.assertEqual(6, len(ensure_instances_consistent(qs, [new_instance.pk, instance_id]))) # Make sure we do

        # Now we're in consistent land!
        self.assertTrue(EnsureCreatedModel.objects.filter(pk=7)[:1])
        self.assertEqual(6, len(ensure_instance_consistent(qs, new_instance.pk)))

        # Make sure it's not returned if it was deleted
        new_instance.delete()
        self.assertEqual(5, len(ensure_instance_consistent(qs, 7)))

        new_instance = EnsureCreatedModel.objects.create(pk=8, field1=8)
        self.assertEqual(1, list(ensure_instance_consistent(qs, 8)).count(new_instance))

    def test_add_many_instances(self):
        for i in xrange(5):
            EnsureCreatedModel.objects.create(
                pk=i + 1,
                field1=i + 5
            )

        with inconsistent_db():
            new_instances = []
            for i in xrange(3):
                instance = EnsureCreatedModel.objects.create(
                    pk=i + 7,
                    field1=i
                )
                new_instances.append(instance)

            new_instance_pks = [i.pk for i in new_instances]

            qs = EnsureCreatedModel.objects.all()
            self.assertEqual(5, len(qs))  # Make sure we don't get the new instance
            self.assertEqual(8, len(ensure_instances_consistent(qs, new_instance_pks)))

            evaled = [ x for x in ensure_instances_consistent(qs.order_by("field1"), new_instance_pks) ]
            self.assertEqual(new_instances[0], evaled[0])  # Make sure our instance is correctly positioned
            self.assertEqual(new_instances[1], evaled[1])  # Make sure our instance is correctly positioned
            self.assertEqual(new_instances[2], evaled[2])  # Make sure our instance is correctly positioned

        # Now we're in consistent land!
        self.assertTrue(EnsureCreatedModel.objects.filter(pk=7)[:1])
        self.assertTrue(EnsureCreatedModel.objects.filter(pk=8)[:1])
        self.assertEqual(8, len(ensure_instances_consistent(qs, new_instance_pks)))

        # Make sure it's not returned if it was deleted
        for instance in new_instances:
            instance.delete()
        self.assertEqual(5, len(ensure_instances_consistent(qs, new_instance_pks)))

    def test_delete_many_instances(self):
        for i in xrange(5):
            EnsureCreatedModel.objects.create(
                pk=i + 1,
                field1=i + 5
            )

        instances_to_delete = []
        for i in xrange(3):
            instance = EnsureCreatedModel.objects.create(
                pk=i + 7,
                field1=i + 1
            )
            instances_to_delete.append(instance)

        instances_to_delete_pks = [i.pk for i in instances_to_delete]

        qs = EnsureCreatedModel.objects.all()
        self.assertEqual(8, len(ensure_instances_consistent(qs, instances_to_delete_pks)))
        with inconsistent_db():
            # Make sure it's not returned if it was deleted
            for instance in instances_to_delete:
                instance.delete()
            self.assertEqual(5, len(ensure_instances_consistent(qs, instances_to_delete_pks)))
