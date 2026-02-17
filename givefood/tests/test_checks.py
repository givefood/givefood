from django.test import override_settings

from givefood.checks import check_session_csrf_enabled


@override_settings(MIDDLEWARE=["session_csrf.CsrfMiddleware"])
def test_check_session_csrf_enabled_when_middleware_present():
    assert check_session_csrf_enabled(None) == []


@override_settings(MIDDLEWARE=[])
def test_check_session_csrf_enabled_when_middleware_missing():
    errors = check_session_csrf_enabled(None)
    assert len(errors) == 1
    assert errors[0].msg == "SESSION_CSRF_DISABLED"
    assert errors[0].hint == (
        "Please add 'session_csrf.CsrfMiddleware' to MIDDLEWARE"
    )
