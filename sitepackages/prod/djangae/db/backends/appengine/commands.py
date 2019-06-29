#STANDARD LIB
from datetime import datetime
import logging
import copy
import decimal
import json
import contextlib

from functools import partial
from itertools import chain, groupby

#LIBRARIES
import django
from django.db import DatabaseError
from django.db import IntegrityError

from google.appengine.api import datastore, datastore_errors, memcache
from google.appengine.datastore import datastore_rpc, datastore_stub_util
from google.appengine.api.datastore import Query
from google.appengine.ext import db

#DJANGAE
from djangae.db.backends.appengine.dbapi import NotSupportedError
from djangae.db.utils import (
    get_datastore_key,
    django_instance_to_entity,
    MockInstance,
    has_concrete_parents,
    get_field_from_column,
    ensure_datetime,
)

from djangae.db.backends.appengine import POLYMODEL_CLASS_ATTRIBUTE
from djangae.db import constraints, utils
from djangae.db.backends.appengine import caching
from djangae.db.unique_utils import query_is_unique
from djangae.db.backends.appengine import transforms

DATE_TRANSFORMS = {
    "year": transforms.year_transform,
    "month": transforms.month_transform,
    "day": transforms.day_transform,
    "hour": transforms.hour_transform,
    "minute": transforms.minute_transform,
    "second": transforms.second_transform
}

DJANGAE_LOG = logging.getLogger("djangae")

OPERATORS_MAP = {
    'exact': '=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',

    # The following operators are supported with special code below.
    'isnull': None,
    'in': None,
    'range': None,
}

EXTRA_SELECT_FUNCTIONS = {
    '+': lambda x, y: x + y,
    '-': lambda x, y: x - y,
    '/': lambda x, y: x / y,
    '*': lambda x, y: x * y,
    '<': lambda x, y: x < y,
    '>': lambda x, y: x > y,
    '=': lambda x, y: x == y
}

REVERSE_OP_MAP = {
    '=':'exact',
    '>':'gt',
    '>=':'gte',
    '<':'lt',
    '<=':'lte',
}

INEQUALITY_OPERATORS = frozenset(['>', '<', '<=', '>='])


def _cols_from_where_node(where_node):
    cols = where_node.get_cols() if hasattr(where_node, 'get_cols') else where_node.get_group_by_cols()
    return cols

def _get_tables_from_where(where_node):
    cols = _cols_from_where_node(where_node)
    if django.VERSION[1] < 8:
        return list(set([x[0] for x in cols if x[0] ]))
    else:
        return list(set([x.alias for x in cols]))


def field_conv_year_only(value):
    value = ensure_datetime(value)
    return datetime(value.year, 1, 1, 0, 0)


def field_conv_month_only(value):
    value = ensure_datetime(value)
    return datetime(value.year, value.month, 1, 0, 0)


def field_conv_day_only(value):
    value = ensure_datetime(value)
    return datetime(value.year, value.month, value.day, 0, 0)


def coerce_unicode(value):
    if isinstance(value, str):
        try:
            value = value.decode('utf-8')
        except UnicodeDecodeError:
            # This must be a Django databaseerror, because the exception happens too
            # early before Django's exception wrapping can take effect (e.g. it happens on SQL
            # construction, not on execution.
            raise DatabaseError("Bytestring is not encoded in utf-8")

    # The SDK raises BadValueError for unicode sub-classes like SafeText.
    return unicode(value)


FILTER_CMP_FUNCTION_MAP = {
    'exact': lambda a, b: a == b,
    'iexact': lambda a, b: a.lower() == b.lower(),
    'gt': lambda a, b: a > b,
    'lt': lambda a, b: a < b,
    'gte': lambda a, b: a >= b,
    'lte': lambda a, b: a <= b,
    'isnull': lambda a, b: (b and (a is None)) or (a is not None),
    'in': lambda a, b: a in b,
    'startswith': lambda a, b: a.startswith(b),
    'range': lambda a, b: b[0] < a < b[1], #I'm assuming that b is a tuple
    'year': lambda a, b: field_conv_year_only(a) == b,
}


def log_once(logging_call, text, args):
    """
        Only logs one instance of the combination of text and arguments to the passed
        logging function
    """
    identifier = "%s:%s" % (text, args)
    if identifier in log_once.logged:
        return
    logging_call(text % args)
    log_once.logged.add(identifier)

log_once.logged = set()


def _convert_entity_based_on_query_options(entity, opts):
    if opts.keys_only:
        return entity.key()

    if opts.projection:
        for k in entity.keys()[:]:
            if k not in list(opts.projection) + [POLYMODEL_CLASS_ATTRIBUTE]:
                del entity[k]

    return entity


