"""
Compare the models against the schema actually in the database.

The project ran on `migrate --run-syncdb` for years before it had migrations.
run-syncdb only ever creates tables that don't exist yet -- it never alters an
existing one -- so anything added to a model after its table was first created
only reached the database if someone ran the DDL by hand. `migrate
--fake-initial` cannot detect that: it checks that a table exists, not that its
columns and indexes match.

Run this against a database before faking the initial migration onto it, and
any time you want to know whether the declared indexes are really there.

With --preflight it goes further and answers the operational question: would
the pending migrations actually succeed against this data? Creating a unique
constraint fails outright if the table already holds rows that violate it, so
for every uniqueness rule found missing it counts the offending rows, using the
same NULL semantics a real unique index would. It also lists any invalid
indexes left behind by an interrupted CREATE INDEX CONCURRENTLY, and how many
rows still have anything in the orphan columns 0008 archives.

The checks are derived from what the comparison above found rather than hard
coded, so they stay correct as the models change.

It reports both directions. Things the models declare that the database is
missing are errors -- they make --fake-initial a lie. Indexes the database has
that nothing in the code declares are warnings: they are usually deliberate
(foodbank_earth_open_idx and the other earthdistance GiST indexes were built by
hand, because ll_to_earth() cannot be expressed as a models.Index), but nothing
would recreate them if the database were rebuilt from migrations. Anything
listed as UNMANAGED either wants capturing in a migration or dropping.

Read-only: it issues SELECTs against the catalogs and nothing else.
"""

import importlib

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


def _sql_managed_index_names():
    """
    Index names that a migration builds as raw SQL rather than via Meta.indexes.

    They are absent from the model state by design -- ll_to_earth() cannot be
    expressed as a models.Index, and Django caps index names at 30 characters
    while most of these are longer -- so without this they would show up as
    unmanaged on every run and drown out the ones that really are.
    """
    module = importlib.import_module("givefood.migrations.0004_hand_built_indexes")
    return {name for name, _table, _definition in module.INDEXES}


# Migrations that repair the data behind a constraint rather than just adding
# it. Anything they cover is reported as handled rather than as a blocker,
# because running the migrations is the fix.
_REPAIR_MIGRATIONS = [
    "givefood.migrations.0009_repair_charityyear_pk",
    "givefood.migrations.0010_dedupe_places",
]


def _repaired_by_migration():
    """Map of (table, columns) -> migration that resolves it."""
    repaired = {}
    for path in _REPAIR_MIGRATIONS:
        module = importlib.import_module(path)
        name = path.rsplit(".", 1)[-1]
        for table, columns in getattr(module, "REPAIRS", []):
            repaired[(table, tuple(sorted(columns)))] = name
    return repaired


