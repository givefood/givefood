import django
import json
import logging
import re
import datetime

from itertools import chain, imap
from django.core.exceptions import FieldError
from django.db.models.fields import FieldDoesNotExist
from django.db.models.sql.datastructures import EmptyResultSet

from django.db.models import AutoField

from django.db.models.query import QuerySet

try:
    from django.db.models.query import FlatValuesListIterable
except ImportError:
    # Django < 1.8
    class FlatValuesListIterable(object):
        pass

try:
    from django.db.models.query import ValuesListQuerySet
except ImportError:
    # Django >= 1.9
    class ValuesListQuerySet(object):
        pass

from django.db.models.expressions import Star

from django.db import NotSupportedError
from djangae.db.backends.appengine.indexing import (
    REQUIRES_SPECIAL_INDEXES,
    add_special_index,
)

from djangae import environment
from djangae.db.backends.appengine import POLYMODEL_CLASS_ATTRIBUTE
from djangae.db.utils import (
    get_top_concrete_parent,
    has_concrete_parents,
    get_field_from_column,
    ensure_datetime,
)

from google.appengine.api import datastore


DJANGAE_LOG = logging.getLogger("djangae")


VALID_QUERY_KINDS = (
    "SELECT",
    "UPDATE",
    "INSERT",
    "DELETE",
    "COUNT",
    "AVERAGE"
)

VALID_ANNOTATIONS = {
    "MIN": min,
    "MAX": max,
    "SUM": sum,
    "COUNT": len,
    "AVG": lambda x: (sum(x) / len(x))
}

VALID_CONNECTORS = (
    'AND', 'OR'
)


VALID_OPERATORS = (
    '=', '<', '>', '<=', '>=', 'IN'
)

def convert_operator(operator):
    if operator == 'exact':
        return '='
    elif operator == 'gt':
        return '>'
    elif operator == 'lt':
        return '<'
    elif operator == 'gte':
        return '>='
    elif operator == 'lte':
        return '<='

    return operator.upper()

class WhereNode(object):
    def __init__(self):
        self.column = None
        self.operator = None
        self.value = None
        self.output_field = None
        self.will_never_return_results = False

        self.children = []
        self.connector = 'AND'
        self.negated = False

    @property
    def is_leaf(self):
        return bool(self.column and self.operator)

    def set_connector(self, connector):
        self.connector = connector

    def append_child(self, node):
        self.children.append(node)

    def set_leaf(self, column, operator, value, is_pk_field, negated, namespace, target_field=None):
        assert column
        assert operator
        assert isinstance(is_pk_field, bool)
        assert isinstance(negated, bool)

        if operator == "iexact" and isinstance(target_field, AutoField):
            # When new instance is created, automatic primary key 'id' does not generate '_idx_iexact_id'.
            # As the primary key 'id' (AutoField) is integer and is always case insensitive,
            # we can deal with 'id_iexact=' query by using 'exact' rather than 'iexact'.
            operator = "exact"
            value = int(value)

        if is_pk_field:
            # If this is a primary key, we need to make sure that the value
            # we pass to the query is a datastore Key. We have to deal with IN queries here
            # because they aren't flattened until the DNF stage
            model = get_top_concrete_parent(target_field.model)
            table = model._meta.db_table

            if isinstance(value, (list, tuple)):
                value = [
                    datastore.Key.from_path(table, x, namespace=namespace)
                    for x in value if x
                ]
            else:
                if (operator == "isnull" and value is True) or not value:
                    # id=None will never return anything and
                    # Empty strings and 0 are forbidden as keys
                    self.will_never_return_results = True
                else:
                    value = datastore.Key.from_path(table, value, namespace=namespace)
            column = "__key__"

        # Do any special index conversions necessary to perform this lookup
        primary_operation = operator.split("__")[0]
        special_indexer = REQUIRES_SPECIAL_INDEXES.get(primary_operation)

        if special_indexer:
            if is_pk_field:
                column = model._meta.pk.column
                value = unicode(value.id_or_name())

            add_special_index(target_field.model, column, primary_operation, value)
            index_type = special_indexer.prepare_index_type(operator, value)
            value = special_indexer.prep_value_for_query(value)
            column = special_indexer.indexed_column_name(column, value, index_type)
            operator = special_indexer.prep_query_operator(operator)

        self.column = column
        self.operator = convert_operator(operator)
        self.value = value



    def __iter__(self):
        for child in chain(*imap(iter, self.children)):
            yield child
        yield self


    def __repr__(self):
        if self.is_leaf:
            return "[%s%s%s]" % (self.column, self.operator, self.value)
        else:
            return "(%s:%s%s)" % (self.connector, "!" if self.negated else "", ",".join([repr(x) for x in self.children]))

    def __eq__(self, rhs):
        if self.is_leaf != rhs.is_leaf:
            return False

        if self.is_leaf:
            return self.column == rhs.column and self.value == rhs.value and self.operator == rhs.operator
        else:
            return self.connector == rhs.connector and self.children == rhs.children

    def __hash__(self):
        if self.is_leaf:
            return hash((self.column, self.value, self.operator))
        else:
            return hash((self.connector,) + tuple([hash(x) for x in self.children]))

