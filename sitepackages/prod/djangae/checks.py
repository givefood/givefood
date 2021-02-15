import os
from django import VERSION
from django.conf import settings
from django.core.checks import register, Tags, Error, Warning

from djangae.environment import get_application_root

try:
    # `sdk_update_checker` only exists in the development SDK
    from google.appengine.tools.sdk_update_checker import GetVersionObject, _VersionList
except ImportError:
    GetVersionObject = None


# django 1.8 didn't declare a "caches" tag
if not hasattr(Tags, "caches"):
    Tags.caches = "caches"
    Tags.urls = "urls"


MAX_APP_ENGINE_SDK_VERSION = (1, 9, 57)

CSP_SOURCE_NAMES = [
    'CSP_DEFAULT_SRC',
    'CSP_SCRIPT_SRC',
    'CSP_IMG_SRC',
    'CSP_OBJECT_SRC',
    'CSP_MEDIA_SRC',
    'CSP_FRAME_SRC',
    'CSP_FONT_SRC',
    'CSP_STYLE_SRC',
    'CSP_CONNECT_SRC',
]


@register
def check_app_engine_sdk_version(app_configs=None, **kwargs):
    errors = []
    if GetVersionObject:
        sdk_version = tuple(_VersionList(GetVersionObject()['release']))
        if sdk_version > MAX_APP_ENGINE_SDK_VERSION:
            errors.append(Warning(
                "MAX_APP_ENGINE_SDK_VERSION",
                hint="You are using a version of the App Engine SDK that is not yet supported",
                id='djangae.W002',
            ))
    return errors


@register(Tags.security)
def check_session_csrf_enabled(app_configs=None, **kwargs):
    errors = []

    # Django 1.11 has built-in session-based CSRF tokens, so if that's enabled
    # we don't need to check for the mozilla version
    if VERSION > (1, 11) and getattr(settings, "CSRF_USE_SESSIONS", False):
        return []

    # Django >= 1.10 has a MIDDLEWARE setting, which is None by default. Convert
    # it to a list, it might be a tuple.
    middleware = list(getattr(settings, 'MIDDLEWARE', []) or [])
    middleware.extend(getattr(settings, 'MIDDLEWARE_CLASSES', []))

    if 'session_csrf.CsrfMiddleware' not in middleware:
        errors.append(Error(
            "SESSION_CSRF_DISABLED",
            hint="Please add 'session_csrf.CsrfMiddleware' to MIDDLEWARE_CLASSES",
            id='djangae.E001',
        ))
    return errors


@register(Tags.security)
def check_csp_is_not_report_only(app_configs=None, **kwargs):
    errors = []
    if getattr(settings, "CSP_REPORT_ONLY", False):
        errors.append(Error(
            "CSP_REPORT_ONLY_ENABLED",
            hint="Please set 'CSP_REPORT_ONLY' to False",
            id='djangae.E002',
        ))
    return errors


@register(Tags.security, deploy=True)
def check_csp_sources_not_unsafe(app_configs=None, **kwargs):
    errors = []
    for csp_src_name in CSP_SOURCE_NAMES:
        csp_src_values = getattr(settings, csp_src_name, [])
        if "'unsafe-inline'" in csp_src_values or "'unsafe-eval'" in csp_src_values:
            errors.append(Error(
                csp_src_name + "_UNSAFE",
                hint="Please remove 'unsafe-inline'/'unsafe-eval' from your CSP policies",
                id='djangae.E1%02d' % CSP_SOURCE_NAMES.index(csp_src_name),
            ))
    return errors


@register(Tags.caches, deploy=True)
def check_cached_template_loader_used(app_configs=None, **kwargs):
    """ Ensure that the cached template loader is used for Django's template system. """
    for template in settings.TEMPLATES:
        if template['BACKEND'] != "django.template.backends.django.DjangoTemplates":
            continue
        loaders = template['OPTIONS'].get('loaders', [])
        for loader_tuple in loaders:
            if loader_tuple[0] == 'django.template.loaders.cached.Loader':
                return []
        error = Error(
            "CACHED_TEMPLATE_LOADER_NOT_USED",
            hint="Please use 'django.template.loaders.cached.Loader' for Django templates",
            id='djangae.E003',
        )
        return [error]
    return []


@register(Tags.urls)
def check_deferred_builtin(app_configs=None, **kwargs):
    """
    Check that the deferred builtin is switched off, as it'll override Djangae's deferred handler
    """
    from google.appengine.tools.devappserver2.application_configuration import ModuleConfiguration

    app_yaml_path = os.path.join(get_application_root(), "app.yaml")
    config = ModuleConfiguration(app_yaml_path)
    errors = []

    for handler in config.handlers:
        if handler.url == '/_ah/queue/deferred':
            if handler.script == 'google.appengine.ext.deferred.application':
                errors.append(
                    Warning(
                        "Deferred builtin is switched on. This overrides Djangae's deferred handler",
                        hint='Remove deferred builtin from app.yaml',
                        id='djangae.W001'
                    )
                )
            break

    return errors
