# encoding: utf-8
# STANDARD LIB
import unittest

# THIRD PARTY
from django.apps.registry import apps  # Apps
from django.conf import settings
from django.db import connection, models
from django.db.migrations.state import ProjectState
from django.test import override_settings

from google.appengine.api import datastore
from google.appengine.runtime import DeadlineExceededError

# DJANGAE
from djangae.contrib import sleuth
from djangae.db.migrations import operations
from djangae.db.migrations.mapper_library import (
    generate_shards,
    shard_query,
    ShardedTaskMarker,
    start_mapping,
)
from djangae.test import TestCase


# Workaround for https://code.djangoproject.com/ticket/28188
def return_a_string():
    return "squirrel"


class TestModel(models.Model):

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "djangae"


class OtherModel(models.Model):

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "djangae"


class OtherAppModel(models.Model):

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "testapp"


class UniqueException(Exception):
    """ An exception which we can explicity throw and catch. """
    pass


def tickle_entity(entity):
    entity['is_tickled'] = True
    datastore.Put(entity)


def tickle_entity_volitle(entity):
    """ Like `tickle_entity`, but raises DeadlineExceededError every 3rd call. """
    call_count = getattr(tickle_entity_volitle, "call_count", 1)
    tickle_entity_volitle.call_count = call_count + 1
    if call_count % 3 == 0:
        raise DeadlineExceededError()
    else:
        tickle_entity(entity)


def flush_task_markers():
    """ Delete all ShardedTaskMarker objects from the DB.
        Useful to call in setUp(), as Django doesn't wipe this kind because there's
        no model for it.
    """
    namespaces = set()
    namespaces.add(settings.DATABASES['default'].get('NAMESPACE', ''))
    namespaces.add(settings.DATABASES.get('ns1', {}).get('NAMESPACE', ''))

    for namespace in namespaces:
        query = datastore.Query(
            ShardedTaskMarker.KIND,
            namespace=namespace,
            keys_only=True
        ).Run()
        datastore.Delete([x for x in query])