class Query(object):
    def __init__(self, model, kind):
        assert kind in VALID_QUERY_KINDS

        self.model = model
        self.concrete_model = get_top_concrete_parent(model)
        self.kind = kind

        self.projection_possible = True
        self.tables = []

        self.columns = None # None means all fields
        self.init_list = []

        self.distinct = False
        self.order_by = []
        self.row_data = [] # For insert/updates
        self._where = None
        self.low_mark = self.high_mark = None

        self.annotations = []
        self.per_entity_annotations = []
        self.extra_selects = []
        self.polymodel_filter_added = False

        # A list of PKs that should be excluded from the resultset
        self.excluded_pks = set()

    @property
    def is_normalized(self):
        """
            Returns True if this query has a normalized where tree
        """
        if not self.where:
            return True

        # Only a leaf node, return True
        if not self.where.is_leaf:
            return True

        # If we have children, and they are all leaf nodes then this is a normalized
        # query
        return self.where.connector == 'OR' and self.where.children and all(x.is_leaf for x in self.where.children)

    def add_extra_select(self, column, lookup):
        if lookup.lower().startswith("select "):
            raise ValueError("SQL statements aren't supported with extra(select=)")

        # Boolean expression test
        bool_expr = "(?P<lhs>[a-zA-Z0-9_]+)\s?(?P<op>[=|>|<]{1,2})\s?(?P<rhs>[\w+|\']+)"

        # Operator expression test
        op_expr = "(?P<lhs>[a-zA-Z0-9_]+)\s?(?P<op>[+|-|/|*])\s?(?P<rhs>[\w+|\']+)"

        OP_LOOKUP = {
            "=": lambda x, y: x == y,
            "is": lambda x, y: x == y,
            "<": lambda x, y: x < y,
            ">": lambda x, y: x > y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "+": lambda x, y: x + y,
            "-": lambda x, y: x - y,
            "/": lambda x, y: x / y,
            "*": lambda x, y: x * y
        }

        for regex in (bool_expr, op_expr):
            match = re.match(regex, lookup)
            if match:
                lhs = match.group('lhs')
                rhs = match.group('rhs')
                op = match.group('op').lower()
                if op in OP_LOOKUP:
                    self.extra_selects.append((column, (OP_LOOKUP[op], (lhs, rhs))))
                else:
                    raise ValueError("Unsupported operator")
                return

        # Assume literal
        self.extra_selects.append((column, (lambda x: x, [lookup])))

    def add_source_table(self, table):
        if table in self.tables:
            return

        self.tables.append(table)

    def set_distinct(self, distinct_fields):
        self.distinct = True
        if distinct_fields:
            for field in distinct_fields:
                self.add_projected_column(field)
        elif not self.columns:
            for field in self.model._meta.fields:
                self.add_projected_column(field.column)

    def add_order_by(self, column):
        self.order_by.append(column)

    def add_annotation(self, column, annotation):
        name = annotation.__class__.__name__
        if name == "Count":
            return # Handled elsewhere

        if name not in ("Col", "Date", "DateTime"):
            raise NotSupportedError("Unsupported annotation %s" % name)

        def process_date(value, lookup_type):
            value = ensure_datetime(value)
            ret = datetime.datetime.fromtimestamp(0)

            POSSIBLE_LOOKUPS = ("year", "month", "day", "hour", "minute", "second")

            ret = ret.replace(
                value.year,
                value.month if lookup_type in POSSIBLE_LOOKUPS[1:] else ret.month,
                value.day if lookup_type in POSSIBLE_LOOKUPS[2:] else ret.day,
                value.hour if lookup_type in POSSIBLE_LOOKUPS[3:] else ret.hour,
                value.minute if lookup_type in POSSIBLE_LOOKUPS[4:] else ret.minute,
                value.second if lookup_type in POSSIBLE_LOOKUPS[5:] else ret.second,
            )

            return ret

        # Abuse the extra_select functionality
        if name == "Col":
            self.extra_selects.append((column, (lambda x: x, [column])))
        elif name in ("Date", "DateTime"):
            self.extra_selects.append(
                (column,
                (lambda x: process_date(x, annotation.lookup_type), [getattr(annotation, "lookup", column)]))
            )
            # Override the projection so that we only get this column
            self.columns = set([ getattr(annotation, "lookup", column) ])


    def add_projected_column(self, column):
        self.init_list.append(column)

        if not self.projection_possible:
            # If we previously tried to add a column that couldn't be
            # projected, we don't try and add any more
            return

        field = get_field_from_column(self.model, column)

        if field is None:
            raise NotSupportedError("{} is not a valid column for the queried model. Did you try to join?".format(column))

        if field.db_type(self.connection) in ("bytes", "text", "list", "set"):
            DJANGAE_LOG.warn("Disabling projection query as %s is an unprojectable type", column)
            self.columns = None
            self.projection_possible = False
            return

        if not self.columns:
            self.columns = set([ column ])
        else:
            self.columns.add(column)

    def add_row(self, data):
        assert self.columns
        assert len(data) == len(self.columns)

        self.row_data.append(data)

    def prepare(self):
        if not self.init_list:
            self.init_list = [ x.column for x in self.model._meta.fields ]

        self._remove_impossible_branches()
        self._remove_erroneous_isnull()
        self._remove_negated_empty_in()
        self._add_inheritence_filter()
        self._populate_excluded_pks()
        self._disable_projection_if_fields_used_in_equality_filter()
        self._check_only_single_inequality_filter()

    @property
    def where(self):
        return self._where

    @where.setter
    def where(self, where):
        assert where is None or isinstance(where, WhereNode)

        self._where = where

    def _populate_excluded_pks(self):
        if not self._where:
            return

        self.excluded_pks = set()
        def walk(node, negated):
            if node.connector == "OR":
                # We can only process AND nodes, if we hit an OR we can't
                # use the excluded PK optimization
                return

            if node.negated:
                negated = not negated

            for child in node.children[:]:
                # As more than one inequality filter is not allowed on the datastore
                # this leaf + count check is probably pointless, but at least if you
                # do try to exclude two things it will blow up in the right place and not
                # return incorrect results
                if child.is_leaf and len(node.children) == 1:
                    if negated and child.operator == "=" and child.column == "__key__":
                        self.excluded_pks.add(child.value)
                        node.children.remove(child)
                    elif negated and child.operator == "IN" and child.column == "__key__":
                        [ self.excluded_pks.add(x) for x in child.value ]
                        node.children.remove(child)
                else:
                    walk(child, negated)

            node.children = [ x for x in node.children if x.children or x.column ]

        walk(self._where, False)

        if not self._where.children:
            self._where = None

    def _remove_negated_empty_in(self):
        """
            An empty exclude(id__in=[]) is pointless, but can cause trouble
            during denormalization. We remove such nodes here.
        """
        if not self._where:
            return

        def walk(node, negated):
            if node.negated:
                negated = node.negated

            for child in node.children[:]:
                if negated and child.operator == "IN" and not child.value:
                    node.children.remove(child)

                walk(child, negated)

            node.children = [ x for x in node.children if x.children or x.column ]

        had_where = bool(self._where.children)
        walk(self._where, False)

        # Reset the where if that was the only filter
        if had_where and not bool(self._where.children):
            self._where = None

    def _remove_erroneous_isnull(self):
        # This is a little crazy, but bear with me...
        # If you run a query like this:  filter(thing=1).exclude(field1="test") where field1 is
        # null-able you'll end up with a negated branch in the where tree which is:

        #           AND (negated)
        #          /            \
        #   field1="test"   field1__isnull=False

        # This is because on SQL, field1 != "test" won't give back rows where field1 is null, so
        # django has to include the negated isnull=False as well in order to get back the null rows
        # as well.  On App Engine though None is just a value, not the lack of a value, so it's
        # enough to just have the first branch in the negated node and in fact, if you try to use
        # the above tree, it will result in looking for:
        #  field1 < "test" and field1 > "test" and field1__isnull=True
        # which returns the wrong result (it'll return when field1 == None only)

        def walk(node, negated):
            if node.negated:
                negated = not negated

            if not node.is_leaf:
                equality_fields = set()
                negated_isnull_fields = set()
                isnull_lookup = {}

                for child in node.children[:]:
                    if negated:
                        if child.operator == "=":
                            equality_fields.add(child.column)
                            if child.column in negated_isnull_fields:
                                node.children.remove(isnull_lookup[child.column])

                        elif child.operator == "ISNULL":
                            negated_isnull_fields.add(child.column)
                            if child.column in equality_fields:
                                node.children.remove(child)
                            else:
                                isnull_lookup[child.column] = child

                    walk(child, negated)
        if self.where:
            walk(self._where, False)

    def _remove_impossible_branches(self):
        """
            If we mark a child node as never returning results we either need to
            remove those nodes, or remove the branches of the tree they are on depending
            on the connector of the parent node.
        """
        if not self._where:
            return

        def walk(node, negated):
            if node.negated:
                negated = not negated

            for child in node.children[:]:
                walk(child, negated)

                if child.will_never_return_results:
                    if node.connector == 'AND':
                        if child.negated:
                            node.children.remove(child)
                        else:
                            node.will_never_return_results = True
                    else:
                        #OR
                        if not child.negated:
                            node.children.remove(child)
                            if not node.children:
                                node.will_never_return_results = True
                        else:
                            node.children[:] = []

        walk(self._where, False)

        if self._where.will_never_return_results:
            # We removed all the children of the root where node, so no results
            raise EmptyResultSet()

    def _check_only_single_inequality_filter(self):
        inequality_fields = set()
        def walk(node, negated):
            if node.negated:
                negated = not negated

            for child in node.children[:]:
                if (negated and child.operator == "=") or child.operator in (">", "<", ">=", "<="):
                    inequality_fields.add(child.column)
                walk(child, negated)

            if len(inequality_fields) > 1:
                raise NotSupportedError(
                    "You can only have one inequality filter per query on the datastore. "
                    "Filters were: %s" % ' '.join(inequality_fields)
                )

        if self.where:
            walk(self._where, False)

    def _disable_projection_if_fields_used_in_equality_filter(self):
        if not self._where or not self.columns:
            return

        equality_columns = set()

        def walk(node):
            if not node.is_leaf:
                for child in node.children:
                    walk(child)
            elif node.operator == "=" or node.operator == "IN":
                equality_columns.add(node.column)

        walk(self._where)

        if equality_columns and equality_columns.intersection(self.columns):
            self.columns = None
            self.projection_possible = False

    def _add_inheritence_filter(self):
        """
            We support inheritence with polymodels. Whenever we set
            the 'where' on this query, we manipulate the tree so that
            the lookups are ANDed with a filter on 'class = db_table'
            and on inserts, we add the 'class' column if the model is part
            of an inheritance tree.

            We only do any of this if the model has concrete parents and isn't
            a proxy model
        """
        if has_concrete_parents(self.model) and not self.model._meta.proxy:
            if self.polymodel_filter_added:
                return

            new_filter = WhereNode()
            new_filter.column = POLYMODEL_CLASS_ATTRIBUTE
            new_filter.operator = '='
            new_filter.value = self.model._meta.db_table

            # We add this bare AND just to stay consistent with what Django does
            new_and = WhereNode()
            new_and.connector = 'AND'
            new_and.children = [ new_filter ]

            new_root = WhereNode()
            new_root.connector = 'AND'
            new_root.children = [ new_and ]
            if self._where:
                # Add the original where if there was one
                new_root.children.append(self._where)
            self._where = new_root

            self.polymodel_filter_added = True

    def serialize(self):
        """
            The idea behind this function is to provide a way to serialize this
            query to a string which can be compared to another query. Pickle won't
            work as some of the values etc. might not be picklable.

            FIXME: This function is incomplete! Not all necessary members are serialized
        """
        if not self.is_normalized:
            raise ValueError("You cannot serialize queries unless they are normalized")

        result = {}
        result["kind"] = self.kind
        result["table"] = self.model._meta.db_table
        result["concrete_table"] = self.concrete_model._meta.db_table
        result["columns"] = list(self.columns or []) # set() is not JSONifiable
        result["projection_possible"] = self.projection_possible
        result["init_list"] = self.init_list
        result["distinct"] = self.distinct
        result["order_by"] = self.order_by
        result["low_mark"] = self.low_mark
        result["high_mark"] = self.high_mark
        result["excluded_pks"] = map(str, self.excluded_pks)

        where = []

        if self.where:
            assert self.where.connector == 'OR'
            for node in self.where.children:
                assert node.connector == 'AND'

                query = {}
                for lookup in node.children:
                    query[''.join([lookup.column, lookup.operator])] = unicode(lookup.value)

                where.append(query)

        result["where"] = where

        return json.dumps(result)


