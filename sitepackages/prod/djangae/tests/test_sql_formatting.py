# -*- coding: utf8 -*-
from django.db import connections, models

from djangae.test import TestCase

from djangae.db.backends.appengine.formatting import (
    _generate_values_expression, generate_sql_representation
)
from djangae.db.backends.appengine.commands import (
    SelectCommand, InsertCommand, DeleteCommand, UpdateCommand
)

from django.db.models.sql.subqueries import UpdateQuery


class FormattingTestModel(models.Model):
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=10)
    field3 = models.TextField()
    field4 = models.BinaryField()


class SelectFormattingTest(TestCase):

    def test_select_star(self):
        command = SelectCommand(connections['default'], FormattingTestModel.objects.all().query)
        sql = generate_sql_representation(command)

        expected = """
SELECT (*) FROM {}
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)

    def test_select_columns(self):
        command = SelectCommand(
            connections['default'],
            FormattingTestModel.objects.only("field1", "field2").all().query
        )
        sql = generate_sql_representation(command)

        expected = """
SELECT (field1, field2, id) FROM {}
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)

    def test_select_in(self):
        """
            We don't build explicit IN queries, only multiple OR branches
            there is essentially no difference between the two
        """
        command = SelectCommand(
            connections['default'],
            FormattingTestModel.objects.filter(field1__in=[1, 2]).query
        )
        sql = generate_sql_representation(command)

        expected = """
SELECT (*) FROM {} WHERE (field1=2) OR (field1=1)
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)

    def test_limit_applied(self):
        command = SelectCommand(
            connections['default'],
            FormattingTestModel.objects.all()[10:15].query
        )
        sql = generate_sql_representation(command)

        expected = """
SELECT (*) FROM {} OFFSET 10 LIMIT 5
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)

    def test_ordering_applied(self):
        command = SelectCommand(
            connections['default'],
            FormattingTestModel.objects.order_by("-field1").query
        )
        sql = generate_sql_representation(command)

        expected = """
SELECT (*) FROM {} ORDER BY field1 DESC
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)

        command = SelectCommand(
            connections['default'],
            FormattingTestModel.objects.order_by("field1", "-field2").query
        )
        sql = generate_sql_representation(command)

        expected = """
SELECT (*) FROM {} ORDER BY field1, field2 DESC
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)

    def test_unicode_error(self):
        command = SelectCommand(
            connections['default'],
            FormattingTestModel.objects.filter(field2=u"Jacqu\xe9s").query
        )
        sql = generate_sql_representation(command)

        expected = u"""
SELECT (*) FROM {} WHERE (field2='Jacqu\xe9s')
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)


class InsertFormattingTest(TestCase):
    def test_single_insert(self):
        instance = FormattingTestModel(field1=1, field2="Two", field3="Three", field4=b'\xff')

        command = InsertCommand(
            connections["default"],
            FormattingTestModel,
            [instance],
            [
                FormattingTestModel._meta.get_field(x)
                for x in ("field1", "field2", "field3", "field4")
            ], True
        )

        sql = generate_sql_representation(command)

        expected = """
INSERT INTO {} (field1, field2, field3, field4) VALUES (1, 'Two', 'Three', '<binary>')
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)


class DeleteFormattingTest(TestCase):
    def test_delete_all(self):
        command = DeleteCommand(
            connections['default'],
            FormattingTestModel.objects.all().query
        )
        sql = generate_sql_representation(command)

        expected = """
DELETE FROM {}
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)

    def test_delete_filtered(self):
        command = DeleteCommand(
            connections['default'],
            FormattingTestModel.objects.filter(field1=1).query
        )
        sql = generate_sql_representation(command)

        expected = """
DELETE FROM {} WHERE (field1=1)
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)


class UpdateFormattingTest(TestCase):
    def test_update_all(self):
        query = FormattingTestModel.objects.all().query.clone(UpdateQuery)
        query.add_update_values({"field1": 1})

        command = UpdateCommand(
            connections['default'],
            query
        )

        sql = generate_sql_representation(command)

        expected = """
REPLACE INTO {} (field1) VALUES (1)
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)

    def test_update_filtered(self):
        query = FormattingTestModel.objects.filter(field1=1).query.clone(UpdateQuery)
        query.add_update_values({"field1": 2})

        command = UpdateCommand(
            connections['default'],
            query
        )
        sql = generate_sql_representation(command)

        expected = """
REPLACE INTO {} (field1) VALUES (2) WHERE (field1=1)
""".format(FormattingTestModel._meta.db_table).strip()

        self.assertEqual(expected, sql)


class UnrecognisedQueryTypeErrorTest(TestCase):

    def test_unrecognised_type_raises_not_implemented_error(self):
        class Command(object):
            class Query(object):
                def serialize(self, *args, **kwargs):
                    return '{}'
            query = Query()

        with self.assertRaises(NotImplementedError):
            generate_sql_representation(Command())


class GenerateValuesExpressionTest(TestCase):
    """Tests for `djangae.db.backends.appengine.formatting._generate_values_expression`."""

    def test_unicode_error(self):
        """Test that _generate_values_expression does not raise a unicode error."""
        class Mock(object):
            value1 = u'ûnīçøde hërę'

        m = Mock()
        output = _generate_values_expression([m], ['value1'])
        self.assertEqual(output, '(\'' + m.value1 + '\')')
