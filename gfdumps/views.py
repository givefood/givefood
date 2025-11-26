from datetime import date
from django.views.decorators.cache import cache_page
from django.shortcuts import render
from django.http import HttpResponse, Http404

from givefood.const.cache_times import SECONDS_IN_DAY, SECONDS_IN_HOUR
from givefood.models import Dump


def dump_index(request):
    dump_types = Dump.objects.values_list('dump_type', flat=True).distinct().order_by('dump_type')

    template_vars = {
        "dump_types": dump_types,
        "stage":"index",
    }
    return render(request, "gfdumps/dumps.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def dump_type(request, dump_type):
    dump_formats = Dump.objects.filter(dump_type=dump_type).values_list('dump_format', flat=True).distinct().order_by('dump_format')

    template_vars = {
        "dump_type": dump_type,
        "dump_formats": dump_formats,
        "stage":"types",
    }
    return render(request, "gfdumps/dumps.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def dump_format(request, dump_type, dump_format):
    dumps = Dump.objects.filter(dump_type=dump_type, dump_format=dump_format).order_by('-created').only('id', 'dump_type', 'dump_format', 'created')

    template_vars = {
        "dump_type": dump_type,
        "dump_format": dump_format,
        "dumps": dumps,
        "stage":"format",
    }
    return render(request, "gfdumps/dumps.html", template_vars)


@cache_page(SECONDS_IN_HOUR)
def dump_latest(request, dump_type, dump_format):

    latest_dump = Dump.objects.filter(dump_type=dump_type, dump_format=dump_format).order_by('-created').defer('the_dump').first()
    return dump_serve(request, dump_type, dump_format, latest_dump.created.year, latest_dump.created.month, latest_dump.created.day)


@cache_page(SECONDS_IN_DAY)
def dump_serve(request, dump_type, dump_format, year=None, month=None, day=None):
    """
    Serve a dump file, either the latest or a specific date
    """
    if year and month and day:
        dump_date = date(year, month, day)
        dump_instance = Dump.objects.filter(dump_type=dump_type, dump_format=dump_format, created__date=dump_date).first()
    else:
        dump_instance = Dump.objects.filter(dump_type=dump_type, dump_format=dump_format).order_by('-created').first()

    if not dump_instance:
        raise Http404("Dump not found")

    # Set content type based on dump format
    if dump_format == 'json':
        content_type = 'application/json'
    elif dump_format == 'xml':
        content_type = 'application/xml'
    else:
        content_type = 'text/csv'

    response = HttpResponse(dump_instance.the_dump, content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename="%s"' % (
        dump_instance.file_name(),
    )
    return response
