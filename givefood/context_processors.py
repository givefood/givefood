import os, sys
from django.urls import resolve, translate_url
from givefood.settings import LANGUAGES
from django.utils.translation import get_language_info


from givefood.const.general import ENABLE_WRITE, SITE_DOMAIN, FACEBOOK_LOCALES

def context(request):

    HASH_CHARS = 7

    language_code = request.LANGUAGE_CODE
    language_name = get_language_info(language_code)['name_local']
    language_direction = "rtl" if get_language_info(language_code)['bidi'] else "ltr"
    language_direction_arrow = "←" if language_direction == "rtl" else "→"

    path = request.path
    translated_path = translate_url(path, language_code)
    canonical_path = "%s%s" % (SITE_DOMAIN, translated_path)
    querystring = request.META['QUERY_STRING']

    if os.environ.get('COOLIFY_CONTAINER_NAME'):
        instance_id = os.environ.get('COOLIFY_CONTAINER_NAME')[:HASH_CHARS]
    else:
        instance_id = "LOCALHOST"
    if os.environ.get('SOURCE_COMMIT'):
        version = os.environ.get('SOURCE_COMMIT')[:HASH_CHARS]
    else:
        version = "LOCALHOST"
    facebook_locale = FACEBOOK_LOCALES.get(language_code, "en_GB")

    TRANSLATEABLE_TEST_LANG = "cy"
    page_translatable = "/%s/" % TRANSLATEABLE_TEST_LANG == translate_url(path, TRANSLATEABLE_TEST_LANG)[:4]
    
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
        'language_code': language_code,
        'language_name': language_name,
        'language_direction': language_direction,
        'language_direction_arrow': language_direction_arrow,
        'facebook_locale': facebook_locale,
    }

    return context
