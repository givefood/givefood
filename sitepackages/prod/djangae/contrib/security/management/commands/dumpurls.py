import inspect
import functools
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.admindocs.views import simplify_regex
from djangae.contrib.security.commands_utils import (
    extract_views_from_urlpatterns,
    display_as_table,
    get_func_name,
    get_decorators,
    get_mixins,
    simplify_regex,
)


DEFAULT_IGNORED_MODULES = ['django', '__builtin__']


class Command(BaseCommand):
    args = "<module_to_ignore> <module_to_ignore> ..."
    help = "Displays all of the url matching routes for the project."

    def handle(self, *args, **options):
        ignored_modules = args if args else DEFAULT_IGNORED_MODULES
        views = []
        urlconf = __import__(settings.ROOT_URLCONF, {}, {}, [''])
        view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns, ignored_modules=ignored_modules)

        for (func, regex, url_name) in view_functions:
            # Extract real function from partial
            if isinstance(func, functools.partial):
                func = func.func

            decorators_and_mixins = get_decorators(func) + get_mixins(func, ignored_modules=ignored_modules)

            views.append("{url}||{module}||{decorators}".format(
                module='{0}.{1}'.format(func.__module__, get_func_name(func)),
                url=simplify_regex(regex),
                decorators=', '.join(decorators_and_mixins)
            ))

        info = (
            "Decorators lists are not comprehensive and do not take account of other patching.\n"
            "Decorators for methods of class-based views are not listed."
        )
        table = display_as_table(views)
        return "\n{0}\n{1}".format(table, info)
