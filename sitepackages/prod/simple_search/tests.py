# -*- coding: utf-8 -*-
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import unittest
from django.db import models

from djangae.test import TestCase

from .models import (
    TermCount,
    InstanceIndex,
    index_instance,
    unindex_instance,
    search
)

class SampleModel(models.Model):
    field1 = models.CharField(max_length=1024)
    field2 = models.CharField(max_length=1024)

    def __unicode__(self):
        return u"{} - {}".format(self.field1, self.field2)

class SearchTests(TestCase):
    def test_field_indexing(self):
        instance1 = SampleModel.objects.create(
            field1="bananas apples cherries plums oranges kiwi bananas"
        )

        index_instance(instance1, ["field1"], defer_index=False)

        self.assertEqual(1, InstanceIndex.objects.filter(iexact="bananas").count())
        self.assertEqual(2, InstanceIndex.objects.get(iexact="bananas").count)
        self.assertEqual(1, InstanceIndex.objects.filter(iexact="apples").count())
        self.assertEqual(1, InstanceIndex.objects.filter(iexact="cherries").count())
        self.assertEqual(1, InstanceIndex.objects.filter(iexact="plums").count())
        self.assertEqual(1, InstanceIndex.objects.filter(iexact="oranges").count())
        self.assertEqual(1, InstanceIndex.objects.filter(iexact="kiwi").count())

    def test_partial_generation(self):
        instance1 = SampleModel.objects.create(field1="bananas")
        index_instance(instance1, ["field1"], defer_index=False)

        index = InstanceIndex.objects.get(iexact="bananas")

        # Check vowels are replaced
        self.assertTrue("bonanas" in index.partials)
        self.assertTrue("bononas" in index.partials)
        self.assertTrue("bononos" in index.partials)

        # Check the original term is there
        self.assertTrue("bananas" in index.partials)

        # Check starts with things
        self.assertTrue("bana" in index.partials)
        self.assertTrue("banan" in index.partials)
        self.assertTrue("banana" in index.partials)
        self.assertTrue("bananas" in index.partials)

        # Check missing letters
        self.assertTrue("bnanas" in index.partials)
        self.assertTrue("baanas" in index.partials)
        self.assertTrue("bannas" in index.partials)

    def test_partial_matching(self):
        instance1 = SampleModel.objects.create(field1="bananas")
        instance2 = SampleModel.objects.create(field1="bana")

        index_instance(instance1, ["field1"], defer_index=False)
        index_instance(instance2, ["field1"], defer_index=False)

        results = search(SampleModel, "bana")

        self.assertEqual(instance2, results[0])
        self.assertEqual(instance1, results[1])

    def test_partial_ranking(self):
        instance2 = SampleModel.objects.create(field1="some other thing 2")
        instance1 = SampleModel.objects.create(field1="extra thing 2")

        index_instance(instance1, ["field1"], defer_index=False)
        index_instance(instance2, ["field1"], defer_index=False)

        results = search(SampleModel, "extr 2")

        self.assertEqual(instance1, results[0])
        self.assertEqual(instance2, results[1])

    def test_ordering(self):
        instance1 = SampleModel.objects.create(field1="eat a fish")
        instance2 = SampleModel.objects.create(field1="eat a chicken")
        instance3 = SampleModel.objects.create(field1="sleep a lot")

        index_instance(instance1, ["field1"], defer_index=False)
        index_instance(instance2, ["field1"], defer_index=False)
        index_instance(instance3, ["field1"], defer_index=False)

        results = search(SampleModel, "eat a")

        #Instance 3 should come last, because it only contains "a"
        self.assertEqual(instance3, results[2], results)

        results = search(SampleModel, "eat fish")

        self.assertEqual(instance1, results[0]) #Instance 1 matches 2 uncommon words
        self.assertEqual(instance2, results[1]) #Instance 2 matches 1 uncommon word

    def test_basic_searching(self):
        self.assertEqual(0, SampleModel.objects.count())
        self.assertEqual(0, TermCount.objects.count())

        instance1 = SampleModel.objects.create(field1="Banana", field2="Apple")
        instance2 = SampleModel.objects.create(field1="banana", field2="Cherry")
        instance3 = SampleModel.objects.create(field1="BANANA")

        index_instance(instance1, ["field1", "field2"], defer_index=False)
        self.assertEqual(2, InstanceIndex.objects.count())
        self.assertEqual(1, TermCount.objects.get(pk="banana").count)
        self.assertEqual(1, TermCount.objects.get(pk="apple").count)

        index_instance(instance2, ["field1", "field2"], defer_index=False)

        self.assertEqual(4, InstanceIndex.objects.count())
        self.assertEqual(2, TermCount.objects.get(pk="banana").count)
        self.assertEqual(1, TermCount.objects.get(pk="apple").count)
        self.assertEqual(1, TermCount.objects.get(pk="cherry").count)

        index_instance(instance3, ["field1"], defer_index=False)
        self.assertEqual(5, InstanceIndex.objects.count())
        self.assertEqual(3, TermCount.objects.get(pk="banana").count)
        self.assertEqual(1, TermCount.objects.get(pk="apple").count)
        self.assertEqual(1, TermCount.objects.get(pk="cherry").count)

        self.assertItemsEqual([instance1, instance2, instance3], search(SampleModel, "banana"))
        self.assertItemsEqual([instance2], search(SampleModel, "cherry"))

        unindex_instance(instance1, ["field1", "field2"])

        self.assertItemsEqual([instance2, instance3], search(SampleModel, "banana"))
        self.assertItemsEqual([instance2], search(SampleModel, "cherry"))

    def test_additional_filters(self):
        instance1 = SampleModel.objects.create(field1="banana", field2="apple")
        instance2 = SampleModel.objects.create(field1="banana", field2="cherry")
        instance3 = SampleModel.objects.create(field1="pineapple", field2="apple")

        index_instance(instance1, ["field2"], defer_index=False)
        index_instance(instance2, ["field2"], defer_index=False)
        index_instance(instance3, ["field2"], defer_index=False)

        self.assertItemsEqual([instance1, instance3], search(SampleModel, "apple"))

        # Now pass to search a queryset filter and check that it's applied
        self.assertItemsEqual([instance1], search(SampleModel, "apple", **{'field1': 'banana'}))

    @unittest.skip("Not implemented yet")
    def test_logic_searching(self):
        instance1 = SampleModel.objects.create(field1="Banana", field2="Apple")
        instance2 = SampleModel.objects.create(field1="banana", field2="Cherry")
        instance3 = SampleModel.objects.create(field1="BANANA")

        index_instance(instance1, ["field1", "field2"], defer_index=False)
        index_instance(instance2, ["field1", "field2"], defer_index=False)
        index_instance(instance3, ["field1"], defer_index=False)

        self.assertItemsEqual([instance1], search(SampleModel, "banana AND apple"))
        self.assertItemsEqual([instance1, instance2], search(SampleModel, "apple OR cherry"))

        unindex_instance(instance1)

        self.assertItemsEqual([], search(SampleModel, "banana AND apple"))
        self.assertItemsEqual([instance2], search(SampleModel, "apple OR cherry"))

    def test_multiple_unindexing_only_does_one(self):
        instance1 = SampleModel.objects.create(field1="Banana", field2="Apple")
        index_instance(instance1, ["field1", "field2"], defer_index=False)

        goc = TermCount.objects.get(pk="banana")
        self.assertEqual(1, goc.count)

        for i in xrange(5):
            unindex_instance(instance1, ["field1", "field2"])

        goc = TermCount.objects.get(pk="banana")
        self.assertEqual(0, goc.count)

    def test_multiple_indexing_only_does_one(self):
        instance1 = SampleModel.objects.create(field1="Banana", field2="Apple")
        index_instance(instance1, ["field1", "field2"], defer_index=False)
        index_instance(instance1, ["field1", "field2"], defer_index=False)
        index_instance(instance1, ["field1", "field2"], defer_index=False)

        goc = TermCount.objects.get(pk="banana")
        self.assertEqual(1, goc.count)
        self.assertEqual(2, InstanceIndex.objects.count())

    def test_non_ascii_characters_in_search_string(self):
        """
        Validates that using a search string with characters outside the ASCII
        set works as expected.
        """
        instance1 = SampleModel.objects.create(field1="Banana", field2=u"čherry")
        index_instance(instance1, ["field1", "field2"], defer_index=False)
        self.assertItemsEqual([instance1], search(SampleModel, u"čherry"))

    def test_indexing_special_characters(self):
        """
        Test that nothing trips up when indexing terms that include special
        characters.
        """
        instance1 = SampleModel.objects.create(field1="ąpple ćhęrry")
        index_instance(instance1, ["field1"], defer_index=False)

        self.assertEqual(1, InstanceIndex.objects.filter(iexact="ąpple").count())
        self.assertEqual(1, InstanceIndex.objects.filter(iexact="ćhęrry").count())
