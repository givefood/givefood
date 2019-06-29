from mapreduce import input_readers
import itertools
import logging
from django.apps import apps
from djangae import utils
from djangae.storage import UniversalNewLineBlobReader


class DjangoInputReader(input_readers.InputReader):

    REQUIRED_PARAMS = ('model',)

    def __init__(self, start_id, end_id, model, *args, **kwargs):
        self.shard_id = 1
        self.start_id = start_id
        self.end_id = end_id
        self.raw_model = model
        self.db = kwargs.pop('db', 'default')
        app, model = self.raw_model.split('.')
        self.model = apps.get_model(app, model)
        super(DjangoInputReader, self).__init__(*args, **kwargs)

    def __iter__(self):
        if self.start_id > self.end_id:
            # This can happen if we are the last shard and
            # the shard size caused each previous shard to process an additional model
            return

        query = self.model.objects.using(self.db)

        if self.start_id:
            query = query.filter(pk__gt=self.start_id).filter(pk__lte=self.end_id)
        query = query.order_by('pk')

        for model in utils.get_in_batches(query, batch_size=500):
            # From the mapreduce docs (AbstractDatastoreInputReader):
            #     The caller must consume yielded values so advancing the KeyRange
            #     before yielding is safe.
            self.start_id = model.id
            yield model

    @classmethod
    def validate(cls, mapper_spec):
        if mapper_spec.input_reader_class() != cls:
            raise input_readers.BadReaderParamsError("Input reader class mismatch")
        params = input_readers._get_params(mapper_spec)
        for param in cls.REQUIRED_PARAMS:
            if not param in params:
                raise input_readers.BadReaderParamsError("Parameter missing: %s" % param)

    @classmethod
    def split_input(cls, mapper_spec):
        shard_count = mapper_spec.shard_count

        # Grab the input parameters for the split
        params = input_readers._get_params(mapper_spec)
        logging.info("Params: %r", params)

        db = params['db']
        # Unpickle the query
        app, model = params['model'].split('.')
        model = apps.get_model(app, model)

        # Grab the lowest pk
        query = model.objects.using(db).all()
        query = query.order_by('pk')

        try:
            first_id = query.values_list('pk', flat=True)[:1][0]

            query = query.order_by('-pk')
            last_id = query.values_list('pk', flat=True)[:1][0]
        except IndexError:
            return [DjangoInputReader(0, 0, params['model'], db=db)]

        pk_range = last_id - first_id

        logging.info("Query range: %s - %s = %s", first_id, last_id, pk_range)

        if pk_range < shard_count or shard_count == 1:
            return [DjangoInputReader(first_id-1, last_id, params['model'], db=db)]

        readers = []
        max_shard_size = int(float(pk_range) / float(shard_count))
        if pk_range % shard_count:
            max_shard_size += 1

        shard_id = 1
        # Splitting could be much smarter by taking a __scatter__ sample and
        # clustering, which is how the DatastoreInputWriter from the mapreduce
        # splits on pks
        for i in itertools.count(first_id-1, max_shard_size):
            if i >= last_id:
                break

            shard_start_id = i
            shard_end_id = i + max_shard_size
            if shard_end_id > last_id:
                shard_end_id = last_id

            logging.info("Creating shard: %s - %s", shard_start_id, shard_end_id)
            reader = DjangoInputReader(shard_start_id, shard_end_id, params['model'], db=db)
            reader.shard_id = shard_id
            readers.append(reader)
            shard_id += 1
        return readers

    @classmethod
    def from_json(cls, input_shard_state):
        start_id = input_shard_state['start']
        end_id = input_shard_state['end']
        shard_id = input_shard_state['shard_id']
        model = input_shard_state['model']
        db = input_shard_state['db']

        reader = DjangoInputReader(start_id, end_id, model, db=db)
        reader.shard_id = shard_id
        return reader

    def to_json(self):
        return {
            'start': self.start_id,
            'end': self.end_id,
            'shard_id': self.shard_id,
            'model': self.raw_model,
            'db': self.db,
        }


class DjangoQuerySpec(object):
  """Encapsulates everything about a query needed by DatastoreInputReader."""

  DEFAULT_BATCH_SIZE = 50

  def __init__(self,
               entity_kind,
               keys_only=None,
               filters=None,
               batch_size=None,
               model_class_path=None,
               app=None,
               ns=None):
    self.entity_kind = entity_kind
    self.keys_only = keys_only or False
    self.filters = filters or None
    self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
    self.model_class_path = model_class_path
    self.app = app
    self.ns = ns

  def to_json(self):
    return {"entity_kind": self.entity_kind,
            "keys_only": self.keys_only,
            "filters": self.filters,
            "batch_size": self.batch_size,
            "model_class_path": self.model_class_path,
            "app": self.app,
            "ns": self.ns}

  @classmethod
  def from_json(cls, json):
    return cls(json["entity_kind"],
               json["keys_only"],
               json["filters"],
               json["batch_size"],
               json["model_class_path"],
               json["app"],
               json["ns"])


class BlobstoreUniversalLineInputReader(input_readers.BlobstoreLineInputReader):
    """A version of the BlobstoreLineInputReader that works with Mac, Windows and Linux line endings"""

    def __init__(self, blob_key, start_position, end_position):
        """Initializes this instance with the given blob key and character range.

        This BlobstoreInputReader will read from the first record starting after
        strictly after start_position until the first record ending at or after
        end_position (exclusive). As an exception, if start_position is 0, then
        this InputReader starts reading at the first record.

        Args:
          blob_key: the BlobKey that this input reader is processing.
          start_position: the position to start reading at.
          end_position: a position in the last record to read.
        """
        self._blob_key = blob_key
        self._blob_reader = UniversalNewLineBlobReader(blob_key,
            self._BLOB_BUFFER_SIZE,
            start_position)
        self._end_position = end_position
        self._has_iterated = False
        self._read_before_start = bool(start_position)