class MigrationOperationTests(TestCase):

    multi_db = True

    def setUp(self):
        # We need to clean out the migration task markers from the Datastore between each test, as
        # the standard flush only cleans out models
        super(MigrationOperationTests, self).setUp()
        flush_task_markers()

    def start_operation(self, operation, detonate=True):
        # Make a from_state and a to_state to pass to the operation, these can just be the
        # current state of the models
        from_state = ProjectState.from_apps(apps)
        to_state = from_state.clone()
        schema_editor = connection.schema_editor()
        app_label = TestModel._meta.app_label

        # If we just start the operation then it will hang forever waiting for its mapper task to
        # complete, so we won't even be able to call process_task_queues().  So to avoid that we
        # detonate the _wait_until_task_finished method. Then tasks can be processed after that.
        if detonate:
            with sleuth.detonate(
                "djangae.tests.test_migrations.operations.%s._wait_until_task_finished" % operation.__class__.__name__,
                UniqueException
            ):
                try:
                    operation.database_forwards(app_label, schema_editor, from_state, to_state)
                except UniqueException:
                    pass
        else:
            operation.database_forwards(app_label, schema_editor, from_state, to_state)

    def get_entities(self, model=TestModel, namespace=None):
        namespace = namespace or settings.DATABASES['default'].get('NAMESPACE', '')
        query = datastore.Query(
            model._meta.db_table,
            namespace=namespace,
        )
        return [x for x in query.Run()]

    def test_run_operation_creates_and_updates_task_marker(self):
        """ If we run one of our custom operations, then it should create the task marker in the DB
            and defer a task, then set the marker to 'is_finished' when done.
        """
        TestModel.objects.create()

        operation = operations.AddFieldData(
            "testmodel", "new_field", models.CharField(max_length=100, default="squirrel")
        )
        self.start_operation(operation)

        # Now check that the task marker has been created.
        # Usefully, calling database_forwards() on the operation will have caused it to set the
        # `identifier` attribute on itself, meaning we can now just call _get_task_marker()
        task_marker = datastore.Get(
            [ShardedTaskMarker.get_key(operation.identifier, operation.namespace)]
        )[0]
        if task_marker is None:
            self.fail("Migration operation did not create its task marker")

        self.assertFalse(task_marker.get("is_finished"))
        self.assertNumTasksEquals(1)
        self.process_task_queues()

        # Now check that the task marker has been marked as finished
        task_marker = datastore.Get(
            [ShardedTaskMarker.get_key(operation.identifier, operation.namespace)]
        )[0]
        self.assertTrue(task_marker["is_finished"])
        self.assertNumTasksEquals(0)

    def test_starting_operation_twice_does_not_trigger_task_twice(self):
        """ If we run an operation, and then try to run it again before the task has finished
            processing, then it should not trigger a second task.
        """
        TestModel.objects.create()

        operation = operations.AddFieldData(
            "testmodel", "new_field", models.CharField(max_length=100, default="squirrel")
        )
        self.start_operation(operation)

        task_marker = datastore.Get(
            ShardedTaskMarker.get_key(operation.identifier, operation.namespace)
        )
        self.assertFalse(task_marker["is_finished"])

        # We expect there to be a task queued for processing the operation
        self.assertNumTasksEquals(1)
        # Now try to run it again
        self.start_operation(operation)
        # We expect there to still be the same number of tasks
        self.assertNumTasksEquals(1)

    def test_running_finished_operation_does_not_trigger_new_task(self):
        """ If we re-trigger an operation which has already been run and finished, it should simply
            return without starting a new task or updating the task marker.
        """
        TestModel.objects.create()

        operation = operations.AddFieldData(
            "testmodel", "new_field", models.CharField(max_length=100, default="squirrel")
        )
        # Run the operation and check that it finishes
        with sleuth.watch("djangae.db.migrations.operations.AddFieldData._start_task") as start:
            self.start_operation(operation)
            self.assertTrue(start.called)
        task_marker = datastore.Get(
            ShardedTaskMarker.get_key(operation.identifier, operation.namespace)
        )
        self.assertFalse(task_marker["is_finished"])
        self.assertNumTasksEquals(1)
        self.process_task_queues()
        task_marker = datastore.Get(
            ShardedTaskMarker.get_key(operation.identifier, operation.namespace)
        )
        self.assertTrue(task_marker["is_finished"])

        # Run the operation again.  It should see that's it's finished and just return immediately.
        self.assertNumTasksEquals(0)
        with sleuth.watch("djangae.db.migrations.operations.AddFieldData._start_task") as start:
            self.start_operation(operation, detonate=False)
            self.assertFalse(start.called)
        self.assertNumTasksEquals(0)
        task_marker = datastore.Get(
            ShardedTaskMarker.get_key(operation.identifier, operation.namespace)
        )
        self.assertTrue(task_marker["is_finished"])

    def test_queue_option(self):
        """ The `queue` kwarg should determine the task queue that the operation runs on. """
        for x in range(3):
            TestModel.objects.create()

        operation = operations.AddFieldData(
            "testmodel", "new_field", models.CharField(max_length=100, default=return_a_string),
            queue="another",
            # Ensure that we trigger a re-defer, so that we test that the correct queue is used for
            # subsequent tasks, not just the first one
            entities_per_task=1,
            shard_count=1
        )
        self.start_operation(operation)
        # The task(s) should not be in the default queue, but in the "another" queue instead
        self.assertEqual(self.get_task_count("default"), 0)
        self.assertTrue(self.get_task_count("another") > 0)
        # And if we only run the tasks on the "another" queue, the whole operation should complete.
        self.process_task_queues("another")
        # And the entities should be updated
        entities = self.get_entities()
        self.assertTrue(all(entity['new_field'] == 'squirrel' for entity in entities))

    def test_default_queue_setting(self):
        """ If no `queue` kwarg is passed then the DJANGAE_MIGRATION_DEFAULT_QUEUE setting should
            be used to determine the task queue.
        """
        for x in range(2):
            TestModel.objects.create()

        operation = operations.AddFieldData(
            "testmodel", "new_field", models.CharField(max_length=100, default="squirrel"),
        )
        # Check that starting the operation with a different setting correctly affects the queue.
        # Note that here we don't check that *all* tasks go on the correct queue, just the first
        # one.  We test that more thoroughly in `test_queue_option` above.
        with override_settings(DJANGAE_MIGRATION_DEFAULT_QUEUE="another"):
            self.start_operation(operation)
            self.assertEqual(self.get_task_count("default"), 0)
            self.assertTrue(self.get_task_count("another") > 0)

        self.flush_task_queues()
        flush_task_markers()
        # santity checks:
        assert getattr(settings, "DJANGAE_MIGRATION_DEFAULT_QUEUE", None) is None
        assert self.get_task_count() == 0
        # Trigger the operation without that setting. The task(s) should go on the default queue.
        self.start_operation(operation)
        self.assertTrue(self.get_task_count("default") > 0)

    def test_uid_allows_separate_identical_operations_to_be_run(self):
        """ By passing the 'uid' kwarg to an operation, we should allow it to be run, even if an
            otherwise idential operation has already been run.
        """
        operation1 = operations.AddFieldData(
            "testmodel", "new_field", models.BooleanField(default=True)
        )
        operation2 = operations.AddFieldData(
            "testmodel", "new_field", models.BooleanField(default=True)
        )
        operation3 = operations.AddFieldData(
            "testmodel", "new_field", models.BooleanField(default=True), uid="x"
        )
        # Create a model instance and run the first operation on it
        instance = TestModel.objects.create()
        self.start_operation(operation1)
        self.process_task_queues()
        # Check that the migration ran successfully
        entity = self.get_entities()[0]
        self.assertTrue(entity["new_field"])
        # Now create another entity and make sure that the second migration (which is idential)
        # does NOT run on it
        instance.delete()
        instance = TestModel.objects.create()
        self.start_operation(operation2)
        self.process_task_queues()
        entity = self.get_entities()[0]
        self.assertIsNone(entity.get("new_field"))
        # Now run the third operation, which is identical but has a uid, so SHOULD be run
        self.start_operation(operation3)
        self.process_task_queues()
        entity = self.get_entities()[0]
        self.assertTrue(entity["new_field"])


    def test_addfielddata(self):
        """ Test the AddFieldData operation. """
        for x in range(2):
            TestModel.objects.create()

        # Just for sanity, check that none of the entities have the new field value yet
        entities = self.get_entities()
        self.assertFalse(any(entity.get("new_field") for entity in entities))

        operation = operations.AddFieldData(
            "testmodel", "new_field", models.CharField(max_length=100, default="squirrel")
        )
        self.start_operation(operation)
        self.process_task_queues()

        # The entities should now all have the 'new_field' actually mapped over
        entities = self.get_entities()
        self.assertTrue(all(entity['new_field'] == 'squirrel' for entity in entities))

    def test_removefielddata(self):
        """ Test the RemoveFieldData operation. """
        for x in range(2):
            TestModel.objects.create(name="name_%s" % x)

        # Just for sanity, check that all of the entities have `name` value
        entities = self.get_entities()
        self.assertTrue(all(entity["name"] for entity in entities))

        operation = operations.RemoveFieldData(
            "testmodel", "name", models.CharField(max_length=100)
        )
        self.start_operation(operation)
        self.process_task_queues()

        # The entities should now all have the 'name' value removed
        entities = self.get_entities()
        self.assertFalse(any(entity.get("name") for entity in entities))

    def test_copyfielddata(self):
        """ Test the CopyFieldData operation. """
        for x in range(2):
            TestModel.objects.create(name="name_%s" % x)

        # Just for sanity, check that none of the entities have the new "new_field" value
        entities = self.get_entities()
        self.assertFalse(any(entity.get("new_field") for entity in entities))

        operation = operations.CopyFieldData(
            "testmodel", "name", "new_field"
        )
        self.start_operation(operation)
        self.process_task_queues()

        # The entities should now all have the "new_field" value
        entities = self.get_entities()
        self.assertTrue(all(entity["new_field"] == entity["name"] for entity in entities))

    def test_deletemodeldata(self):
        """ Test the DeleteModelData operation. """
        for x in range(2):
            TestModel.objects.create()

        # Just for sanity, check that the entities exist!
        entities = self.get_entities()
        self.assertEqual(len(entities), 2)

        operation = operations.DeleteModelData("testmodel")
        self.start_operation(operation)
        self.process_task_queues()

        # The entities should now all be gone
        entities = self.get_entities()
        self.assertEqual(len(entities), 0)

    def test_copymodeldata_overwrite(self):
        """ Test the CopyModelData operation with overwrite_existing=True. """

        # Create the TestModel instances, with OtherModel instances with matching PKs
        for x in range(2):
            instance = TestModel.objects.create(name="name_which_will_be_copied")
            OtherModel.objects.create(name="original_name", id=instance.pk)

        # Just for sanity, check that the entities exist
        testmodel_entities = self.get_entities()
        othermodel_entities = self.get_entities(model=OtherModel)
        self.assertEqual(len(testmodel_entities), 2)
        self.assertEqual(len(othermodel_entities), 2)

        operation = operations.CopyModelData(
            "testmodel", "djangae", "othermodel", overwrite_existing=True
        )
        self.start_operation(operation)
        self.process_task_queues()

        # The OtherModel entities should now all have a name lof "name_which_will_be_copied"
        othermodel_entities = self.get_entities(model=OtherModel)
        self.assertTrue(all(
            entity["name"] == "name_which_will_be_copied" for entity in othermodel_entities
        ))

    def test_copymodeldata_no_overwrite(self):
        """ Test the CopyModelData operation with overwrite_existing=False. """

        # Create the TestModel instances, with OtherModel instances with matching PKs only for
        # odd PKs
        for x in range(1, 5):
            TestModel.objects.create(id=x, name="name_which_will_be_copied")
            if x % 2:
                OtherModel.objects.create(id=x, name="original_name")

        # Just for sanity, check that the entities exist
        testmodel_entities = self.get_entities()
        othermodel_entities = self.get_entities(model=OtherModel)
        self.assertEqual(len(testmodel_entities), 4)
        self.assertEqual(len(othermodel_entities), 2)

        operation = operations.CopyModelData(
            "testmodel", "djangae", "othermodel", overwrite_existing=False
        )
        self.start_operation(operation)
        self.process_task_queues()

        # We now expect there to be 4 OtherModel entities, but only the ones which didn't exist
        # already (i.e. the ones with even PKs) should have the name copied from the TestModel
        othermodel_entities = self.get_entities(model=OtherModel)
        self.assertEqual(len(othermodel_entities), 4)
        for entity in othermodel_entities:
            if entity.key().id() % 2:
                self.assertEqual(entity["name"], "original_name")
            else:
                self.assertEqual(entity["name"], "name_which_will_be_copied")

    @unittest.skipIf("ns1" not in settings.DATABASES, "This test is designed for the Djangae testapp settings")
    def test_copymodeldatatonamespace_overwrite(self):
        """ Test the CopyModelDataToNamespace operation with overwrite_existing=True. """
        ns1 = settings.DATABASES["ns1"]["NAMESPACE"]
        # Create instances, with copies in the other namespace with matching IDs
        for x in range(2):
            instance = TestModel.objects.create(name="name_which_will_be_copied")
            instance.save(using="ns1")

        # Just for sanity, check that the entities exist
        entities = self.get_entities()
        ns1_entities = self.get_entities(namespace=ns1)
        self.assertEqual(len(entities), 2)
        self.assertEqual(len(ns1_entities), 2)

        operation = operations.CopyModelDataToNamespace(
            "testmodel", ns1, overwrite_existing=True
        )
        self.start_operation(operation)
        self.process_task_queues()

        # The entities in ns1 should now all have a name lof "name_which_will_be_copied"
        ns1_entities = self.get_entities(namespace=ns1)
        self.assertTrue(all(
            entity["name"] == "name_which_will_be_copied" for entity in ns1_entities
        ))

    @unittest.skipIf("ns1" not in settings.DATABASES, "This test is designed for the Djangae testapp settings")
    def test_copymodeldatatonamespace_no_overwrite(self):
        """ Test the CopyModelDataToNamespace operation with overwrite_existing=False. """
        ns1 = settings.DATABASES["ns1"]["NAMESPACE"]
        # Create the TestModel instances, with OtherModel instances with matching PKs only for
        # odd PKs
        for x in range(1, 5):
            TestModel.objects.create(id=x, name="name_which_will_be_copied")
            if x % 2:
                ns1_instance = TestModel(id=x, name="original_name")
                ns1_instance.save(using="ns1")

        # Just for sanity, check that the entities exist
        entities = self.get_entities()
        ns1_entities = self.get_entities(namespace=ns1)
        self.assertEqual(len(entities), 4)
        self.assertEqual(len(ns1_entities), 2)

        operation = operations.CopyModelDataToNamespace(
            "testmodel", ns1, overwrite_existing=False
        )
        self.start_operation(operation)
        self.process_task_queues()

        # We now expect there to be 4 entities in the new namespace, but only the ones which didn't
        # exist already (i.e. the ones with even PKs) should have their `name` updated
        ns1_entities = self.get_entities(namespace=ns1)
        self.assertEqual(len(ns1_entities), 4)
        for entity in ns1_entities:
            if entity.key().id() % 2:
                self.assertEqual(entity["name"], "original_name")
            else:
                self.assertEqual(entity["name"], "name_which_will_be_copied")

    @unittest.skipIf(
        "ns1" not in settings.DATABASES or "testapp" not in settings.INSTALLED_APPS,
        "This test is designed for the Djangae testapp settings"
    )
    def test_copymodeldatatonamespace_new_app_label(self):
        """ Test the CopyModelDataToNamespace operation with new data being saved to a new model in
            a new app as well as in a new namespace.
        """
        ns1 = settings.DATABASES["ns1"]["NAMESPACE"]
        for x in range(2):
            TestModel.objects.create(name="name_which_will_be_copied")

        # Just for sanity, check that the entities exist
        entities = self.get_entities()
        new_entities = self.get_entities(model=OtherAppModel, namespace=ns1)
        self.assertEqual(len(entities), 2)
        self.assertEqual(len(new_entities), 0)

        operation = operations.CopyModelDataToNamespace(
            "testmodel", ns1, to_app_label="testapp", to_model_name="otherappmodel"
        )
        self.start_operation(operation)
        self.process_task_queues()

        # The entities in ns1 should now all have a name lof "name_which_will_be_copied"
        new_entities = self.get_entities(model=OtherAppModel, namespace=ns1)
        self.assertEqual(len(new_entities), 2)
        self.assertTrue(all(
            entity["name"] == "name_which_will_be_copied" for entity in new_entities
        ))

    def test_mapfunctiononentities(self):
        """ Test the MapFunctionOnEntities operation. """
        for x in range(2):
            TestModel.objects.create()
        # Test that our entities have not had our function called on them
        entities = self.get_entities()
        self.assertFalse(any(entity.get("is_tickled") for entity in entities))

        operation = operations.MapFunctionOnEntities("testmodel", tickle_entity)
        self.start_operation(operation)
        self.process_task_queues()

        entities = self.get_entities()
        self.assertEqual(len(entities), 2)
        self.assertTrue(all(entity.get("is_tickled") for entity in entities))


