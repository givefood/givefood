import datetime
import logging

from django.conf import settings
from django.apps import apps
from django.db import models, connections
from django.dispatch import receiver
from django.db.models.signals import post_save

from google.appengine.api import datastore
from google.appengine.ext import deferred

from djangae.db import transaction
from djangae.fields import RelatedSetField
from djangae.contrib.mappers.pipes import MapReduceTask, DjangaeMapperPipeline, PIPELINE_BASE_PATH
from djangae.db.utils import django_instance_to_entity
from djangae.db.unique_utils import unique_identifiers_from_entity
from djangae.db.constraints import UniqueMarker
from djangae.db.caching import disable_cache

ACTION_TYPES = [
    ('check', 'Check'),  # Verify all models unique contraint markers exist and are assigned to it.
    ('repair', 'Repair'),  # Recreate any missing markers
    ('clean', 'Clean'),  # Remove any marker that isn't properly linked to an instance.
]

ACTION_STATUSES = [
    ('running', 'Running'),
    ('done', 'Done'),
]

LOG_MSGS = [
    ('missing_marker', "Marker for the unique constraint is missing"),
    ('missing_instance', "Unique constraint marker exists, but doesn't point to the instance"),
    ('already_assigned', "Marker is assigned to a different instance already"),
    ('old_instance_key', "Marker was created when instance was a StringProperty")
]

MAX_ERRORS = 100


def encode_model(model):
    return "%s,%s" % (model._meta.app_label, model._meta.model_name)

def decode_model(model_str):
    return apps.get_model(*model_str.split(','))


class ActionLog(models.Model):
    instance_key = models.TextField()
    marker_key = models.CharField(max_length=500)
    log_type = models.CharField(max_length=255, choices=LOG_MSGS)
    action = models.ForeignKey('UniqueAction')


class UniqueAction(models.Model):
    action_type = models.CharField(choices=ACTION_TYPES, max_length=100)
    model = models.CharField(max_length=100)
    db = models.CharField(max_length=100, default='default')
    status = models.CharField(choices=ACTION_STATUSES, default=ACTION_STATUSES[0][0], editable=False, max_length=100)
    logs = RelatedSetField(ActionLog, editable=False)


def _log_action(action_id, log_type, instance_key, marker_key):
    @transaction.atomic(xg=True)
    def _atomic(action_id, log_type, instance_key, marker_key):
        action = UniqueAction.objects.get(pk=action_id)
        if len(action.logs) > MAX_ERRORS:
            return

        log = ActionLog.objects.create(
            action_id=action_id,
            log_type=log_type,
            instance_key=instance_key,
            marker_key=marker_key)
        action.logs.add(log)
        action.save()
    _atomic(action_id, log_type, instance_key, marker_key)


def log(action_id, log_type, instance_key, marker_key, defer=True):
    """ Shorthand for creating an ActionLog.

    Defer doesn't accept an inline function or an atomic wrapped function directly, so
    we defer a helper function, which wraps the transactionaly decorated one. """
    if defer:
        deferred.defer(_log_action, action_id, log_type, instance_key, marker_key)
    else:
        _log_action(action_id, log_type, instance_key, marker_key)


@receiver(post_save, sender=UniqueAction)
def start_action(sender, instance, created, raw, **kwargs):
    if created == False:
        # we are saving because status is now "done"?
        return

    kwargs = dict(
        action_pk=instance.pk,
    )

    if instance.action_type == "clean":
        kwargs.update(model=instance.model)
        CleanMapper(db=instance.db).start(**kwargs)
    else:
        kwargs.update(repair=instance.action_type=="repair")
        CheckRepairMapper(model=decode_model(instance.model), db=instance.db).start(**kwargs)


def _finish(*args, **kwargs):
    action_pk = kwargs.get('action_pk')

    @transaction.atomic
    def finish_the_action():
        action = UniqueAction.objects.get(pk=action_pk)
        action.status = "done"
        action.save()

    finish_the_action()

class RawMapperMixin(object):
    def get_model_app_(self):
        return None

    def start(self, *args, **kwargs):
        kwargs['db'] = self.db
        mapper_parameters = {
            'entity_kind': self.kind,
            'keys_only': False,
            'kwargs': kwargs,
            'args': args,
            'namespace': settings.DATABASES.get(self.db, {}).get('NAMESPACE'),
        }
        mapper_parameters['_map'] = self.get_relative_path(self.map)
        pipe = DjangaeMapperPipeline(
            self.job_name,
            'djangae.contrib.mappers.thunks.thunk_map',
            'mapreduce.input_readers.RawDatastoreInputReader',
            params=mapper_parameters,
            shards=self.shard_count
        )
        pipe.start(base_path=PIPELINE_BASE_PATH)