class QueryByKeys(object):
    """ Does the most efficient fetching possible for when we have the keys of the entities we want. """

    def __init__(self, model, queries, ordering, namespace):
        # `queries` should be filtered by __key__ with keys that have the namespace applied to them.
        # `namespace` is passed for explicit niceness (mostly so that we don't have to assume that
        # all the keys belong to the same namespace, even though they will).
        def _get_key(query):
            result = query["__key__ ="]
            return result

        self.model = model
        self.namespace = namespace

        # groupby requires that the iterable is sorted by the given key before grouping
        self.queries = sorted(queries, key=_get_key)
        self.queries_by_key = { a: list(b) for a, b in groupby(self.queries, _get_key) }

        self.ordering = ordering
        self._Query__kind = queries[0]._Query__kind

    def Run(self, limit=None, offset=None):
        """
            Here are the options:

            1. Single key, hit memcache
            2. Multikey projection, async MultiQueries with ancestors chained
            3. Full select, datastore get
        """

        opts = self.queries[0]._Query__query_options
        key_count = len(self.queries_by_key)

        is_projection = False

        results = None
        if key_count == 1:
            # FIXME: Potentially could use get_multi in memcache and the make a query
            # for whatever remains
            key = self.queries_by_key.keys()[0]
            result = caching.get_from_cache_by_key(key)
            if result is not None:
                results = [ result ]
                cache = False # Don't update cache, we just got it from there

        if results is None:
            if opts.projection:
                is_projection = True # Don't cache projection results!

                # Assumes projection ancestor queries are faster than a datastore Get
                # due to lower traffic over the RPC. This should be faster for queries with
                # < 30 keys (which is the most common case), and faster if the entities are
                # larger and there are many results, but there is probably a slower middle ground
                # because the larger number of RPC calls. Still, if performance is an issue the
                # user can just do a normal get() rather than values/values_list/only/defer

                to_fetch = (offset or 0) + limit if limit else None
                additional_cols = set([ x[0] for x in self.ordering if x[0] not in opts.projection])

                multi_query = []
                final_queries = []
                orderings = self.queries[0]._Query__orderings
                for key, queries in self.queries_by_key.iteritems():
                    for query in queries:
                        if additional_cols:
                            # We need to include additional orderings in the projection so that we can
                            # sort them in memory. Annoyingly that means reinstantiating the queries
                            query = Query(
                                kind=query._Query__kind,
                                filters=query,
                                projection=list(opts.projection).extend(list(additional_cols)),
                                namespace=self.namespace,
                            )

                        query.Ancestor(key) # Make this an ancestor query
                        multi_query.append(query)
                        if len(multi_query) == 30:
                            final_queries.append(datastore.MultiQuery(multi_query, orderings).Run(limit=to_fetch))
                            multi_query = []
                else:
                    if len(multi_query) == 1:
                        final_queries.append(multi_query[0].Run(limit=to_fetch))
                    elif multi_query:
                        final_queries.append(datastore.MultiQuery(multi_query, orderings).Run(limit=to_fetch))

                results = chain(*final_queries)
            else:
                results = datastore.Get(self.queries_by_key.keys())

        def iter_results(results):
            returned = 0
            # This is safe, because Django is fetching all results any way :(
            sorted_results = sorted(results, cmp=partial(utils.django_ordering_comparison, self.ordering))
            sorted_results = [result for result in sorted_results if result is not None]
            if not is_projection and sorted_results:
                caching.add_entities_to_cache(
                    self.model,
                    sorted_results,
                    caching.CachingSituation.DATASTORE_GET,
                    self.namespace,
                )

            for result in sorted_results:
                if is_projection:
                    entity_matches_query = True
                else:
                    entity_matches_query = any(
                        utils.entity_matches_query(result, qry) for qry in self.queries_by_key[result.key()]
                    )

                if not entity_matches_query:
                    continue

                if offset and returned < offset:
                    # Skip entities based on offset
                    returned += 1
                    continue
                else:

                    yield _convert_entity_based_on_query_options(result, opts)

                    returned += 1

                    # If there is a limit, we might be done!
                    if limit is not None and returned == (offset or 0) + limit:
                        break

        return iter_results(results)

    def Count(self, limit, offset):
        return len([ x for x in self.Run(limit, offset) ])


class NoOpQuery(object):
    def Run(self, limit, offset):
        return []

    def Count(self, limit, offset):
        return 0


