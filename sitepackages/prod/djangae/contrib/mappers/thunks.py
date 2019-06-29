from mapreduce import context
from pipeline.util import for_name


def thunk_map(x):
    """
        This is the default map function that wraps the static map function.

        It allows you to pass args and kwargs to your map function for defining
        more dynamic mappers
    """
    ctx = context.get()
    params = ctx.mapreduce_spec.mapper.params
    map_func = params.get('_map', None)
    args = params.get('args', [])
    kwargs = params.get('kwargs', {})
    map_func = for_name(map_func)
    return map_func(x, *args, **kwargs)
