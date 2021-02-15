import pipeline

from importlib import import_module
from mapreduce import context
from mapreduce import mapper_pipeline
from mapreduce.mapreduce_pipeline import MapreducePipeline
from mapreduce import pipeline_base
from mapreduce.model import MapreduceState
from mapreduce.input_readers import RawDatastoreInputReader, GoogleCloudStorageInputReader
from mapreduce import model
from pipeline.util import for_name

from django.utils import six
from djangae.contrib.processing.mapreduce.input_readers import DjangoInputReader

from utils import qualname

def import_callable(dotted_path):
    module_path = dotted_path.rsplit(".", 1)[0]
    while module_path:
        try:
            module = import_module(module_path)
            break
        except ImportError:
            module_path = module_path.rsplit(".", 1)[0]
            continue
    else:
        raise ImportError("Module not found in path: {}".format(dotted_path))

    remainder = dotted_path[len(module_path):].lstrip(".")
    remainder_parts = remainder.split(".")

    func = module
    while remainder_parts:
        next_step = remainder_parts[0]
        if not hasattr(func, next_step):
            raise ImportError("Couldn't find {} in module {}".format(next_step, module))
        func = getattr(func, next_step)
        remainder_parts = remainder_parts[1:]

    if not callable(func):
        raise ImportError("Specified path is not a callable: {}".format(dotted_path))

    return func

class MapperPipeline(mapper_pipeline.MapperPipeline):

    def finalized(self):
        mapreduce_id = self.outputs.job_id.value
        mapreduce_state = model.MapreduceState.get_by_job_id(mapreduce_id)
        params = mapreduce_state.mapreduce_spec.mapper.params
        finalized_func = params.get('_finalized', None)
        if not finalized_func:
            return None
        finalized_func = for_name(finalized_func)
        return finalized_func(job_name=self.args[0],
                              outputs=self.outputs,
                              *params.get('args', []),
                              **params.get('kwargs', {}))

def unpacker(obj):
    params = context.get().mapreduce_spec.mapper.params
    handler = import_callable(params["func"])
    yield handler(obj, *params["args"], **params["kwargs"])


def _do_map(
    input_reader, processor_func, finalize_func, params,
    _shards, _output_writer, _output_writer_kwargs, _job_name, _queue_name,
    *processor_args, **processor_kwargs):

    start_pipeline = processor_kwargs.pop('start_pipeline', True)

    handler_spec = qualname(unpacker)
    handler_params = {
        "func": qualname(processor_func) if callable(processor_func) else processor_func,
        "args": processor_args,
        "kwargs": processor_kwargs,
        "_finalized": qualname(finalize_func) if callable(finalize_func) else finalize_func
    }

    handler_params.update(params)

    new_pipeline = MapperPipeline(
        _job_name,
        handler_spec=handler_spec,
        input_reader_spec=qualname(input_reader),
        output_writer_spec=qualname(_output_writer) if _output_writer else None,
        params=handler_params,
        shards=_shards
    )

    if start_pipeline:
        new_pipeline.start(queue_name=_queue_name or 'default')

    return new_pipeline

def extract_options(kwargs, additional=None):
    VALID_OPTIONS = {
        "_shards",
        "_output_writer",
        "_output_writer_kwargs",
        "_job_name",
        "_queue_name",
    }

    options = {}

    for option in VALID_OPTIONS.union(additional or set()):
        if option in kwargs:
            options[option] = kwargs.pop(option)

    return options


def map_queryset(queryset, processor_func, *args, **kwargs):
    """
        Iterates over a queryset with mapreduce calling process_func for
        each Django instance. Calls finalize_func when the iteration completes.

        output_writer is optional, but should be a mapreduce OutputWriter
        subclass. Any additional args or kwargs are passed down to the
        handling function.

        Returns the pipeline.

        Valid additional options are (as kwargs):
            "finalize_func",
            "_shards",
            "_output_writer",
            "_output_writer_kwargs",
            "_job_name",
            "_queue_name",
    """
    options = extract_options(kwargs, additional={"finalize_func"})

    params = {
        'input_reader': DjangoInputReader.params_from_queryset(queryset),
        'output_writer': options.pop("_output_writer_kwargs", {}) or {}
    }

    finalize_func = options.pop("finalize_func", None)
    _shards = options.pop("_shards", None)
    _output_writer = options.pop("_output_writer", None)
    _output_writer_kwargs = params["output_writer"]
    _job_name = options.pop("_job_name", "Map task over {}".format(queryset.model))
    _queue_name = options.pop("_queue_name", None)

    return _do_map(
        DjangoInputReader,
        processor_func, finalize_func, params, _shards, _output_writer,
        _output_writer_kwargs,
        _job_name,
        _queue_name,
        *args, **kwargs
    )