class UniqueQuery(object):
    """
        This mimics a normal query but hits the cache if possible. It must
        be passed the set of unique fields that form a unique constraint
    """
    def __init__(self, unique_identifier, gae_query, model, namespace):
        self._identifier = unique_identifier
        self._gae_query = gae_query
        self._model = model
        self._namespace = namespace

        self._Query__kind = gae_query._Query__kind

    def get(self, x):
        return self._gae_query.get(x)

    def keys(self):
        return self._gae_query.keys()

    def Run(self, limit, offset):
        opts = self._gae_query._Query__query_options
        if opts.keys_only or opts.projection:
            return self._gae_query.Run(limit=limit, offset=offset)

        ret = caching.get_from_cache(self._identifier, self._namespace)
        if ret is not None and not utils.entity_matches_query(ret, self._gae_query):
            ret = None

        if ret is None:
            # We do a fast keys_only query to get the result
            keys_query = Query(self._gae_query._Query__kind, keys_only=True, namespace=self._namespace)
            keys_query.update(self._gae_query)
            keys = keys_query.Run(limit=limit, offset=offset)

            # Do a consistent get so we don't cache stale data, and recheck the result matches the query
            ret = [x for x in datastore.Get(keys) if x and utils.entity_matches_query(x, self._gae_query)]
            if len(ret) == 1:
                caching.add_entities_to_cache(
                    self._model,
                    [ret[0]],
                    caching.CachingSituation.DATASTORE_GET,
                    self._namespace,
                )
            return iter(ret)

        return iter([ret])

    def Count(self, limit, offset):
        return sum(1 for x in self.Run(limit, offset))


from djangae.db.backends.appengine.query import transform_query
from djangae.db.backends.appengine.dnf import normalize_query

def convert_django_ordering_to_gae(ordering):
    result = []

    for column in ordering:
        if column.startswith("-"):
            result.append((column.lstrip("-"), datastore.Query.DESCENDING))
        else:
            result.append((column, datastore.Query.ASCENDING))
    return result

def wrap_result_with_functor(results, func):
    for result in results:
        result = func(result)
        if result is not None:
            yield result

def limit_results_generator(results, limit):
    for result in results:
        yield result
        limit -= 1
        if not limit:
            raise StopIteration


def can_perform_datastore_get(normalized_query):
    """
        Given a normalized query, returns True if there is an equality
        filter on a key in each branch of the where
    """
    assert normalized_query.is_normalized

    for and_branch in normalized_query.where.children:
        if and_branch.is_leaf:
            if (and_branch.column != "__key__" or and_branch.operator != "="):
                return False
        else:
            key_found = False
            for filter_node in and_branch.children:
                assert filter_node.is_leaf

                if filter_node.column == "__key__":
                    if filter_node.operator == "=":
                        key_found = True
                        break

            if not key_found:
                return False

    return True