class CheckRepairMapper(MapReduceTask):
    name = 'action_mapper'
    kind = '_djangae_unique_marker'

    def start(self, *args, **kwargs):
        kwargs['db'] = self.db
        return super(CheckRepairMapper, self).start(*args, **kwargs)

    @staticmethod
    def finish(*args, **kwargs):
        _finish(*args, **kwargs)

    @staticmethod
    def map(instance, *args, **kwargs):
        """ Figure out what markers the instance should use and verify they're attached to
        this instance. Log any weirdness and in repair mode - recreate missing markers. """
        action_id = kwargs.get("action_pk")
        repair = kwargs.get("repair")

        alias = kwargs.get("db", "default")
        namespace = settings.DATABASES.get(alias, {}).get("NAMESPACE")
        assert alias == (instance._state.db or "default")
        entity = django_instance_to_entity(connections[alias], type(instance), instance._meta.fields, raw=True, instance=instance, check_null=False)
        identifiers = unique_identifiers_from_entity(type(instance), entity, ignore_pk=True)
        identifier_keys = [datastore.Key.from_path(UniqueMarker.kind(), i, namespace=namespace) for i in identifiers]

        markers = datastore.Get(identifier_keys)
        instance_key = str(entity.key())

        markers_to_save = []

        for i, m in zip(identifier_keys, markers):
            marker_key = str(i)
            if m is None:
                # Missig marker
                if repair:
                    new_marker = datastore.Entity(UniqueMarker.kind(), name=i.name(), namespace=namespace)
                    new_marker['instance'] = entity.key()
                    new_marker['created'] = datetime.datetime.now()
                    markers_to_save.append(new_marker)
                else:
                    log(action_id, "missing_marker", instance_key, marker_key)

            elif 'instance' not in m or not m['instance']:
                # Marker with missining instance attribute
                if repair:
                    m['instance'] = entity.key()
                    markers_to_save.append(m)
                else:
                    log(action_id, "missing_instance", instance_key, marker_key)

            elif m['instance'] != entity.key():

                if isinstance(m['instance'], basestring):
                    m['instance'] = datastore.Key(m['instance'])

                    if repair:
                        markers_to_save.append(m)
                    else:
                        log(action_id, "old_instance_key", instance_key, marker_key)

                if m['instance'] != entity.key():
                    # Marker already assigned to a different instance
                    log(action_id, "already_assigned", instance_key, marker_key)
                    # Also log in repair mode as reparing would break the other instance.

        if markers_to_save:
            datastore.Put(markers_to_save)


class CleanMapper(RawMapperMixin, MapReduceTask):
    name = 'action_clean_mapper'
    kind = '_djangae_unique_marker'

    @staticmethod
    def finish(*args, **kwargs):
        _finish(*args, **kwargs)

    @staticmethod
    def map(entity, model, *args, **kwargs):
        """ The Clean mapper maps over all UniqueMarker instances. """

        alias = kwargs.get("db", "default")
        namespace = settings.DATABASES.get(alias, {}).get("NAMESPACE", "")

        model = decode_model(model)
        if not entity.key().id_or_name().startswith(model._meta.db_table + "|"):
            # Only include markers which are for this model
            return

        assert namespace == entity.namespace()
        with disable_cache():
            # At this point, the entity is a unique marker that is linked to an instance of 'model', now we should see if that instance exists!
            instance_id = entity["instance"].id_or_name()
            try:
                instance = model.objects.using(alias).get(pk=instance_id)
            except model.DoesNotExist:
                logging.info("Deleting unique marker %s because the associated instance no longer exists", entity.key().id_or_name())
                datastore.Delete(entity)
                return

            # Get the possible unique markers for the entity, if this one doesn't exist in that list then delete it
            instance_entity = django_instance_to_entity(connections[alias], model, instance._meta.fields, raw=True, instance=instance, check_null=False)
            identifiers = unique_identifiers_from_entity(model, instance_entity, ignore_pk=True)
            identifier_keys = [datastore.Key.from_path(UniqueMarker.kind(), i, namespace=entity["instance"].namespace()) for i in identifiers]
            if entity.key() not in identifier_keys:
                logging.info("Deleting unique marker %s because the it no longer represents the associated instance state", entity.key().id_or_name())
                datastore.Delete(entity)