def map_files(bucketname, processor_func, *args, **kwargs):
    """
        Iterates over files in cloudstorage matching patterns in filenames list.

        output_writer is optional, but should be a mapreduce OutputWriter
        subclass. Any additional args or kwargs are passed down to the
        handling function.

        Returns the pipeline

        Valid additional options are (as kwargs):
            "finalize_func",
            "filenames",
            "_shards",
            "_output_writer",
            "_output_writer_kwargs",
            "_job_name",
            "_queue_name",
    """

    options = extract_options(kwargs, additional={"filenames", "finalize_func"})

    filenames = options.pop("filenames", None)

    if filenames is None:
        filenames = ['*']

    params = {
        'input_reader': {
            GoogleCloudStorageInputReader.OBJECT_NAMES_PARAM: filenames,
            GoogleCloudStorageInputReader.BUCKET_NAME_PARAM: bucketname,
        },
        'output_writer': options.pop("_output_writer_kwargs", {}) or {}
    }

    finalize_func = options.pop("finalize_func", None)
    _shards = options.pop("_shards", None)
    _output_writer = options.pop("_output_writer", None)
    _output_writer_kwargs = params["output_writer"]
    _job_name = options.pop("_job_name", "Map task over files {} in {}".format(filenames, bucketname))
    _queue_name = options.pop("_queue_name", None)

    return _do_map(
        GoogleCloudStorageInputReader,
        processor_func, finalize_func, params, _shards, _output_writer,
        _output_writer_kwargs,
        _job_name,
        _queue_name,
        *args, **kwargs
    )


def map_entities(kind_name, namespace, processor_func, *args, **kwargs):
    """
        Iterates over all entities of a particular kind, calling processor_func
        on each one.
        Calls finalize_func when the iteration completes.

        output_writer is optional, but should be a mapreduce OutputWriter subclass
        _filters is an optional kwarg which will be passed directly to the input reader

        Returns the pipeline
    """
    options = extract_options(kwargs, additional={"finalize_func", "_filters"})

    params = {
        'input_reader': {
            RawDatastoreInputReader.ENTITY_KIND_PARAM: kind_name,
            RawDatastoreInputReader.NAMESPACE_PARAM: namespace,
            RawDatastoreInputReader.FILTERS_PARAM: options.pop("_filters", [])
        },
        'output_writer': options.pop("_output_writer_kwargs", {}) or {}
    }

    finalize_func = options.pop("finalize_func", None)
    _shards = options.pop("_shards", None)
    _output_writer = options.pop("_output_writer", None)
    _output_writer_kwargs = params["output_writer"]
    _job_name = options.pop("_job_name", "Map task over {}".format(kind_name))
    _queue_name = options.pop("_queue_name", None)

    return _do_map(
        RawDatastoreInputReader,
        processor_func, finalize_func, params, _shards, _output_writer,
        _output_writer_kwargs,
        _job_name,
        _queue_name,
        *args, **kwargs
    )


def map_reduce_queryset(queryset, map_func, reduce_func, output_writer, *args, **kwargs):

    """
        Does a complete map-shuffle-reduce over the queryset

        output_writer should be a mapreduce OutputWriter subclass

        Returns the pipeline
    """
    map_func = qualname(map_func)
    reduce_func = qualname(reduce_func)
    output_writer = qualname(output_writer)

    options = extract_options(kwargs)

    _shards = options.pop("_shards", None)
    _job_name = options.pop("_job_name", "Map reduce task over {}".format(queryset.model))
    _queue_name = options.pop("_queue_name", 'default')

    pipeline = MapreducePipeline(
        _job_name,
        map_func,
        reduce_func,
        qualname(DjangoInputReader),
        output_writer,
        mapper_params={
            "input_reader": DjangoInputReader.params_from_queryset(queryset),
        },
        reducer_params={
            'output_writer': options.pop("_output_writer_kwargs", {}) or {}
        },
        shards=_shards
    )
    pipeline.start(queue_name=_queue_name)
    return pipeline


def map_reduce_entities(kind_name, namespace, map_func, reduce_func, output_writer, *args, **kwargs):
    """
        Does a complete map-shuffle-reduce over the entities

        output_writer should be a mapreduce OutputWriter subclass
        _filters is an optional kwarg which will be passed directly to the input reader

        Returns the pipeline
    """
    map_func = qualname(map_func)
    reduce_func = qualname(reduce_func)
    output_writer = qualname(output_writer)

    options = extract_options(kwargs, additional={"_filters"})

    _shards = options.pop("_shards", None)
    _job_name = options.pop("_job_name", "Map reduce task over {}".format(kind_name))
    _queue_name = options.pop("_queue_name", 'default')

    pipeline = MapreducePipeline(
        _job_name,
        map_func,
        reduce_func,
        qualname(RawDatastoreInputReader),
        output_writer,
        mapper_params={
            'input_reader': {
                RawDatastoreInputReader.ENTITY_KIND_PARAM: kind_name,
                RawDatastoreInputReader.NAMESPACE_PARAM: namespace,
                RawDatastoreInputReader.FILTERS_PARAM: options.pop("_filters", [])
            },
        },
        reducer_params={
            'output_writer': options.pop("_output_writer_kwargs", {}) or {}
        },
        shards=_shards
    )
    pipeline.start(queue_name=_queue_name)
    return pipeline


def pipeline_has_finished(pipeline_id):
    """
        Returns True if the specified pipeline has finished
    """
    pipe = get_pipeline_by_id(pipeline_id)
    return pipe.has_finalized


def pipeline_in_progress(pipeline_id):
    """
        Returns True if the specified pipeline is in progress
    """
    return not pipeline_has_finished(pipeline_id)


def get_pipeline_by_id(pipeline_id):
    return pipeline.Pipeline.from_id(pipeline_id)


def get_mapreduce_state(pipeline):
    mapreduce_id = pipeline.outputs.job_id.value
    mapreduce_state = MapreduceState.get_by_job_id(mapreduce_id)
    return mapreduce_state