class SelectCommand(object):
    def __init__(self, connection, query, keys_only=False):
        self.connection = connection
        self.namespace = connection.ops.connection.settings_dict.get("NAMESPACE")

        self.query = transform_query(connection, query)
        self.query.prepare()
        self.query = normalize_query(self.query)

        self.original_query = query
        self.keys_only = (keys_only or [x.field for x in query.select] == [ query.model._meta.pk ])

        # MultiQuery doesn't support keys_only
        if self.query.where and len(self.query.where.children) > 1:
            self.keys_only = False

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.query.serialize() == other.query.serialize())

    def __ne__(self, other):
        return not self.__eq__(other)

    def _sanity_check(self):
        if self.query.distinct and not self.query.columns:
            raise NotSupportedError("Tried to perform distinct query when projection wasn't possible")

    def _exclude_pk(self, columns):
        if columns is None:
            return None

        opts = self.query.model._meta
        copts = self.query.concrete_model._meta

        return [
            x for x in columns if x not in
            (opts.pk.column, copts.pk.column)
        ]

    def _build_query(self):
        self._sanity_check()

        queries = []

        projection = self._exclude_pk(self.query.columns) or None

        query_kwargs = {
            "kind": self.query.concrete_model._meta.db_table,
            "distinct": self.query.distinct or None,
            "keys_only": self.keys_only or None,
            "projection": projection,
            "namespace": self.namespace,
        }

        ordering = convert_django_ordering_to_gae(self.query.order_by)

        if self.query.distinct and not ordering:
            # If we specified we wanted a distinct query, but we didn't specify
            # an ordering, we must set the ordering to the distinct columns, otherwise
            # App Engine shouts at us. Nastily. And without remorse.
            # The order of the columns in `ordering` makes a difference, but `distinct` is a set
            # and therefore unordered, but in  this situation (where the ordering has not been
            # explicitly defined) any order of the columns will do
            ordering = list(self.query.columns)

        # Deal with the no filters case
        if self.query.where is None:
            query = Query(
                **query_kwargs
            )
            try:
                query.Order(*ordering)
            except datastore_errors.BadArgumentError as e:
                raise NotSupportedError(e)
            return query

        assert self.query.where

        # Go through the normalized query tree
        for and_branch in self.query.where.children:
            query = Query(
                **query_kwargs
            )

            # This deals with the oddity that the root of the tree may well be a leaf
            filters = [ and_branch ] if and_branch.is_leaf else and_branch.children

            for filter_node in filters:
                lookup = "{} {}".format(filter_node.column, filter_node.operator)

                value = filter_node.value
                # This is a special case. Annoyingly Django's decimal field doesn't
                # ever call ops.get_prep_save or lookup or whatever when you are filtering
                # on a query. It *does* do it on a save, so we basically need to do a
                # conversion here, when really it should be handled elsewhere
                if isinstance(value, decimal.Decimal):
                    field = get_field_from_column(self.query.model, filter_node.column)
                    value = self.connection.ops.adapt_decimalfield_value(value, field.max_digits, field.decimal_places)
                elif isinstance(value, basestring):
                    value = coerce_unicode(value)
                elif isinstance(value, datastore.Key):
                    # Make sure we apply the current namespace to any lookups
                    # by key. Fixme: if we ever add key properties this will break if
                    # someone is trying to filter on a key which has a different namespace
                    # to the active one.
                    value = datastore.Key.from_path(
                        value.kind(),
                        value.id_or_name(),
                        namespace=self.namespace
                    )

                # If there is already a value for this lookup, we need to make the
                # value a list and append the new entry
                if lookup in query and not isinstance(query[lookup], (list, tuple)) and query[lookup] != value:
                    query[lookup] = [ query[lookup ] ] + [ value ]
                else:
                    # If the value is a list, we can't just assign it to the query
                    # which will treat each element as its own value. So in this
                    # case we nest it. This has the side effect of throwing a BadValueError
                    # which we could throw ourselves, but the datastore might start supporting
                    # list values in lookups.. you never know!
                    if isinstance(value, (list, tuple)):
                        query[lookup] = [ value ]
                    else:
                        # Common case: just add the raw where constraint
                        query[lookup] = value

            if ordering:
                try:
                    query.Order(*ordering)
                except datastore_errors.BadArgumentError as e:
                    # This is the easiest way to detect unsupported orderings
                    # ideally we'd detect this at the query normalization stage
                    # but it's a lot of hassle, this is much easier and seems to work OK
                    raise NotSupportedError(e)
            queries.append(query)

        if can_perform_datastore_get(self.query):
            # Yay for optimizations!
            return QueryByKeys(self.query.model, queries, ordering, self.namespace)

        if len(queries) == 1:
            identifier = query_is_unique(self.query.model, queries[0])
            if identifier:
                # Yay for optimizations!
                return UniqueQuery(identifier, queries[0], self.query.model, self.namespace)

            return queries[0]
        else:
            return datastore.MultiQuery(queries, ordering)

    def _fetch_results(self, query):
        # If we're manually excluding PKs, and we've specified a limit to the results
        # we need to make sure that we grab more than we were asked for otherwise we could filter
        # out too many! These are again limited back to the original request limit
        # while we're processing the results later

        # Apply the namespace before excluding
        excluded_pks = [
            datastore.Key.from_path(x.kind(), x.id_or_name(), namespace=self.namespace)
            for x in self.query.excluded_pks
        ]

        high_mark = self.query.high_mark
        low_mark = self.query.low_mark

        excluded_pk_count = 0
        if excluded_pks and high_mark:
            excluded_pk_count = len(excluded_pks)
            high_mark += excluded_pk_count

        limit = None if high_mark is None else (high_mark - (low_mark or 0))
        offset = low_mark or 0

        if self.query.kind == "COUNT":
            if excluded_pks:
                # If we're excluding pks, relying on a traditional count won't work
                # so we have two options:
                # 1. Do a keys_only query instead and count the results excluding keys
                # 2. Do a count, then a pk__in=excluded_pks to work out how many to subtract
                # Here I've favoured option one as it means a single RPC call. Testing locally
                # didn't seem to indicate much of a performance difference, even when doing the pk__in
                # with GetAsync while the count was running. That might not be true of prod though so
                # if anyone comes up with a faster idea let me know!
                if isinstance(query, QueryByKeys):
                    # If this is a QueryByKeys, just do the datastore Get and count the results
                    resultset = (x.key() for x in query.Run(limit=limit, offset=offset) if x)
                else:
                    count_query = Query(query._Query__kind, keys_only=True, namespace=self.namespace)
                    count_query.update(query)
                    resultset = count_query.Run(limit=limit, offset=offset)
                self.results = (x for x in [ len([ y for y in resultset if y not in excluded_pks]) ])
            else:
                self.results = (x for x in [query.Count(limit=limit, offset=offset)])
            return
        elif self.query.kind == "AVERAGE":
            raise ValueError("AVERAGE not yet supported")
        else:
            self.results = query.Run(limit=limit, offset=offset)

        # Ensure that the results returned is reset
        self.results_returned = 0

        def increment_returned_results(result):
            self.results_returned += 1
            return result

        def convert_key_to_entity(result):
            class FakeEntity(dict):
                def __init__(self, key):
                    self._key = key

                def key(self):
                    return self._key

            return FakeEntity(result)

        def rename_pk_field(result):
            if result is None:
                return result

            value = result.key().id_or_name()
            result[self.query.model._meta.pk.column] = value
            result[self.query.concrete_model._meta.pk.column] = value
            return result

        def process_extra_selects(result):
            """
                We handle extra selects by generating the new columns from
                each result. We can handle simple boolean logic and operators.
            """
            extra_selects = self.query.extra_selects
            model_fields = self.query.model._meta.fields

            DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S")

            def process_arg(arg):
                if arg.startswith("'") and arg.endswith("'"):
                    # String literal
                    arg = arg.strip("'")
                    # Check to see if this is a date
                    for date in DATE_FORMATS:
                        try:
                            value = datetime.strptime(arg, date)
                            return value
                        except ValueError:
                            continue
                    return arg
                elif arg in [ x.column for x in model_fields ]:
                    # Column value
                    return result.get(arg)

                # Handle NULL
                if arg.lower() == 'null':
                    return None
                elif arg.lower() == 'true':
                    return True
                elif arg.lower() == 'false':
                    return False

                # See if it's an integer
                try:
                    arg = int(arg)
                except (TypeError, ValueError):
                    pass

                # Just a plain old literal
                return arg

            for col, select in extra_selects:
                result[col] = select[0](*[ process_arg(x) for x in select[1] ])

            return result

        def convert_datetime_fields(result):
            fields = [
                x for x in self.query.model._meta.fields
                if x.get_internal_type() in ("DateTimeField", "DateField", "TimeField")
            ]

            for field in fields:
                column = field.column
                if isinstance(result, dict): # sometimes it's a key!
                    value = result.get(column)
                else:
                    value = None

                if value is not None:
                    result[column] = ensure_datetime(value)
            return result

        def ignore_excluded_pks(result):
            if result.key() in excluded_pks:
                return None
            return result

        self.results = wrap_result_with_functor(self.results, increment_returned_results)

        # If this is a keys only query, we need to generate a fake entity
        # for each key in the result set
        if self.keys_only:
            self.results = wrap_result_with_functor(self.results, convert_key_to_entity)

        self.results = wrap_result_with_functor(self.results, ignore_excluded_pks)
        self.results = wrap_result_with_functor(self.results, convert_datetime_fields)
        self.results = wrap_result_with_functor(self.results, rename_pk_field)
        self.results = wrap_result_with_functor(self.results, process_extra_selects)

        if self.query.distinct and self.query.extra_selects:
            # If we had extra selects, and we're distinct, we must deduplicate results
            def deduper_factory():
                seen = set()

                def dedupe(result):
                    # FIXME: This logic can't be right. I think we need to store the distinct fields
                    # somewhere on the query
                    if getattr(self.original_query, "annotation_select", None):
                        columns = self.original_query.annotation_select.keys()
                    else:
                        columns = self.query.columns or []
                    if not columns:
                        return result

                    key = tuple([ result[x] for x in self._exclude_pk(columns) if x in result ])
                    if key in seen:
                        return None
                    seen.add(key)
                    return result

                return dedupe

            self.results = wrap_result_with_functor(self.results, deduper_factory())

        if limit:
            self.results = limit_results_generator(self.results, limit - excluded_pk_count)


    def execute(self):
        self.gae_query = self._build_query()
        self._fetch_results(self.gae_query)

    def __unicode__(self):
        # TODO: should we print out the namespace in here too?
        try:
            qry = json.loads(self.query.serialize())

            result = u" ".join([
                qry["kind"],
                u", ".join(qry["columns"] if qry["projection_possible"] and qry["columns"] else ["*"]),
                u"FROM",
                qry["concrete_table"]
            ])

            if qry["where"]:
                result += u" " + u" ".join([
                    u"WHERE",
                    u" OR ".join([
                        u" AND ".join( [ u"{} {}".format(k, v) for k, v in x.iteritems() ])
                        for x in qry["where"]
                    ])
                ])
            return result
        except:
            # We never want this to cause things to die
            logging.exception("Unable to translate query to string")
            return "QUERY TRANSLATION ERROR"

    def __repr__(self):
        return self.__unicode__().encode("utf-8")

    def lower(self):
        """
            This exists solely for django-debug-toolbar compatibility.
        """
        return str(self).lower()


