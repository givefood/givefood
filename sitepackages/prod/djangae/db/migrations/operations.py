# STANDARD LIB
from __future__ import print_function

import logging
import sys
import time

# THIRD PARTY
from django.db import DataError
from django.db.migrations.operations.base import Operation
from google.appengine.api.datastore import Delete, Query, Get, Key, Put, RunInTransaction
from google.appengine.api import datastore_errors
from google.appengine.runtime import DeadlineExceededError

# DJANGAE
from djangae.db.backends.appengine.caching import remove_entities_from_cache_by_key
from djangae.db.backends.appengine.commands import reserve_id
from djangae.utils import retry
from . import mapper_library

from .constants import TASK_RECHECK_INTERVAL
from .utils import clone_entity


logger = logging.getLogger(__name__)
TESTING = 'test' in sys.argv


class DjangaeMigration(object):
    """ Base class to enable us to distinguish between Djangae migrations and Django migrations.
    """
    pass


class BaseEntityMapperOperation(Operation, DjangaeMigration):
    """ Base class for operations which map over Datastore Entities, rather than Django model
        instances.
    """

    reversible = False
    reduces_to_sql = False

    def __init__(self, *args, **kwargs):
        self.uid = kwargs.pop("uid", "")
        self.shard_count = kwargs.pop("shard_count", None)
        self.entities_per_task = kwargs.pop("entities_per_task", None)
        self.queue = kwargs.pop("queue", None)
        self.skip_errors = kwargs.pop("skip_errors", False)
        super(BaseEntityMapperOperation, self).__init__(*args, **kwargs)

    def state_forwards(self, app_label, state):
        """ As all Djangae migrations are only supplements to the Django migrations, we don't need
            to do any altering of the model state.
        """
        pass

    def _print(self, *objects):
        if not TESTING:
            print(*objects)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        # Django's `migrate` command writes to stdout without a trailing line break, which means
        # that unless we print a blank line our first print statement is on the same line
        self._print("")   # yay

        self.identifier = self._get_identifier(app_label, schema_editor, from_state, to_state)
        if self.uid:
            self.identifier = "{}.{}".format(self.uid, self.identifier)

        self._set_map_kind(app_label, schema_editor, from_state, to_state)
        self._pre_map_hook(app_label, schema_editor, from_state, to_state)
        self.namespace = schema_editor.connection.settings_dict.get("NAMESPACE")

        if mapper_library.mapper_exists(self.identifier, self.namespace):
            self._wait_until_task_finished()
            return

        self._print("Deferring migration operation task for %s" % self.identifier)
        self._start_task()

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        raise NotImplementedError("Erm...?  Help?!")

    def _wait_until_task_finished(self):
        if mapper_library.is_mapper_finished(self.identifier, self.namespace):
            self._print("Task for migration operation '%s' already finished. Skipping." % self.identifier)
            return

        while mapper_library.is_mapper_running(self.identifier, self.namespace):
            self._print("Waiting for migration operation '%s' to complete." % self.identifier)
            time.sleep(TASK_RECHECK_INTERVAL)

        self._print("Migration operation '%s' completed!" % self.identifier)

    def _start_task(self):
        assert not mapper_library.is_mapper_running(self.identifier, self.namespace), "Migration started by separate thread?"

        query = Query(self.map_kind, namespace=self.namespace)
        return mapper_library.start_mapping(
            self.identifier, query, self, operation_method="_wrapped_map_entity",
            shard_count=self.shard_count, entities_per_task=self.entities_per_task,
            queue=self.queue
        )

    def _wrapped_map_entity(self, entity):
        """ Wrapper for self._map_entity which removes the entity from Djangae's cache. """

        # TODO: Note that other threads (from the general application running) could also be
        # modifying the entity, and that we're not using Djangae's transaction managers for our
        # stuff here.

        remove_entities_from_cache_by_key([entity.key()], self.namespace)
        try:
            retry(self._map_entity, entity)
        except DeadlineExceededError:
            # This is (probably) not an error with the individual entity, but more likey that the
            # task has tried to process too many entities. Either way, we always re-raise it so
            # that the mapper library can deal with it
            raise
        except Exception:
            if self.skip_errors:
                logger.exception(
                    "Error processing operation %s for entity %s.  Skipping.",
                    self.identifier, entity.key()
                )
            else:
                raise
        if entity.key():
            # Assuming the entity hasn't been deleted and/or it's key been wiped...
            remove_entities_from_cache_by_key([entity.key()], self.namespace)


    ##############################################################################################
    #                           METHODS FOR SUBCLASSES TO IMPLEMENT
    ##############################################################################################

    def _pre_map_hook(self, app_label, schema_editor, from_state, to_state):
        """ A hook for subclasses to do anything that needs to be done before the mapping starts
            but which cannot be done in __init__ due to the need for the schema_editor/state/etc.
        """
        pass

    def _get_identifier(self, app_label, schema_editor, from_state, to_state):
        """ Return an ID for self.identifier, which must be a string which uniquely identifies this operation
            across the entire site.  It must be able to fit in a Datastore string property.
            This will likely need to use app_label combined with values passed to __init__.
        """
        raise NotImplementedError(
            "Subclasses of EntityMapperOperation must implement _get_identifier"
        )

    def _set_map_kind(self, app_label, schema_editor, from_state, to_state):
        """ Set an attribute 'map_kind' of the 'kind' of Datastore Entities to be mapped over. """
        raise NotImplementedError(
            "Subclasses of EntityMapperOperation must implement _set_map_kind"
        )

    def _map_entity(self, entity):
        """ Hook for subclasses to implement.  This is called for every Entity and should do
            whatever data manipulation is necessary.  Note that whatever you do to the entity
            must be done transactionally; this is not wrapped in a transaction.
        """
        raise NotImplementedError("Subclasses of EntityMapperOperation must implement _map_entity")