INVALID_ORDERING_FIELD_MESSAGE = (
    "Ordering on TextField or BinaryField is not supported on the datastore. "
    "You might consider using a ComputedCharField which stores the first "
    "_MAX_STRING_LENGTH (from google.appengine.api.datastore_types) bytes of the "
    "field and instead order on that."
)


def _extract_ordering_from_query_18(query):
    from djangae.db.backends.appengine.commands import log_once
    from django.db.models.expressions import OrderBy, F

    # Add any orderings
    if not query.default_ordering:
        result = list(query.order_by)
    else:
        result = list(query.order_by or query.get_meta().ordering or [])

    if query.extra_order_by:
        result = list(query.extra_order_by)

        # we need some extra logic to handle dot seperated ordering
        new_result = []
        cross_table_ordering = set()
        for ordering in result:
            if "." in ordering:
                dot_based_ordering = ordering.split(".")
                if dot_based_ordering[0] == query.model._meta.db_table:
                    ordering = dot_based_ordering[1]
                elif dot_based_ordering[0].lstrip('-') == query.model._meta.db_table:
                    ordering = '-{}'.format(dot_based_ordering[1])
                else:
                    cross_table_ordering.add(ordering)
                    continue # we don't want to add this ordering value
            new_result.append(ordering)

        if len(cross_table_ordering):
            log_once(
                DJANGAE_LOG.warning if environment.is_development_environment() else DJANGAE_LOG.debug,
                "The following orderings were ignored as cross-table orderings are not supported on the datastore: %s", cross_table_ordering
            )

        result = new_result

    final = []

    opts = query.model._meta

    # Apparently expression ordering is absolute and so shouldn't be flipped
    # if the standard_ordering is False. This keeps track of which columns
    # were expressions and so don't need flipping
    expressions = set()

    for col in result:
        if isinstance(col, OrderBy):
            descending = col.descending
            col = col.expression.name
            if descending:
                col = "-" + col
            expressions.add(col)

        elif isinstance(col, F):
            col = col.name

        if isinstance(col, (int, long)):
            # If you do a Dates query, the ordering is set to [1] or [-1]... which is weird
            # I think it's to select the column number but then there is only 1 column so
            # unless the ordinal is one-based I have no idea. So basically if it's an integer
            # subtract 1 from the absolute value and look up in the select for the column (guessing)
            idx = abs(col) - 1
            try:
                field_name = query.select[idx].col.col[-1]
                field = query.model._meta.get_field(field_name)
                final.append("-" + field.column if col < 0 else field.column)
            except IndexError:
                raise NotSupportedError("Unsupported order_by %s" % col)
        elif col.lstrip("-") == "pk":
            pk_col = "__key__"
            final.append("-" + pk_col if col.startswith("-") else pk_col)
        elif col == "?":
            raise NotSupportedError("Random ordering is not supported on the datastore")
        elif col.lstrip("-").startswith("__") and col.endswith("__"):
            # Allow stuff like __scatter__
            final.append(col)
        elif "__" in col:
            continue
        else:
            try:
                column = col.lstrip("-")

                # This is really 1.8 only, but I didn't want to duplicate this function
                # just for this. Suggestions for doing this more cleanly welcome!
                if column in getattr(query, "annotation_select", {}):
                    # It's an annotation, if it's a supported one, return the
                    # original column
                    annotation = query.annotation_select[column]
                    name = annotation.__class__.__name__

                    # We only support a few expressions
                    if name not in ("Col", "Date", "DateTime"):
                        raise NotSupportedError("Tried to order by unsupported expression")
                    else:
                        # Retrieve the original column and use that for ordering
                        if name == "Col":
                            column = annotation.output_field.column
                        else:
                            column = annotation.col.output_field.column

                field = query.model._meta.get_field(column)

                if field.get_internal_type() in (u"TextField", u"BinaryField"):
                    raise NotSupportedError(INVALID_ORDERING_FIELD_MESSAGE)

                # If someone orders by 'fk' rather than 'fk_id' this complains as that should take
                # into account the related model ordering. Note the difference between field.name == column
                # and field.attname (X_id)
                if field.related_model and field.name == column and field.related_model._meta.ordering:
                    raise NotSupportedError("Related ordering is not supported on the datastore")

                column = "__key__" if field.primary_key else field.column
                final.append("-" + column if col.startswith("-") else column)
            except FieldDoesNotExist:
                if col in query.extra_select:
                    # If the column is in the extra select we transform to the original
                    # column
                    try:
                        field = opts.get_field(query.extra_select[col][0])
                        column = "__key__" if field.primary_key else field.column
                        final.append("-" + column if col.startswith("-") else column)
                        continue
                    except FieldDoesNotExist:
                        # Just pass through to the exception below
                        pass

                available = opts.get_all_field_names()
                raise FieldError("Cannot resolve keyword %r into field. "
                    "Choices are: %s" % (col, ", ".join(available))
                )

    # Reverse if not using standard ordering
    def swap(col):
        if col.startswith("-"):
            return col.lstrip("-")
        else:
            return "-{}".format(col)

    if not query.standard_ordering:
        final = [ x if x in expressions else swap(x) for x in final ]

    if len(final) != len(result):
        diff = set(result) - set(final)
        log_once(
            DJANGAE_LOG.warning if environment.is_development_environment() else DJANGAE_LOG.debug,
            "The following orderings were ignored as cross-table and random orderings are not supported on the datastore: %s", diff
        )

    return final