class FlushCommand(object):
    """
        sql_flush returns the SQL statements to flush the database,
        which are then executed by cursor.execute()

        We instead return a list of FlushCommands which are called by
        our cursor.execute
    """
    def __init__(self, table, connection):
        self.table = table
        self.namespace = connection.ops.connection.settings_dict.get("NAMESPACE")

    def execute(self):
        table = self.table
        query = datastore.Query(table, keys_only=True, namespace=self.namespace)
        while query.Count():
            datastore.Delete(query.Run())

        # Delete the markers we need to
        from djangae.db.constraints import UniqueMarker
        query = datastore.Query(UniqueMarker.kind(), keys_only=True, namespace=self.namespace)
        query["__key__ >="] = datastore.Key.from_path(UniqueMarker.kind(), self.table, namespace=self.namespace)
        query["__key__ <"] = datastore.Key.from_path(
            UniqueMarker.kind(), u"{}{}".format(self.table, u'\ufffd'), namespace=self.namespace
        )
        while query.Count():
            datastore.Delete(query.Run())

        # TODO: ideally we would only clear the cached objects for the table that was flushed, but
        # we have no way of doing that
        memcache.flush_all()
        caching.get_context().reset()


@db.non_transactional
def reserve_id(kind, id_or_name, namespace):
    from google.appengine.api.datastore import _GetConnection
    key = datastore.Key.from_path(kind, id_or_name, namespace=namespace)
    _GetConnection()._async_reserve_keys(None, [key])