class ShardQueryTestCase(TestCase):
    """ Tests for the `shard_query` function. """

    def test_query_sharding(self):
        ns1 = settings.DATABASES["default"]["NAMESPACE"]

        for x in range(1, 21):
            TestModel.objects.create(pk=x)

        qry = datastore.Query(TestModel._meta.db_table, namespace=ns1)
        shards = shard_query(qry, 1)
        self.assertEqual(1, len(shards))

        shards = shard_query(qry, 20)
        self.assertEqual(12, len(shards))

        shards = shard_query(qry, 50)
        # We can't create 50 shards if there are only 20 objects
        self.assertEqual(12, len(shards))


class MapperLibraryTestCase(TestCase):
    """ Tests which check the behaviour of the mapper library directly. """

    def setUp(self):
        # We need to clean out the migration task markers from the Datastore between each test, as
        # the standard flush only cleans out models
        super(MapperLibraryTestCase, self).setUp()
        flush_task_markers()

    def _get_testmodel_query(self, db="default"):
        namespace = settings.DATABASES[db].get('NAMESPACE', '')
        return datastore.Query(
            TestModel._meta.db_table,
            namespace=namespace
        )

    def _get_taskmarker_query(self, namespace=""):
        return datastore.Query("ShardedTaskMarker", namespace=namespace)

    def test_basic_processing(self):
        """ Test that calling `start_mapping` with some sensible parameters will do the right
            processing.
        """
        objs = []
        for x in range(2):
            objs.append(TestModel(name="Test-%s" % x))
        TestModel.objects.bulk_create(objs)
        start_mapping("my_lovely_mapper", self._get_testmodel_query(), tickle_entity)
        self.process_task_queues()
        # And check that every entity has been tickled
        self.assertTrue(all(e['is_tickled'] for e in self._get_testmodel_query().Run()))

    def test_cannot_start_same_mapping_twice(self):
        """ Calling `start_mapping` with the same parameters twice then it should NOT create 2
            mappers.
        """
        objs = []
        for x in range(2):
            objs.append(TestModel(name="Test-%s" % x))
        TestModel.objects.bulk_create(objs)

        assert self._get_taskmarker_query().Count() == 0  # Sanity
        marker = start_mapping("my_test_mapper", self._get_testmodel_query(), tickle_entity)
        task_count = self.get_task_count()
        assert marker  # Sanity
        assert task_count  # Sanity
        # Now try to defer the same mapper again
        marker = start_mapping("my_test_mapper", self._get_testmodel_query(), tickle_entity)
        # That shouldn't have worked, so the number of tasks should remain unchanged
        self.assertEqual(self.get_task_count(), task_count)
        # And it should not have returned a marker
        self.assertIsNone(marker)

    def test_can_start_same_mapping_in_2_different_namespaces(self):
        """ Calling `start_mapping` with the same parameters but with different namespaces on the
            query should work and correctly defer 2 processing tasks.
        """
        dbs = ("default", "ns1")
        # Create some objects in 2 different namespaces
        for db in dbs:
            objs = []
            for x in range(2):
                objs.append(TestModel(name="Test-%s" % x))
            TestModel.objects.using(db).bulk_create(objs)

        # Start the same mapper twice but in 2 different namespaces, and check that they both work
        current_task_count = self.get_task_count()
        markers = set()
        for db in dbs:
            marker = start_mapping("my_test_mapper", self._get_testmodel_query(db), tickle_entity)
            self.assertIsNotNone(marker)
            self.assertFalse(marker in markers)
            markers.add(marker)
            new_task_count = self.get_task_count()
            self.assertTrue(new_task_count > current_task_count)
            current_task_count = new_task_count

    def test_mapper_will_continue_after_deadline_exceeded_error(self):
        """ If DeadlineExceededError is encountered when processing one of the entities, the mapper
            should redefer and continue.
        """
        objs = []
        for x in range(8):
            objs.append(TestModel(name="Test-%s" % x))
        TestModel.objects.bulk_create(objs)

        identifier = "my_test_mapper"
        query = self._get_testmodel_query()

        # Reset the call_count on tickle_entity_volitle.  We can't use sleuth.watch because a
        # wrapped function can't be pickled
        tickle_entity_volitle.call_count = 0
        # Run the mapper and run all the tasks
        start_mapping(
            identifier, query, tickle_entity_volitle, shard_count=1,
        )
        self.process_task_queues()
        # Check that the tickle_entity_volitle function was called more times than there are
        # entities (because some calls should have failed and been retried)
        # self.assertTrue(tickle_entity_volitle.call_count > TestModel.objects.count())
        # And check that every entity has been tickled
        self.assertTrue(all(e['is_tickled'] for e in self._get_testmodel_query().Run()))