def _extract_projected_columns_from_query_18(query):
    result = []

    if query.select:
        for x in query.select:
            column = x.target.column
            result.append(column)
        return result
    else:
        # If the query uses defer()/only() then we need to process deferred. We have to get all deferred columns
        # for all (concrete) inherited models and then only include columns if they appear in that list
        only_load = query.get_loaded_field_names()
        if only_load:
            for field, model in query.model._meta.get_concrete_fields_with_model():
                model = model or query.model
                try:
                    if field.column in only_load[model]:
                        # Add a field that has been explicitly included
                        result.append(field.column)
                except KeyError:
                    # Model wasn't explicitly listed in the only_load table
                    # Therefore, we need to load all fields from this model
                    result.append(field.column)
            return result
        else:
            return []


def _walk_django_where(query, trunk_callback, leaf_callback, **kwargs):
    """
        Walks through a Django where tree. If a leaf node is encountered
        the leaf_callback is called, otherwise the trunk_callback is called
    """

    def walk_node(node, **kwargs):
        negated = kwargs["negated"]

        if node.negated:
            negated = not negated

        for child in node.children:
            new_kwargs = kwargs.copy()
            new_kwargs["negated"] = negated
            if not getattr(child, "children", []):
                leaf_callback(child, **new_kwargs)
            else:
                new_parent = trunk_callback(child, **new_kwargs)

                if new_parent:
                    new_kwargs["new_parent"] = new_parent

                walk_node(child, **new_kwargs)

    kwargs.setdefault("negated", False)
    walk_node(query.where, **kwargs)