class BulkInsertError(IntegrityError, NotSupportedError):
    pass


class InsertCommand(object):
    def __init__(self, connection, model, objs, fields, raw):
        self.has_pk = any(x.primary_key for x in fields)
        self.model = model
        self.objs = objs
        self.connection = connection
        self.namespace = connection.ops.connection.settings_dict.get("NAMESPACE")
        self.raw = raw
        self.fields = fields

        self.entities = []
        self.included_keys = []

        for obj in self.objs:
            if self.has_pk:
                # We must convert the PK value here, even though this normally happens in django_instance_to_entity otherwise
                # custom PK fields don't work properly
                value = self.model._meta.pk.get_db_prep_save(
                    self.model._meta.pk.pre_save(obj, True),
                    self.connection
                )
                self.included_keys.append(
                    get_datastore_key(self.model, value, self.namespace)
                    if value else None
                )

                if value == 0:
                    raise IntegrityError("The datastore doesn't support 0 as a key value")

                if not self.model._meta.pk.blank and self.included_keys[-1] is None:
                    raise IntegrityError("You must specify a primary key value for {} instances".format(self.model))
            else:
                # We zip() self.entities and self.included_keys in execute(), so they should be the same length
                self.included_keys.append(None)

            # We don't use the values returned, but this does make sure we're
            # doing the same validation as Django. See issue #493 for an
            # example of how not doing this can mess things up
            for field in fields:
                field.get_db_prep_save(
                    getattr(obj, field.attname) if raw else field.pre_save(obj, True),
                    connection=connection,
                )

            self.entities.append(
                django_instance_to_entity(self.connection, self.model, self.fields, self.raw, obj)
            )

    def execute(self):
        check_existence = self.has_pk and not has_concrete_parents(self.model)

        if not constraints.has_active_unique_constraints(self.model) and not check_existence:
            # Fast path, no constraint checks and no keys mean we can just do a normal datastore.Put
            # which isn't limited to 25
            results = datastore.Put(self.entities) # This modifies self.entities and sets their keys
            caching.add_entities_to_cache(
                self.model,
                self.entities,
                caching.CachingSituation.DATASTORE_GET_PUT,
                self.namespace,
                skip_memcache=True
            )
            return results

        def insert_chunk(keys, entities):
            # Note that this is limited to a maximum of 25 entities.
            markers = []
            @db.transactional(xg=len(entities) > 1)
            def txn():
                for key in keys:
                    if check_existence and key is not None:
                        if utils.key_exists(key):
                            raise IntegrityError("Tried to INSERT with existing key")

                        id_or_name = key.id_or_name()
                        if isinstance(id_or_name, basestring) and id_or_name.startswith("__"):
                            raise NotSupportedError("Datastore ids cannot start with __. Id was %s" % id_or_name)

                        # Notify App Engine of any keys we're specifying intentionally
                        reserve_id(key.kind(), key.id_or_name(), self.namespace)

                results = datastore.Put(entities)
                for entity in entities:
                    markers.extend(constraints.acquire(self.model, entity))

                caching.add_entities_to_cache(
                    self.model,
                    entities,
                    caching.CachingSituation.DATASTORE_GET_PUT,
                    self.namespace,
                    skip_memcache=True
                )

                return results

            try:
                return txn()
            except:
                # There are 3 possible reasons why we've ended up here:
                # 1. The datastore.Put() failed, but note that because it's a transaction, the
                #    exception isn't raised until the END of the transaction block.
                # 2. Some of the markers were acquired, but then we hit a unique constraint
                #    conflict and so the outer transaction was rolled back.
                # 3. Something else went wrong after we'd acquired markers, e.g. the
                #    caching.add_entities_to_cache call got hit by a metaphorical bus.
                # In any of these cases, we (may) have acquired markers via (a) nested, independent
                # transaction(s), and so we need to release them again.
                constraints.release_markers(markers)
                raise

        # We can't really support this and maintain expected behaviour. If we chunked the insert and one of the
        # chunks fails it will mean some of the data would be saved and rather than trying to communicate that back
        # to the user it's better that they chunk the data themselves as they can deal with the failure better
        if len(self.entities) > datastore_stub_util._MAX_EG_PER_TXN:
            raise BulkInsertError("Bulk inserts with unique constraints, or pre-defined keys are limited to {} instances on the datastore".format(
                datastore_stub_util._MAX_EG_PER_TXN
            ))

        return insert_chunk(self.included_keys, self.entities)

    def lower(self):
        """
            This exists solely for django-debug-toolbar compatibility.
        """
        return str(self).lower()

    def __unicode__(self):
        try:
            keys = self.entities[0].keys()
            result = u" ".join([
                u"INSERT INTO",
                self.entities[0].kind(),
                u"(" + u", ".join(keys) + u")",
                u"VALUES"
            ])

            for entity in self.entities:
                result += u"(" + u", ".join([unicode(entity[x]) for x in keys]) + u")"

            return result
        except:
            # We never want this to cause things to die
            logging.info("InsertCommand is unable to translate query to string")
            return u"QUERY TRANSLATION ERROR"

    def __repr__(self):
        return self.__unicode__().encode("utf-8")


