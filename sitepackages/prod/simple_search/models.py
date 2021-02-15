import shlex
import time
import hashlib
import math
import collections

from django.db import models
from django.utils.encoding import smart_str, smart_unicode
from django.conf import settings
from djangae.db import transaction
from djangae.fields import SetField
from google.appengine.ext import deferred

"""
    REMAINING TO DO!

    1. Partial matches. These should be recorded as new Index instances, with an FK to the full term being indexes.
       Partials should only be recorded for between 4, and len(original_term) - 1 characters. Partial matches should be much more highly scored,
       the lower the match, the more the score should be
    2. Cross-join indexing  e.g. book__title on an Author.
    3. Field matches. e.g "id:1234 field1:banana". This should match any other words using indexes, but only return matches that match the field lookups
"""

QUEUE_FOR_INDEXING = getattr(settings, "QUEUE_FOR_INDEXING", "default")


def get_data_from_field(field_, instance_):
    lookups = field_.split("__")
    value = instance_
    for lookup in lookups:
        if value is None:
            continue
        value = getattr(value, lookup)

        if "RelatedManager" in value.__class__.__name__:
            if lookup == lookups[-2]:
                return [ getattr(x, lookups[-1]) for x in value.all() ]
            else:
                raise TypeError("You can only index one level of related object")

        elif hasattr(value, "__iter__"):
            if lookup == lookups[-1]:
                return value
            else:
                raise TypeError("You can only index one level of iterable")

    return value


def _process_texts(instance, fields_to_index, func):
    for field in fields_to_index:
        texts = get_data_from_field(field, instance)
        if not isinstance(texts, (list, set, tuple)):
            texts = [ texts ]

        for text in texts:
            terms = parse_terms(text)

            for term in terms:
                func(instance, text, term)


def _do_unindex(instance, fields_to_index):
    def callback(instance, text, term):
        try:
            with transaction.atomic(xg=True):
                index = InstanceIndex.objects.get(pk=InstanceIndex.calc_id(term, instance))

                counter = TermCount.objects.get(pk=term)
                counter.count -= index.count
                counter.save()

                index.delete()
        except (InstanceIndex.DoesNotExist, TermCount.DoesNotExist):
            pass

    _process_texts(instance, fields_to_index, callback)


def _do_index(instance, fields_to_index):
    try:
        instance = instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        _do_unindex(instance)
        return

    def callback(instance, text, term):
        with transaction.atomic(xg=True):
            term_count = text.lower().count(term)
            index_pk = InstanceIndex.calc_id(term, instance)
            try:
                index = InstanceIndex.objects.get(pk=index_pk)

                if index.count == term_count:
                    return
                else:
                    # OK, something weird happened and we indexed twice
                    # we need to just need to figure out what difference we need to add to
                    # the global count!
                    term_count = term_count - index.count
            except InstanceIndex.DoesNotExist:
                index = InstanceIndex.objects.create(
                    pk=index_pk,
                    **{
                        "count": term_count,
                        "iexact": term,
                        "instance_db_table": instance._meta.db_table,
                        "instance_pk": instance.pk,
                    }
                )

            counter, created = TermCount.objects.get_or_create(
                pk=term
            )
            counter.count += term_count
            counter.save()

    _process_texts(instance, fields_to_index, callback)


def _unindex_then_reindex(instance, fields_to_index):
    _do_unindex(instance, fields_to_index)
    _do_index(instance, fields_to_index)


def index_instance(instance, fields_to_index, defer_index=True):
    if defer_index:
        deferred.defer(_unindex_then_reindex, instance, fields_to_index,
                        _queue=QUEUE_FOR_INDEXING, _transactional=transaction.in_atomic_block())
    else:
        _unindex_then_reindex(instance, fields_to_index)


def unindex_instance(instance, fields_to_index):
    _do_unindex(instance, fields_to_index)


def parse_terms(search_string):
    terms = smart_str(search_string.lower()).split()

    # The split requires the unicode string to be encoded to a bytestring, but
    # we need the terms to be decoded back to utf-8 for use in the datastore queries.
    return [smart_unicode(term) for term in terms]


Match = collections.namedtuple("Match", ("count", "term", "partial"))