def _django_18_query_walk_leaf(node, negated, new_parent, connection, model):
    new_node = WhereNode()

    if not hasattr(node, "lhs"):
        raise NotSupportedError("Attempted probable subquery, these aren't supported on the datastore")

    # Leaf
    if hasattr(node.lhs, 'target'):
        # from Django 1.9, some node.lhs might not have a target attribute
        # as they might be wrapping date fields
        field = node.lhs.target
        operator = node.lookup_name
    else:
        field = node.lhs.lhs.target
        operator = node.lhs.lookup_name

        # This deals with things like datefield__month__gt=X which means from this point
        # on, operator will have two parts in that particular case and will probably need to
        # be dealt with by a special indexer
        if node.lookup_name != operator:
            operator = "{}__{}".format(operator, node.lookup_name)

    if get_top_concrete_parent(field.model) != get_top_concrete_parent(model):
        raise NotSupportedError("Cross-join where filters are not supported on the datastore")

    # Make sure we don't let people try to filter on a text field, otherwise they just won't
    # get any results!

    if field.db_type(connection) in ("bytes", "text"):
        raise NotSupportedError("You can't filter on text or blob fields on the datastore")

    if operator == "isnull" and field.model._meta.parents.values():
        raise NotSupportedError("isnull lookups on inherited relations aren't supported on the datastore")

    lhs = field.column

    try:
        if hasattr(node.rhs, "get_compiler"):
            # This is a subquery
            raise NotSupportedError("Attempted to run a subquery on the datastore")
        elif isinstance(node.rhs, ValuesListQuerySet):
            # We explicitly handle ValuesListQuerySet because of the
            # common case of pk__in=Something.objects.values_list("pk", flat=True)
            # this WILL execute another query, but that is to be expected on a
            # non-relational datastore.

            node.rhs = [ x for x in node.rhs ] # Evaluate the queryset
            rhs = node.process_rhs(None, connection) # Process the RHS as if it was a list

        elif isinstance(node.rhs, QuerySet):
            # In Django 1.9, ValuesListQuerySet doesn't exist anymore, and instead
            # values_list returns a QuerySet
            if node.rhs._iterable_class == FlatValuesListIterable:
                # if the queryset has FlatValuesListIterable as iterable class
                # then it's a flat list, and we just need to evaluate the
                # queryset converting it into a list
                node.rhs = [ x for x in node.rhs ]
            else:
                # otherwise, we try to get the PK from the queryset
                node.rhs = [ x.pk for x in node.rhs ]

            rhs = node.process_rhs(None, connection) # Process the RHS as if it was a list

        else:
            rhs = node.process_rhs(None, connection)
    except EmptyResultSet:
        if operator == 'in':
            # Deal with this later
            rhs = [ [] ]
        else:
            raise


    if operator in ('in', 'range'):
        rhs = rhs[-1]
    elif operator == 'isnull':
        rhs = node.rhs
    else:
        rhs = rhs[-1][0]

    new_node.set_leaf(
        lhs,
        operator,
        rhs,
        is_pk_field=field==model._meta.pk,
        negated=negated,
        namespace=connection.ops.connection.settings_dict.get("NAMESPACE"),
        target_field=field,
    )

    # For some reason, this test:
    # test_update_with_related_manager (get_or_create.tests.UpdateOrCreateTests)
    # ends up with duplicate nodes in the where tree. I don't know why. But this
    # weirdly causes the datastore query to return nothing.
    # so here we don't add duplicate nodes, I can't think of a case where that would
    # change the query if it's under the same parent.
    if new_node in new_parent.children:
        return

    new_parent.children.append(new_node)