class DeleteCommand(object):
    def __init__(self, connection, query):
        self.model = query.model
        self.select = SelectCommand(connection, query, keys_only=True)
        self.namespace = connection.ops.connection.settings_dict.get("NAMESPACE")
        self.table_to_delete = query.tables[0]

    def execute(self):
        """
            Ideally we'd just be able to tell appengine to delete all the entities
            which match the query, that would be nice wouldn't it?

            Except we can't. Firstly Delete() only accepts keys so we first have to
            execute a keys_only query to find the entities that match the query, then send
            those keys to Delete(), except it's not as easy as that either because the
            query might be eventually consistent and so we might delete entities which
            were updated in another request and no-longer match the query. Bugger.

            And then there might be constraints... in which case we need to grab the entity
            in its entirety, release any constraints and then delete the entity.

            And then there are polymodels (model inheritence) which means we might not even be
            deleting the entity after all, only deleting some of the fields from it.

            What we do then is do a keys_only query, then iterate the entities in batches of
            25 (well _MAX_EG_PER_TXN), each entity in the batch has its polymodel fields wiped out
            (if necessary) and then we do either a PutAsync or DeleteAsync all inside a transaction.

            Oh, and we wipe out memcache and delete the constraints in an independent transaction.

            Things to improve:

             - Delete the constraints in a background thread. We don't need to wait for them, and really,
             we don't want the non-deletion of them to affect the deletion of the entity. Lingering markers
             are handled automatically they just case a small performance hit on write.
             - Check the entity matches the query still (there's a fixme there)
        """

        self.select.execute()

        constraints_enabled = constraints.has_active_unique_constraints(self.model)
        keys = [ x.key() for x in self.select.results ]

        def wipe_polymodel_from_entity(entity, db_table):
            """
                Wipes out the fields associated with the specified polymodel table
            """
            polymodel_value = entity.get('class', [])
            if polymodel_value and self.table_to_delete in polymodel_value:
                # Remove any local fields from this model from the entity
                model = utils.get_model_from_db_table(self.table_to_delete)
                for field in model._meta.local_fields:
                    col = field.column
                    if col in entity:
                        del entity[col]

                # Then remove this model from the polymodel heirarchy
                polymodel_value.remove(self.table_to_delete)
                if polymodel_value:
                    entity['class'] = polymodel_value

        @db.transactional(xg=True)
        def delete_batch(key_slice):
            entities = datastore.Get(key_slice)

            #FIXME: We need to make sure the entity still matches the query!
#            entities = (x for x in entities if utils.entity_matches_query(x, self.select.gae_query))

            to_delete = []
            to_update = []
            updated_keys = []

            # Go through the entities
            for entity in entities:
                if entity is None:
                    continue

                wipe_polymodel_from_entity(entity, self.table_to_delete)
                if not entity.get('class'):
                    to_delete.append(entity)
                    constraints.release(self.model, entity)
                else:
                    to_update.append(entity)
                updated_keys.append(entity.key())

            datastore.DeleteAsync([x.key() for x in to_delete])
            datastore.PutAsync(to_update)

            caching.remove_entities_from_cache_by_key(
                updated_keys, self.namespace
            )

            return len(updated_keys)

        deleted = 0
        while keys:
            deleted += delete_batch(keys[:datastore_stub_util._MAX_EG_PER_TXN])
            keys = keys[datastore_stub_util._MAX_EG_PER_TXN:]

        return deleted


    def lower(self):
        """
            This exists solely for django-debug-toolbar compatibility.
        """
        return str(self).lower()