class AddFieldData(BaseEntityMapperOperation):

    def __init__(self, model_name, name, field, **kwargs):
        self.model_name = model_name
        self.name = name
        self.field = field
        super(AddFieldData, self).__init__(**kwargs)

    def _get_identifier(self, app_label, schema_editor, from_state, to_state):
        identifier = "%s.%s.%s:%s" % (
            app_label, self.model_name, self.__class__.__name__, self.name
        )
        return identifier

    def _set_map_kind(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        kind = model._meta.db_table
        self.map_kind = kind

    def _map_entity(self, entity):
        column_name = self.field.db_column or self.name
        # Call get_default() separately for each entity, in case it's a callable like timezone.now
        value = self.field.get_default()

        def txn(entity):
            entity = Get(entity.key())
            entity[column_name] = value
            Put(entity)

        RunInTransaction(txn, entity)


class RemoveFieldData(BaseEntityMapperOperation):

    def __init__(self, model_name, name, field, **kwargs):
        self.model_name = model_name
        self.name = name
        self.field = field
        super(RemoveFieldData, self).__init__(**kwargs)

    def _get_identifier(self, app_label, schema_editor, from_state, to_state):
        identifier = "%s.%s.%s:%s" % (
            app_label, self.model_name, self.__class__.__name__, self.name
        )
        return identifier

    def _set_map_kind(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        kind = model._meta.db_table
        self.map_kind = kind

    def _map_entity(self, entity):
        column_name = self.field.db_column or self.name

        def txn(entity):
            entity = Get(entity.key())
            try:
                del entity[column_name]
            except KeyError:
                return
            Put(entity)

        RunInTransaction(txn, entity)


class CopyFieldData(BaseEntityMapperOperation):

    def __init__(self, model_name, from_column_name, to_column_name, **kwargs):
        self.model_name = model_name
        self.from_column_name = from_column_name
        self.to_column_name = to_column_name
        super(CopyFieldData, self).__init__(**kwargs)

    def _get_identifier(self, app_label, schema_editor, from_state, to_state):
        identifier = "%s.%s.%s:%s.%s" % (
            app_label, self.model_name, self.__class__.__name__,
            self.from_column_name, self.to_column_name
        )
        return identifier

    def _set_map_kind(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        kind = model._meta.db_table
        self.map_kind = kind

    def _map_entity(self, entity):

        def txn(entity):
            entity = Get(entity.key())
            try:
                entity[self.to_column_name] = entity[self.from_column_name]
            except KeyError:
                return
            Put(entity)

        RunInTransaction(txn, entity)


class DeleteModelData(BaseEntityMapperOperation):

    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        super(DeleteModelData, self).__init__(**kwargs)

    def _get_identifier(self, app_label, schema_editor, from_state, to_state):
        identifier = "%s.%s:%s" % (
            app_label, self.model_name, self.__class__.__name__
        )
        return identifier

    def _set_map_kind(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        kind = model._meta.db_table
        self.map_kind = kind

    def _map_entity(self, entity):
        try:
            Delete(entity.key())
        except datastore_errors.EntityNotFoundError:
            return


class CopyModelData(BaseEntityMapperOperation):
    """ Copies entities from one entity kind to another. """

    def __init__(
        self, model_name, to_app_label, to_model_name,
        overwrite_existing=False, **kwargs
    ):
        self.model_name = model_name
        self.to_app_label = to_app_label
        self.to_model_name = to_model_name
        self.overwrite_existing = overwrite_existing
        super(CopyModelData, self).__init__(**kwargs)

    def _get_identifier(self, app_label, schema_editor, from_state, to_state):
        identifier = "%s.%s.%s:%s.%s" % (
            app_label, self.model_name, self.__class__.__name__,
            self.to_app_label, self.to_model_name
        )
        return identifier

    def _set_map_kind(self, app_label, schema_editor, from_state, to_state):
        """ We need to map over the entities that we're copying *from*. """
        model = to_state.apps.get_model(app_label, self.model_name)
        kind = model._meta.db_table
        self.map_kind = kind

    def _pre_map_hook(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(self.to_app_label, self.to_model_name)
        self.to_kind = to_model._meta.db_table

    def _map_entity(self, entity):
        new_key = Key.from_path(self.to_kind, entity.key().id_or_name(), namespace=self.namespace)

        def txn():
            try:
                existing = Get(new_key)
            except datastore_errors.EntityNotFoundError:
                existing = None
            if existing and not self.overwrite_existing:
                return
            if isinstance(entity.key().id_or_name(), (int, long)):
                reserve_id(self.to_kind, entity.key().id_or_name(), self.namespace)
            new_entity = clone_entity(entity, new_key)
            Put(new_entity)

        RunInTransaction(txn)


class CopyModelDataToNamespace(BaseEntityMapperOperation):
    """ Copies entities from one Datastore namespace to another. """

    def __init__(
        self, model_name, to_namespace, to_app_label=None, to_model_name=None,
        overwrite_existing=False, **kwargs
    ):
        self.model_name = model_name
        self.to_namespace = to_namespace
        self.to_app_label = to_app_label
        self.to_model_name = to_model_name
        self.overwrite_existing = overwrite_existing
        super(CopyModelDataToNamespace, self).__init__(**kwargs)

    def _get_identifier(self, app_label, schema_editor, from_state, to_state):
        to_app_label = self.to_app_label or app_label
        to_model_name = self.to_model_name or self.model_name
        identifier = "%s.%s.%s:%s.%s.%s" % (
            app_label, self.model_name, self.__class__.__name__, self.to_namespace, to_app_label,
            to_model_name
        )
        return identifier

    def _set_map_kind(self, app_label, schema_editor, from_state, to_state):
        """ We need to map over the entities that we're copying *from*. """
        model = to_state.apps.get_model(app_label, self.model_name)
        self.map_kind = model._meta.db_table

    def _pre_map_hook(self, app_label, schema_editor, from_state, to_state):
        to_app_label = self.to_app_label or app_label
        to_model_name = self.to_model_name or self.model_name
        to_model = to_state.apps.get_model(to_app_label, to_model_name)
        self.to_kind = to_model._meta.db_table

    def _map_entity(self, entity):
        new_key = Key.from_path(
            self.to_kind, entity.key().id_or_name(), namespace=self.to_namespace
        )

        parent = entity.parent()
        if parent:
            # If the entity has an ancestor then we need to make sure that that ancestor exists in
            # the new namespace as well
            new_parent_key = Key.from_path(
                parent.kind(), parent.is_or_name(), namespace=self.to_namespace
            )
            new_parent_exists = Get([new_parent_key])[0]
            if not new_parent_exists:
                raise DataError(
                    "Trying to copy entity with an ancestor (%r) to a new namespace but the "
                    "ancestor does not exist in the new namespace. Copy the ancestors first."
                    % entity.key()
                )

        def txn():
            existing = Get([new_key])[0]
            if existing and not self.overwrite_existing:
                return
            if isinstance(entity.key().id_or_name(), (int, long)):
                reserve_id(self.to_kind, entity.key().id_or_name(), self.to_namespace)
            new_entity = clone_entity(entity, new_key)
            Put(new_entity)

        RunInTransaction(txn)


class MapFunctionOnEntities(BaseEntityMapperOperation):
    """ Operation for calling a custom function on each entity of a given model. """

    def __init__(self, model_name, function, **kwargs):
        self.model_name = model_name
        self.function = function
        super(MapFunctionOnEntities, self).__init__(**kwargs)

    def _get_identifier(self, app_label, schema_editor, from_state, to_state):
        identifier = "%s.%s.%s:%s" % (
            app_label, self.model_name, self.__class__.__name__, self.function.__name__
        )
        return identifier

    def _set_map_kind(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        kind = model._meta.db_table
        self.map_kind = kind

    def _map_entity(self, entity):
        self.function(entity)