class Command(BaseCommand):

    help = "Report differences between the models and the live database schema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            default="givefood",
            help="App label to check (default: givefood)",
        )
        parser.add_argument(
            "--preflight",
            action="store_true",
            help="Also scan table data for anything that would make the "
                 "pending migrations fail",
        )

    def handle(self, *args, **options):

        app_label = options["app"]
        models = apps.get_app_config(app_label).get_models(include_auto_created=True)

        sql_managed = _sql_managed_index_names() if app_label == "givefood" else set()

        problems = 0
        missing_unique = []
        orphan_columns = []

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"
            )
            db_tables = {row[0] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                """
            )
            db_columns = {}
            for table, column in cursor.fetchall():
                db_columns.setdefault(table, set()).add(column)

            cursor.execute(
                """
                SELECT tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = current_schema()
                """
            )
            index_rows = cursor.fetchall()
            db_indexes = {row[1] for row in index_rows}
            db_index_defs = {row[1]: (row[0], row[2]) for row in index_rows}

            table_constraints = {}
            for table in db_tables:
                table_constraints[table] = connection.introspection.get_constraints(
                    cursor, table
                )

        unmanaged = []

        for model in sorted(models, key=lambda m: m._meta.db_table):

            table = model._meta.db_table

            if table not in db_tables:
                self.stdout.write(self.style.ERROR("MISSING TABLE  %s" % table))
                problems += 1
                continue

            expected_columns = {f.column for f in model._meta.local_fields}
            actual_columns = db_columns.get(table, set())

            for column in sorted(expected_columns - actual_columns):
                # The model reads and writes this column but it isn't there.
                self.stdout.write(
                    self.style.ERROR("MISSING COLUMN %s.%s" % (table, column))
                )
                problems += 1

            for column in sorted(actual_columns - expected_columns):
                # Harmless, but it means something was dropped from the model
                # without being dropped from the table.
                self.stdout.write(
                    self.style.WARNING("ORPHAN COLUMN  %s.%s" % (table, column))
                )
                orphan_columns.append((table, column))

            for index in model._meta.indexes:
                if index.name not in db_indexes:
                    # Declared in Meta.indexes but never built -- the query it
                    # was written for is still doing whatever it did before.
                    self.stdout.write(
                        self.style.ERROR(
                            "MISSING INDEX  %s.%s" % (table, index.name)
                        )
                    )
                    problems += 1

            for constraint in model._meta.constraints:
                if constraint.name not in db_indexes:
                    self.stdout.write(
                        self.style.ERROR(
                            "MISSING CONSTRAINT %s.%s" % (table, constraint.name)
                        )
                    )
                    problems += 1

            # Uniqueness, checked by columns rather than by name: run-syncdb
            # and hand-written DDL both name these differently from Django, and
            # a uniqueness rule the model claims but the database does not
            # enforce lets duplicates in that the code assumes cannot exist.
            # Compared as sets of columns, not ordered tuples: a UNIQUE index
            # rejects the same rows whatever order its columns are declared in,
            # and the hand-written ones on this database do not use Django's
            # order. Column order matters for whether an index can serve a
            # query, but that is not what this check is about.
            actual_unique = {
                frozenset(c for c in (info.get("columns") or []) if c)
                for info in table_constraints.get(table, {}).values()
                if info.get("unique") or info.get("primary_key")
            }

            expected_unique = {
                frozenset([field.column])
                for field in model._meta.local_fields
                if field.unique or field.primary_key
            }
            for unique_set in model._meta.unique_together:
                expected_unique.add(
                    frozenset(model._meta.get_field(f).column for f in unique_set)
                )

            for columns in sorted(expected_unique - actual_unique, key=sorted):
                self.stdout.write(
                    self.style.ERROR(
                        "MISSING UNIQUE  %s (%s)" % (table, ", ".join(sorted(columns)))
                    )
                )
                problems += 1
                is_pk = any(
                    field.primary_key and frozenset([field.column]) == columns
                    for field in model._meta.local_fields
                )
                missing_unique.append((table, sorted(columns), is_pk))

            # The other direction: indexes the database has that nothing in the
            # code would recreate. Matched by declared name first (which covers
            # the expression indexes in Meta.indexes, whose columns Postgres
            # reports as an expression rather than a column list), then by the
            # set of columns they cover.
            declared_names = (
                {index.name for index in model._meta.indexes}
                | {constraint.name for constraint in model._meta.constraints}
                | sql_managed
            )

            declared_columns = set()
            for field in model._meta.local_fields:
                if field.primary_key or field.unique or field.db_index or field.remote_field:
                    declared_columns.add((field.column,))
            for unique_set in model._meta.unique_together:
                declared_columns.add(
                    tuple(model._meta.get_field(f).column for f in unique_set)
                )
            for index in model._meta.indexes:
                if index.fields:
                    declared_columns.add(
                        tuple(
                            model._meta.get_field(f.lstrip("-")).column
                            for f in index.fields
                        )
                    )

            for name, info in table_constraints.get(table, {}).items():
                if not (info.get("index") or info.get("unique") or info.get("primary_key")):
                    continue
                if name in declared_names:
                    continue
                columns = tuple(c for c in (info.get("columns") or []) if c)
                if columns and columns in declared_columns:
                    continue
                unmanaged.append((table, name))

        for table, name in unmanaged:
            definition = db_index_defs.get(name, (table, "?"))[1]
            self.stdout.write(
                self.style.WARNING("UNMANAGED INDEX %s.%s" % (table, name))
            )
            self.stdout.write("                %s" % definition)

        if unmanaged:
            self.stdout.write(
                self.style.WARNING(
                    "\n%s index(es) exist only in the database. Nothing would "
                    "recreate them from a fresh migrate -- capture them in a "
                    "migration or drop them." % len(unmanaged)
                )
            )

        if problems:
            self.stdout.write(
                self.style.ERROR(
                    "\n%s difference(s) that would make --fake-initial a lie." % problems
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nModels are fully present in the database. Safe to fake "
                    "the initial migration."
                )
            )

        if options["preflight"]:
            self.preflight(missing_unique, orphan_columns)

    def preflight(self, missing_unique, orphan_columns):
        """Scan table data for anything that would abort the pending migrations."""

        self.stdout.write("\n--- preflight ---")

        blockers = 0
        repaired = _repaired_by_migration()

        with connection.cursor() as cursor:

            # An interrupted CREATE INDEX CONCURRENTLY leaves an invalid index
            # holding the name. The planner ignores it, and a retry fails with
            # "already exists", so it has to go before anything is re-run.
            cursor.execute(
                """
                SELECT i.relname
                FROM pg_index x
                JOIN pg_class i ON i.oid = x.indexrelid
                WHERE NOT x.indisvalid
                ORDER BY i.relname
                """
            )
            for (name,) in cursor.fetchall():
                self.stdout.write(
                    self.style.ERROR(
                        "INVALID INDEX  %s -- drop it before migrating: "
                        'DROP INDEX CONCURRENTLY IF EXISTS "%s";' % (name, name)
                    )
                )
                blockers += 1

            for table, columns, is_pk in missing_unique:

                quoted = ", ".join('"%s"' % c for c in columns)

                # A unique index treats NULLs as distinct, so rows with a NULL
                # in any of the columns never collide. Excluding them here
                # keeps this honest about what would really block creation.
                not_null = " AND ".join('"%s" IS NOT NULL' % c for c in columns)
                cursor.execute(
                    'SELECT count(*) FROM (SELECT 1 FROM "%s" WHERE %s '
                    "GROUP BY %s HAVING count(*) > 1) d" % (table, not_null, quoted)
                )
                duplicate_groups = cursor.fetchone()[0]

                fixed_by = repaired.get((table, tuple(sorted(columns))))

                if duplicate_groups and fixed_by:
                    self.stdout.write(
                        self.style.WARNING(
                            "HANDLED        %s (%s) -- %s duplicate value(s), "
                            "resolved by %s"
                            % (table, ", ".join(columns), duplicate_groups, fixed_by)
                        )
                    )
                elif duplicate_groups:
                    self.stdout.write(
                        self.style.ERROR(
                            "DUPLICATES     %s (%s) -- %s value(s) appear more "
                            "than once; the unique index cannot be created "
                            "until they are resolved"
                            % (table, ", ".join(columns), duplicate_groups)
                        )
                    )
                    blockers += 1

                if is_pk:
                    # A primary key additionally requires NOT NULL.
                    cursor.execute(
                        'SELECT count(*) FROM "%s" WHERE %s IS NULL'
                        % (table, '"%s"' % columns[0])
                    )
                    nulls = cursor.fetchone()[0]
                    if nulls and fixed_by:
                        self.stdout.write(
                            self.style.WARNING(
                                "HANDLED        %s.%s -- %s NULL row(s), filled "
                                "in by %s" % (table, columns[0], nulls, fixed_by)
                            )
                        )
                    elif nulls:
                        self.stdout.write(
                            self.style.ERROR(
                                "NULLS          %s.%s -- %s row(s) are NULL; a "
                                "primary key cannot be added until they are "
                                "filled in" % (table, columns[0], nulls)
                            )
                        )
                        blockers += 1

            # Not a blocker, but it is what the column drop will archive.
            for table, column in orphan_columns:
                cursor.execute(
                    'SELECT count(*) FROM "%s" WHERE "%s" IS NOT NULL' % (table, column)
                )
                populated = cursor.fetchone()[0]
                if populated:
                    self.stdout.write(
                        self.style.WARNING(
                            "POPULATED      %s.%s -- %s row(s) carry a value, "
                            "archived to givefood_dropped_foodbank_columns"
                            % (table, column, populated)
                        )
                    )

        if blockers:
            self.stdout.write(
                self.style.ERROR(
                    "\n%s blocker(s). Resolve these before migrating." % blockers
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\nNothing in the data blocks the migrations.")
            )
