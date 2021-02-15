"""
    Test that you can query on json field properties
"""

from google.appengine.api.datastore import Get, Key

from djangae.fields import JSONField
from djangae.test import TestCase
from django.core import serializers
from django.db import connection, models


class Dog(models.Model):
    name = models.CharField(max_length=32)
    data = JSONField()


class JSONFieldTests(TestCase):
    def _fetch_entity(self, instance):
        kind = instance._meta.db_table
        namespace = connection.settings_dict["NAMESPACE"]

        return Get(
            Key.from_path(kind, instance.pk, namespace=namespace)
        )

    def test_matching_then_unmatching(self):
        dog1 = Dog.objects.create(name="Suzi", data={"breed": "cross"})

        self.assertEqual(dog1, Dog.objects.get(data__breed="cross"))

        dog1.data = {"breed": "dalmation"}
        dog1.save()

        self.assertRaises(Dog.DoesNotExist, Dog.objects.get, data__breed="cross")

    def test_none_queryable(self):
        dog1 = Dog.objects.create(name="Jude", data={"breed": None})

        Dog.objects.create(name="Bilbo", data={}) # This shouldn't come back None != no value

        self.assertEqual(dog1, Dog.objects.get(data__breed__isnull=True))

    def test_field_querying(self):
        dog1 = Dog.objects.create(name='Rufus', data={
            'breed': 'labrador',
            'owner': {
                'name': 'Bob',
                'other_pets': [{
                    'name': 'Fishy'
                }]
            }
        })

        Dog.objects.create(name='Meg', data={'breed': 'collie'})

        self.assertEqual(
            dog1,
            Dog.objects.get(
                data__breed='labrador'
            )
        )

        self.assertEqual(
            dog1,
            Dog.objects.get(
                data__owner__other_pets__0__name='Fishy'
            )
        )

        entity = self._fetch_entity(dog1)

        # We should have two index properties
        index_fields = [x for x in entity if x.startswith("_idx")]
        self.assertEqual(3, len(index_fields))

        # Wipe out the data
        dog1.data = {}
        dog1.save()

        entity = self._fetch_entity(dog1)

        # There should be no index fields now
        index_fields = [x for x in entity if x.startswith("_idx")]
        self.assertFalse(index_fields)

    def test_serialization_and_deserialization(self):
        dog = Dog.objects.create(name="Bingo", data={"One": "one"})

        dogs = serializers.deserialize('json', serializers.serialize('json', [dog]))
        dog = next(dogs).object

        self.assertEqual(dog.data["One"], "one")