def search(model_class, search_string, per_page=50, current_page=1, total_pages=10, **filters):
    terms = parse_terms(search_string)

    #Get all matching terms
    matches = InstanceIndex.objects.filter(
        partials__in=terms,
        instance_db_table=model_class._meta.db_table
    ).values("partials", "iexact", "instance_pk")

    matching_terms = dict(TermCount.objects.filter(pk__in=[ x["iexact"] for x in matches ]).values_list('pk', 'count'))

    instance_weights = {}

    for match in matches:
        # This might not be the best matching partial, for that we'd have to work out the
        # difference... not sure if this is worthy of a fixme though...
        matching_partial = (x for x in match["partials"] if x in terms).next()
        instance_weights.setdefault(match["instance_pk"], []).append(Match(matching_terms[match["iexact"]], match["iexact"], matching_partial))

    final_weights = []
    for k, v in instance_weights.items():
        """
            This is where we rank the results. Lower scores are better. Scores are based
            on the commonality of the word. More matches are rewarded, but not too much so
            that rarer terms still have a chance.

            Examples for n matches:

            1 = 1 + (0 * 0.5) = 1    -> scores / 1
            2 = 2 + (1 * 0.5) = 2.5  -> scores / 2.5 (rather than 2)
            3 = 3 + (2 * 0.5) = 4    -> scores / 4 (rather than 3)

            We penalize partial matches by the percentage difference based on the length
            of the term
        """

        n = float(len(v))

        final_counts = []
        for match in v:
            count = match.count
            partial = match.partial
            term = match.term

            term_length = len(term)
            partial_length = len(partial)

            # Here we penalize counts if they are partial matches depending on
            # how loosely they match the term. Remember lower is better, so we
            # bump the score
            min_length = min(term_length, partial_length)
            max_length = max(term_length, partial_length)
            difference = abs(term_length - partial_length)
            difference += sum([1 for i in xrange(min_length) if match.term[i] != match.partial[i]])
            penalization = 1.0 + ((1.0 / float(max_length)) * float(difference))

            final_counts.append(count * penalization)

        score = sum(final_counts) / (n + ((n-1) * 0.5))

        final_weights.append((score, k))

    final_weights.sort()

    #Restrict to the max possible
    final_weights = final_weights[:total_pages*per_page]

    #Restrict to the page
    offset = ((current_page - 1) * per_page)
    final_weights = final_weights[offset:offset + per_page]

    order = {}
    for index, (score, pk) in enumerate(final_weights):
        order[pk] = index

    sorted_results = [None] * len(order.keys())

    queryset = model_class.objects.all()
    if filters:
        queryset = queryset.filter(**filters)

    results = queryset.filter(pk__in=order.keys())
    for result in results:
        position = order[result.pk]
        sorted_results[position] = result

    return [x for x in sorted_results if x ]


class TermCount(models.Model):
    id = models.CharField(max_length=1024, primary_key=True)
    count = models.PositiveIntegerField(default=0)

    def update(self):
        while True:
            try:
                count = 0
                for index in InstanceIndex.objects.filter(iexact=self.id):
                    count += InstanceIndex.objects.get(pk=index.pk).count

                with transaction.atomic():
                    goc = TermCount.objects.get(pk=self.id)
                    goc.count = count
                    goc.save()

            except transaction.TransactionFailedError:
                time.sleep(1)
                continue


class InstanceIndex(models.Model):
    @classmethod
    def calc_id(cls, term, instance):
        source = u"|".join([term, instance.__class__._meta.db_table, unicode(instance.pk)])
        return hashlib.md5(source.encode("utf-8")).hexdigest()

    id = models.CharField(max_length=500, primary_key=True)
    iexact = models.CharField(max_length=1024)
    instance_db_table = models.CharField(max_length=1024)
    instance_pk = models.PositiveIntegerField(default=0)
    count = models.PositiveIntegerField(default=0)

    partials = SetField(models.CharField(max_length=500))

    class Meta:
        unique_together = [
            ('iexact', 'instance_db_table', 'instance_pk')
        ]

    def _generate_partials(self):
        """
            Partials are anything we want to match when doing fuzzy matching
            change this logic if you can think of more possibilities!
        """

        partials = set([self.iexact]) #We always include the term itself for easier querying
        length = len(self.iexact)
        for i in xrange(int(math.floor(float(length) / 2.0)), length):
            s = self.iexact[:i]
            # We want to match the first half of the word always
            # but be fuzzy with the last half
            partials.add(s)

        # Now, just add the term with characters missing
        for j in xrange(1, len(self.iexact)):
            partials.add(self.iexact[:j] + self.iexact[j+1:])

        # And swap out vowels
        vowels = "aeiou"
        for i, vowel in enumerate(vowels):
            others = vowels[:i] + vowels[i+1:]
            for other in others:
                s = self.iexact
                while vowel in s:
                    s = s.replace(vowel, other, 1)
                    partials.add(s)
        return partials

    def save(self, *args, **kwargs):
        self.partials = self._generate_partials()
        return super(InstanceIndex, self).save(*args, **kwargs)

from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete

@receiver(post_save)
def post_save_index(sender, instance, created, raw, *args, **kwargs):
    if getattr(instance, "Search", None):
        fields_to_index = getattr(instance.Search, "fields", [])
        if fields_to_index:
            index_instance(instance, fields_to_index, defer_index=not raw) #Don't defer if we are loading from a fixture

@receiver(pre_delete)
def pre_delete_unindex(sender, instance, using, *args, **kwarg):
    if getattr(instance, "Search", None):
        fields_to_index = getattr(instance.Search, "fields", [])
        if fields_to_index:
            unindex_instance(instance, fields_to_index)