def _django_18_query_walk_trunk(node, negated, new_parent, **kwargs):
    new_node = WhereNode()
    new_node.connector = node.connector
    new_node.negated = node.negated

    new_parent.children.append(new_node)

    return new_node


def _transform_query_18(connection, kind, query):
    from django.db.models.sql.where import EmptyWhere
    if isinstance(query.where, EmptyWhere):
        # Empty where means return nothing!
        raise EmptyResultSet()

    ret = Query(query.model, kind)
    ret.connection = connection

    # Add the root concrete table as the source table
    root_table = get_top_concrete_parent(query.model)._meta.db_table
    ret.add_source_table(root_table)

    # Extract the ordering of the query results
    for order_col in _extract_ordering_from_query_18(query):
        ret.add_order_by(order_col)

    # Extract any projected columns (values/values_list/only/defer)
    for projected_col in _extract_projected_columns_from_query_18(query):
        ret.add_projected_column(projected_col)

    # Add any extra selects
    for col, select in query.extra_select.items():
        ret.add_extra_select(col, select[0])

    if query.distinct:
        # This must happen after extracting projected cols
        ret.set_distinct(list(query.distinct_fields))

    # Process annotations!
    if query.annotation_select:
        for k, v in query.annotation_select.items():
            ret.add_annotation(k, v)

    # Extract any query offsets and limits
    ret.low_mark = query.low_mark
    ret.high_mark = query.high_mark

    output = WhereNode()
    output.connector = query.where.connector

    _walk_django_where(
        query,
        _django_18_query_walk_trunk,
        _django_18_query_walk_leaf,
        new_parent=output,
        connection=connection,
        negated=query.where.negated,
        model=query.model
    )

    # If there no child nodes, just wipe out the where
    if not output.children:
        output = None

    ret.where = output

    return ret


