import os, sys
from django.urls import resolve, translate_url
from givefood.settings.default import LANGUAGES

from givefood.const.general import ENABLE_WRITE, SITE_DOMAIN

def context(request):

    language = request.LANGUAGE_CODE
    path = request.path
    translated_path = translate_url(path, language)
    canonical_path = "%s%s" % (SITE_DOMAIN, translated_path)
    querystring = request.META['QUERY_STRING']
    instance_id = os.environ.get('GAE_INSTANCE')
    version = os.environ.get('GAE_VERSION')

    page_translatable = "/cy/" == translate_url(path, "cy")[:4]
    languages = []
    for language in LANGUAGES:
        url = translate_url(path, language[0])
        if querystring:
            url = "%s?%s" % (url, querystring)
        languages.append({
            'code': language[0],
            'name': language[1],
            'url': url,
        })

    flag_path = canonical_path
    if querystring:
        flag_path = "%s?%s" % (canonical_path, querystring)

    try:
        app_name = sys.modules[resolve(request.path_info).func.__module__].__package__
    except:
        app_name = "unknown"


    context = {
        'canonical_path': canonical_path,
        'flag_path': flag_path,
        'instance_id': instance_id,
        'version': version,
        'enable_write': ENABLE_WRITE,
        'app_name': app_name,
        'domain': SITE_DOMAIN,
        'page_translatable': page_translatable,
        'languages': languages,
    }

    return context
