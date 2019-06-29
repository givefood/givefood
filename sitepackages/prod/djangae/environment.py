import os
from djangae.utils import memoized


def application_id():
    from google.appengine.api import app_identity

    try:
        result = app_identity.get_application_id()
    except AttributeError:
        result = None

    if not result:
        # Apparently we aren't running live, probably inside a management command
        from google.appengine.api import appinfo

        info = appinfo.LoadSingleAppInfo(open(os.path.join(get_application_root(), "app.yaml")))

        result = "dev~" + info.application
        os.environ['APPLICATION_ID'] = result
        result = app_identity.get_application_id()

    return result


def sdk_is_available():
    try:
        from google.appengine.api import apiproxy_stub_map
        apiproxy_stub_map  # Silence pylint
        return True
    except ImportError:
        return False


def is_production_environment():
    return not is_development_environment()


def is_development_environment():
    return 'SERVER_SOFTWARE' not in os.environ or os.environ['SERVER_SOFTWARE'].startswith("Development")


def datastore_is_available():
    if not sdk_is_available():
        return False

    from google.appengine.api import apiproxy_stub_map
    return bool(apiproxy_stub_map.apiproxy.GetStub('datastore_v3'))


def is_in_task():
    "Returns True if the request is a task, False otherwise"
    return bool(task_name())


def is_in_cron():
    "Returns True if the request is in a cron, False otherwise"
    return bool(os.environ.get("HTTP_X_APPENGINE_CRON"))


def task_name():
    "Returns the name of the current task if any, else None"
    return os.environ.get("HTTP_X_APPENGINE_TASKNAME")


def task_retry_count():
    "Returns the task retry count, or None if this isn't a task"
    try:
        return int(os.environ.get("HTTP_X_APPENGINE_TASKRETRYCOUNT"))
    except (TypeError, ValueError):
        return None


def task_queue_name():
    "Returns the name of the current task queue (if this is a task) else None"
    if "HTTP_X_APPENGINE_QUEUENAME" in os.environ:
        return os.environ["HTTP_X_APPENGINE_QUEUENAME"]
    else:
        return None


@memoized
def get_application_root():
    """Traverse the filesystem upwards and return the directory containing app.yaml"""
    path = os.path.dirname(os.path.abspath(__file__))
    app_yaml_path = os.environ.get('DJANGAE_APP_YAML_LOCATION', None)

    # If the DJANGAE_APP_YAML_LOCATION variable is setup, will try to locate
    # it from there.
    if (app_yaml_path is not None and
            os.path.exists(os.path.join(app_yaml_path, "app.yaml"))):
        return app_yaml_path

    # Failing that, iterates over the parent folders until it finds it,
    # failing when it gets to the root
    while True:
        if os.path.exists(os.path.join(path, "app.yaml")):
            return path
        else:
            parent = os.path.dirname(path)
            if parent == path:  # Filesystem root
                break
            else:
                path = parent

    raise RuntimeError("Unable to locate app.yaml. Did you add it to skip_files?")