def _transform_query_19(connection, kind, query):
    from django.db.models.sql.where import NothingNode, WhereNode as DjangoWhereNode

    # It could either be a NothingNode, or a WhereNode(AND NothingNode)
    if (
            isinstance(query.where, NothingNode) or (
            isinstance(query.where, DjangoWhereNode) and
            len(query.where.children) == 1 and
            isinstance(query.where.children[0], NothingNode)
            )):
        # Empty where means return nothing!
        raise EmptyResultSet()

    ret = Query(query.model, kind)
    ret.connection = connection

    # Add the root concrete table as the source table
    root_table = get_top_concrete_parent(query.model)._meta.db_table
    ret.add_source_table(root_table)

    # Extract the ordering of the query results
    for order_col in _extract_ordering_from_query_18(query):
        ret.add_order_by(order_col)

    # Extract any projected columns (values/values_list/only/defer)
    for projected_col in _extract_projected_columns_from_query_18(query):
        ret.add_projected_column(projected_col)

    # Add any extra selects
    for col, select in query.extra_select.items():
        ret.add_extra_select(col, select[0])

    if query.distinct:
        # This must happen after extracting projected cols
        ret.set_distinct(list(query.distinct_fields))

    # Process annotations!
    if query.annotation_select:
        for k, v in query.annotation_select.items():
            ret.add_annotation(k, v)

    # Extract any query offsets and limits
    ret.low_mark = query.low_mark
    ret.high_mark = query.high_mark

    output = WhereNode()
    output.connector = query.where.connector

    _walk_django_where(
        query,
        _django_18_query_walk_trunk,
        _django_18_query_walk_leaf,
        new_parent=output,
        connection=connection,
        negated=query.where.negated,
        model=query.model
    )

    # If there no child nodes, just wipe out the where
    if not output.children:
        output = None

    ret.where = output

    return ret


