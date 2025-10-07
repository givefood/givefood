from django.core.checks import Error
from django.conf import settings


def check_session_csrf_enabled(app_configs, **kwargs):
    errors = []
    if "session_csrf.CsrfMiddleware" not in settings.MIDDLEWARE_CLASSES:
        errors.append(Error(
            "SESSION_CSRF_DISABLED",
            hint="Please add 'session_csrf.CsrfMiddleware' to MIDDLEWARE_CLASSES",
        ))
    return errors


def check_cached_template_loader_used(app_configs, **kwargs):
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
            hint="Please use 'django.template.loaders.cached.Loader' for Django templates"
        )
        return [error]