class UpdateCommand(object):
    def __init__(self, connection, query):
        self.model = query.model
        self.select = SelectCommand(connection, query, keys_only=True)
        self.values = query.values
        self.connection = connection
        self.namespace = connection.ops.connection.settings_dict.get("NAMESPACE")

    def lower(self):
        """
            This exists solely for django-debug-toolbar compatibility.
        """
        return str(self).lower()

    def _update_entity(self, key):
        markers_to_acquire = []
        markers_to_release = []

        # This is a list rather than a straight bool, because we need to pass
        # by reference so we can set it in the nested function. 'global' doesnt
        # work on nested functions
        rollback_markers = [False]

        @db.transactional
        def txn():
            caching.remove_entities_from_cache_by_key([key], self.namespace)

            try:
                result = datastore.Get(key)
            except datastore_errors.EntityNotFoundError:
                # Return false to indicate update failure
                return False

            if (
                isinstance(self.select.gae_query, (Query, UniqueQuery)) # ignore QueryByKeys and NoOpQuery
                and not utils.entity_matches_query(result, self.select.gae_query)
            ):
                # Due to eventual consistency they query may have returned an entity which no longer
                # matches the query
                return False

            original = copy.deepcopy(result)

            instance_kwargs = {field.attname:value for field, param, value in self.values}

            # Note: If you replace MockInstance with self.model, you'll find that some delete
            # tests fail in the test app. This is because any unspecified fields would then call
            # get_default (even though we aren't going to use them) which may run a query which
            # fails inside this transaction. Given as we are just using MockInstance so that we can
            # call django_instance_to_entity it on it with the subset of fields we pass in,
            # what we have is fine.
            meta = self.model._meta
            instance = MockInstance(
                _original=MockInstance(_meta=meta, **result),
                _meta=meta,
                **instance_kwargs
            )

            # We need to add to the class attribute, rather than replace it!
            original_class = result.get(POLYMODEL_CLASS_ATTRIBUTE, [])

            # Update the entity we read above with the new values
            result.update(django_instance_to_entity(
                self.connection, self.model,
                [ x[0] for x in self.values],  # Pass in the fields that were updated
                True, instance)
            )

            # Make sure we keep all classes in the inheritence tree!
            if original_class:
                if result[POLYMODEL_CLASS_ATTRIBUTE] is not None:
                    result[POLYMODEL_CLASS_ATTRIBUTE].extend(original_class)
                    # Make sure we don't add duplicates
                else:
                    result[POLYMODEL_CLASS_ATTRIBUTE] = original_class

            if POLYMODEL_CLASS_ATTRIBUTE in result:
                result[POLYMODEL_CLASS_ATTRIBUTE] = list(set(result[POLYMODEL_CLASS_ATTRIBUTE]))

            if not constraints.has_active_unique_constraints(self.model):
                # The fast path, no constraint checking
                datastore.Put(result)
                caching.add_entities_to_cache(
                    self.model,
                    [result],
                    caching.CachingSituation.DATASTORE_PUT,
                    self.namespace,
                    skip_memcache=True,
                )
            else:
                markers_to_acquire[:], markers_to_release[:] = constraints.get_markers_for_update(
                    self.model, original, result
                )
                datastore.Put(result)

                constraints.update_identifiers(markers_to_acquire, markers_to_release, result.key())

                # If the datastore.Put() fails then the exception will only be raised when the
                # transaction applies, which means that we will still get to here and will still have
                # applied the marker changes (because they're in a nested, independent transaction).
                # Hence we set this flag to tell us that we got this far and that we should roll them back.
                rollback_markers[0] = True
                # If something dies between here and the `return` statement then we'll have stale unique markers

                try:
                    # Update the cache before dealing with unique markers, as CachingSituation.DATASTORE_PUT
                    # will only update the context cache
                    caching.add_entities_to_cache(
                        self.model,
                        [result],
                        caching.CachingSituation.DATASTORE_PUT,
                        self.namespace,
                        skip_memcache=True,
                    )
                except:
                    # We ignore the exception because raising will rollback the transaction causing
                    # an inconsistent state
                    logging.exception("Unable to update the context cache")
                    pass

            # Return true to indicate update success
            return True

        try:
            return txn()
        except:
            if rollback_markers[0]:
                constraints.update_identifiers(markers_to_release, markers_to_acquire, key)
            raise

    def execute(self):
        self.select.execute()

        i = 0
        for result in self.select.results:
            if self._update_entity(result.key()):
                # Only increment the count if we successfully updated
                i += 1

        return i