def get_factory_for_version(factory, version):
    try:
        return factory[version]
    except KeyError:
        return factory[max(factory.keys())]


_FACTORY = {
    (1, 8): _transform_query_18,
    (1, 9): _transform_query_19,
    (1, 10): _transform_query_19, # Same as 1.9
}


def _determine_query_kind_18(query):
    if query.annotations:
        if "__count" in query.annotations:
            field = query.annotations["__count"].input_field
            if isinstance(field, Star) or field.value == "*":
                return "COUNT"

    return "SELECT"


def _determine_query_kind_19(query):
    if query.annotations:
        if "__count" in query.annotations:
            field = query.annotations["__count"].source_expressions[0]
            if isinstance(field, Star) or field.value == "*":
                return "COUNT"

    return "SELECT"


_KIND_FACTORY = {
    (1, 8): _determine_query_kind_18,
    (1, 9): _determine_query_kind_19,
    (1, 10): _determine_query_kind_19  # Same as 1.9
}


def transform_query(connection, query):
    version = django.VERSION[:2]
    kind = get_factory_for_version(_KIND_FACTORY, version)(query)
    return get_factory_for_version(_FACTORY, version)(connection, kind, query)


_ORDERING_FACTORY = {
    (1, 8): _extract_ordering_from_query_18,
    (1, 9): _extract_ordering_from_query_18,  # Same as 1.8
    (1, 10): _extract_ordering_from_query_18  # Same as 1.8
}


def extract_ordering(query):
    version = django.VERSION[:2]
    return get_factory_for_version(_ORDERING_FACTORY, version)(query)
