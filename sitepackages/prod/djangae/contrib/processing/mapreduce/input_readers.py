from mapreduce import input_readers
from djangae.utils import get_in_batches
from django.apps import apps
from django.utils.six.moves import range
import logging
import cPickle

class DjangoInputReader(input_readers.InputReader):

    # Use same batch size as mapreduce's built-in DatastoreInputReader
    _BATCH_SIZE = 50

    """
    """
    def __init__(self, model_path=None, pk__gt=None, pk__lte=None, pk_last_read=None, query=None, shard_id=None, db='default'):
        self.model_path = model_path
        try:
            app, model = self.model_path.split('.')
        except ValueError:
            app, model = self.model_path.split(',')
        self.model = apps.get_model(app, model)
        self.pk__gt = pk__gt
        self.pk__lte = pk__lte
        self.pk_last_read = pk_last_read
        self.query = query
        self.shard_id = shard_id
        self.db = db

    def __iter__(self):
        pk_filters = {}
        if self.pk__gt is not None:
            pk_filters['pk__gt'] = self.pk__gt
        if self.pk__lte is not None:
            pk_filters['pk__lte'] = self.pk__lte

        if self.pk_last_read is not None:
            pk_filters['pk__gt'] = max(self.pk_last_read, pk_filters.get('pk__gt', self.pk_last_read))

        qs = self.model.objects.all()
        if self.query is not None:
            qs.query = self.query
        qs = qs.using(self.db).filter(**pk_filters).order_by('pk')

        for model in get_in_batches(qs, batch_size=self._BATCH_SIZE):
            # From the mapreduce docs (AbstractDatastoreInputReader):
            #     The caller must consume yielded values so advancing the KeyRange
            #     before yielding is safe.
            self.pk_last_read = model.id
            yield model

    @classmethod
    def from_json(cls, input_shard_state):
        """
        """
        query = input_shard_state.pop('query')
        input_shard_state['query'] = cPickle.loads(str(query))
        return cls(**input_shard_state)

    def to_json(self):
        """
        """
        return {
            'model_path': self.model_path,
            'pk__gt': self.pk__gt,
            'pk__lte': self.pk__lte,
            'pk_last_read': self.pk_last_read,
            'query': cPickle.dumps(self.query),
            'shard_id': self.shard_id,
            'db': self.db
        }

    @classmethod
    def split_input(cls, mapper_spec):
        """
        """
        params = input_readers._get_params(mapper_spec)
        db = params.get('db', None)
        try:
            app, model = params['model'].split('.')
        except ValueError:
            app, model = params['model'].split(',')
        model = apps.get_model(app, model)
        query = params.get('query', None)
        if query is not None:
            # FIXME why we have to cast to a str here? comes back as unicode
            query = cPickle.loads(str(query))

        shard_count = mapper_spec.shard_count
        if db:
            scatter_query = model.objects.using(db)
        else:
            scatter_query = model.objects

        scatter_query = scatter_query.all()
        scatter_query = scatter_query.values_list('pk').order_by('__scatter__')
        oversampling_factor = 32
        # FIXME values
        keys = [x[0] for x in scatter_query[:shard_count * oversampling_factor]]
        keys.sort()

        if len(keys) > shard_count:
            keys = cls._choose_split_points(keys, shard_count)
        keyranges = []
        if len(keys) > 1:
            keyranges.append(DjangoInputReader(params['model'], pk__lte=keys[0], query=query, shard_id=0, db=db))
            for x in range((len(keys) - 1)):
                keyranges.append(DjangoInputReader(params['model'], pk__gt=keys[x], pk__lte=keys[x+1], query=query, shard_id=x+1, db=db))
            keyranges.append(DjangoInputReader(params['model'], pk__gt=keys[x+1], query=query, shard_id=x+2, db=db))
        elif len(keys) == 1:
            keyranges.append(DjangoInputReader(params['model'], pk__lte=keys[0], query=query, shard_id=0, db=db))
            keyranges.append(DjangoInputReader(params['model'], pk__gt=keys[0], query=query, shard_id=1, db=db))
        else:
            keyranges.append(DjangoInputReader(params['model'], query=query, shard_id=0, db=db))
        return keyranges

    @classmethod
    def _choose_split_points(cls, sorted_keys, shard_count):
        """
        Returns the best split points given a random set of datastore.Keys.
        """
        assert len(sorted_keys) >= shard_count
        index_stride = len(sorted_keys) / float(shard_count)
        return [sorted_keys[int(round(index_stride * i))] for i in range(1, shard_count)]

    @staticmethod
    def params_from_queryset(queryset):
        """
        Returns a formated dictionary for use in the handler dict
        """
        return {
            'model': '{}.{}'.format(queryset.model._meta.app_label, queryset.model.__name__),
            'query': cPickle.dumps(queryset.query),
            'db': queryset._db
        }
#