class GenerateShardsTestCase(unittest.TestCase):
    def test_key_pairs_returned_in_order(self):
        keys = [5, 3, 1, 2, 4]
        result = generate_shards(keys, 2)

        self.assertEqual(result, [(1, 4), (4, None)])

    def test_key_pairs_for_1_shard(self):
        keys = [1, 2, 3, 4, 5]
        result = generate_shards(keys, 1)

        self.assertEqual(result, [(1, None)])

    def test_key_pairs_for_shards_equal_to_keys(self):
        keys = [1, 2, 3, 4, 5]
        result = generate_shards(keys, 5)

        self.assertEqual(result, [(1, 2), (2, 3), (3, 4), (4, 5), (5, None)])

    def test_key_pairs_for_shards_evenly_dividing_num_keys(self):
        keys = [1, 2, 3, 4]
        result = generate_shards(keys, 2)

        self.assertEqual(result, [(1, 3), (3, None)])

    def test_key_pairs_for_shards_not_evenly_dividing_num_keys(self):
        keys = [1, 2, 3, 4, 5]
        result = generate_shards(keys, 2)

        self.assertEqual(result, [(1, 4), (4, None)])

    def test_key_pairs_for_more_shards_than_keys(self):
        keys = [1, 2, 3, 4, 5]
        result = generate_shards(keys, 999)

        self.assertEqual(result, [(1, 2), (2, 3), (3, 4), (4, 5), (5, None)])
