import os
import re
from optparse import make_option

from django.core.management.commands.runserver import BaseRunserverCommand
from django.conf import settings

from datetime import datetime

from google.appengine.tools.devappserver2 import shutdown
from google.appengine.tools.sdk_update_checker import (
    GetVersionObject,
    _VersionList
)

DJANGAE_RUNSERVER_IGNORED_FILES_REGEXES = getattr(settings, "DJANGAE_RUNSERVER_IGNORED_FILES_REGEXES", [])
DJANGAE_RUNSERVER_IGNORED_DIR_REGEXES = getattr(settings, "DJANGAE_RUNSERVER_IGNORED_DIR_REGEXES", [])
if DJANGAE_RUNSERVER_IGNORED_FILES_REGEXES:
    DJANGAE_RUNSERVER_IGNORED_FILES_REGEXES = [re.compile(regex) for regex in DJANGAE_RUNSERVER_IGNORED_FILES_REGEXES]
if DJANGAE_RUNSERVER_IGNORED_DIR_REGEXES:
    DJANGAE_RUNSERVER_IGNORED_DIR_REGEXES = [re.compile(regex) for regex in DJANGAE_RUNSERVER_IGNORED_DIR_REGEXES]


def ignore_file(filename):
    """ Replacement for devappserver2.watchter_common.ignore_file
        - to be monkeypatched into place.
    """
    from google.appengine.tools.devappserver2 import watcher_common
    filename = os.path.basename(filename)
    return(
        filename.startswith(watcher_common._IGNORED_PREFIX) or
        any(filename.endswith(suffix) for suffix in watcher_common._IGNORED_FILE_SUFFIXES) or
        watcher_common._IGNORED_REGEX.match(filename) or
        any(regex.match(filename) for regex in DJANGAE_RUNSERVER_IGNORED_FILES_REGEXES)
    )


def skip_ignored_dirs(dirs):
    """ Replacement for devappserver2.watchter_common.skip_ignored_dirs
    - to be monkeypatched into place.
    """
    # Note that this function modifies the `dirs` list in place, it doesn't return anything.
    # Also note that `dirs` is a list of dir *names* not dir *paths*, which means that we can't
    # differentiate between /foo/bar and /moo/bar because we just get 'bar'. But allowing that
    # would require a whole load more monkey patching.
    from google.appengine.tools.devappserver2 import watcher_common
    watcher_common._remove_pred(dirs, lambda d: d.startswith(watcher_common._IGNORED_PREFIX))
    watcher_common._remove_pred(
        dirs,
        lambda d: any(regex.search(d) for regex in DJANGAE_RUNSERVER_IGNORED_DIR_REGEXES)
    )


class Command(BaseRunserverCommand):
    """
    Overrides the default Django runserver command.

    Instead of starting the default Django development server this
    command fires up a copy of the full fledged App Engine
    dev_appserver that emulates the live environment your application
    will be deployed to.
    """
    # We use this list to prevent user using certain dev_appserver options that
    # might collide with some Django settings.
    WHITELISTED_DEV_APPSERVER_OPTIONS = [
        'A',
        'admin_host',
        'admin_port',
        'auth_domain',
        'storage_path',
        'log_level',
        'max_module_instances',
        'use_mtime_file_watcher',
        'appidentity_email_address',
        'appidentity_private_key_path',
        'blobstore_path',
        'datastore_path',
        'clear_datastore',
        'datastore_consistency_policy',
        'require_indexes',
        'auto_id_policy',
        'logs_path',
        'show_mail_body',
        'enable_sendmail',
        'prospective_search_path',
        'clear_prospective_search',
        'search_indexes_path',
        'clear_search_indexes',
        'enable_task_running',
        'allow_skipped_files',
        'api_port',
        'dev_appserver_log_level',
        'skip_sdk_update_check',
        'default_gcs_bucket_name',
    ]

    def __new__(cls, *args, **kwargs):
        # We need to dynamically populate the `option_list` attribute
        # in order to Django allow extra parameters that we're going to pass
        # to GAE's `dev_appserver.py`
        instance = BaseRunserverCommand.__new__(cls, *args, **kwargs)
        sandbox_options = cls._get_sandbox_options()
        for option in sandbox_options:
            if option in cls.WHITELISTED_DEV_APPSERVER_OPTIONS:
                instance.option_list += (
                    make_option('--%s' % option, action='store', dest=option),
                )
        return instance

    @classmethod
    def _get_sandbox_options(cls):
        # We read the options from Djangae's sandbox
        from djangae import sandbox
        return [option for option in dir(sandbox._OPTIONS) if not option.startswith('_')]

    def handle(self, addrport='', *args, **options):
        from djangae import sandbox

        self.gae_options = {}
        sandbox_options = self._get_sandbox_options()

        # this way we populate the dictionary with the options that relevant
        # just for `dev_appserver.py`
        for option, value in options.items():
            if option in sandbox_options and value is not None:
                self.gae_options[option] = value

        super(Command, self).handle(addrport=addrport, *args, **options)

    def run(self, *args, **options):
        self.use_reloader = options.get("use_reloader")
        options["use_reloader"] = False
        return super(Command, self).run(*args, **options)

    def inner_run(self, *args, **options):
        import sys

        shutdown_message = options.get('shutdown_message', '')

        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'

        from djangae.environment import get_application_root
        from djangae.sandbox import _find_sdk_from_python_path
        from djangae.blobstore_service import stop_blobstore_service

        from django.conf import settings
        from django.utils import translation

        stop_blobstore_service()

        # Check for app.yaml
        expected_path = os.path.join(get_application_root(), "app.yaml")
        if not os.path.exists(expected_path):
            sys.stderr.write("Unable to find app.yaml at '%s'\n" % expected_path)
            sys.exit(1)

        self.stdout.write("Validating models...\n\n")
        self.check(display_num_errors=True)
        self.stdout.write((
            "%(started_at)s\n"
            "Django version %(version)s, using settings %(settings)r\n"
            "Starting development server at http://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "started_at": datetime.now().strftime('%B %d, %Y - %X'),
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": self._raw_ipv6 and '[%s]' % self.addr or self.addr,
            "port": self.port,
            "quit_command": quit_command,
        })
        sys.stdout.write("\n")
        sys.stdout.flush()

        # django.core.management.base forces the locale to en-us. We should
        # set it up correctly for the first request (particularly important
        # in the "--noreload" case).
        translation.activate(settings.LANGUAGE_CODE)

        # Will have been set by setup_paths
        sdk_path = _find_sdk_from_python_path()

        from google.appengine.tools.devappserver2 import devappserver2
        from google.appengine.tools.devappserver2 import python_runtime

        from djangae import sandbox

        # Add any additional modules specified in the settings
        additional_modules = getattr(settings, "DJANGAE_ADDITIONAL_MODULES", [])
        if additional_modules:
            sandbox._OPTIONS.config_paths.extend(additional_modules)

        if int(self.port) != sandbox._OPTIONS.port or additional_modules:
            # Override the port numbers
            sandbox._OPTIONS.port = int(self.port)
            sandbox._OPTIONS.admin_port = int(self.port) + len(additional_modules) + 1
            sandbox._OPTIONS.api_port = int(self.port) + len(additional_modules) + 2

        if self.addr != sandbox._OPTIONS.host:
            sandbox._OPTIONS.host = sandbox._OPTIONS.admin_host = sandbox._OPTIONS.api_host = self.addr

        # Extra options for `dev_appserver.py`
        for param, value in self.gae_options.items():
            setattr(sandbox._OPTIONS, param, value)

        # External port is a new flag introduced in 1.9.19
        current_version = _VersionList(GetVersionObject()['release'])
        if current_version >= _VersionList('1.9.19'):
            sandbox._OPTIONS.external_port = None

        sandbox._OPTIONS.automatic_restart = self.use_reloader

        if sandbox._OPTIONS.host == "127.0.0.1" and os.environ["HTTP_HOST"].startswith("localhost"):
            hostname = "localhost"
            sandbox._OPTIONS.host = "localhost"
        else:
            hostname = sandbox._OPTIONS.host

        os.environ["HTTP_HOST"] = "%s:%s" % (hostname, sandbox._OPTIONS.port)
        os.environ['SERVER_NAME'] = os.environ['HTTP_HOST'].split(':', 1)[0]
        os.environ['SERVER_PORT'] = os.environ['HTTP_HOST'].split(':', 1)[1]
        os.environ['DEFAULT_VERSION_HOSTNAME'] = '%s:%s' % (os.environ['SERVER_NAME'], os.environ['SERVER_PORT'])

        from google.appengine.api.appinfo import EnvironmentVariables

        class NoConfigDevServer(devappserver2.DevelopmentServer):
            def _create_api_server(self, request_data, storage_path, options, configuration):
                # sandbox._create_dispatcher returns a singleton dispatcher instance made in sandbox
                self._dispatcher = sandbox._create_dispatcher(configuration, options)
                # the dispatcher may have passed environment variables, it should be propagated
                env_vars = self._dispatcher._configuration.modules[0]._app_info_external.env_variables or EnvironmentVariables()
                for module in configuration.modules:
                    module_name = module._module_name
                    if module_name == 'default' or module_name is None:
                        module_settings = 'DJANGO_SETTINGS_MODULE'
                    else:
                        module_settings = '%s_DJANGO_SETTINGS_MODULE' % module_name
                    if module_settings in env_vars:
                        module_env_vars = module.env_variables or EnvironmentVariables()
                        module_env_vars['DJANGO_SETTINGS_MODULE'] = env_vars[module_settings]

                        old_env_vars = module._app_info_external.env_variables
                        new_env_vars = EnvironmentVariables.Merge(module_env_vars, old_env_vars)
                        module._app_info_external.env_variables = new_env_vars
                self._dispatcher._configuration = configuration
                self._dispatcher._port = options.port
                self._dispatcher._host = options.host

                self._dispatcher.request_data = request_data
                request_data._dispatcher = self._dispatcher

                sandbox._API_SERVER._host = options.api_host
                sandbox._API_SERVER.bind_addr = (options.api_host, options.api_port)

                from google.appengine.api import apiproxy_stub_map
                task_queue = apiproxy_stub_map.apiproxy.GetStub('taskqueue')
                # Make sure task running is enabled (it's disabled in the sandbox by default)
                if not task_queue._auto_task_running:
                    task_queue._auto_task_running = True
                    task_queue.StartBackgroundExecution()

                return sandbox._API_SERVER

        from google.appengine.tools.devappserver2 import module

        def fix_watcher_files(regex):
            """ Monkeypatch dev_appserver's file watcher to ignore any unwanted dirs or files. """
            from google.appengine.tools.devappserver2 import watcher_common
            watcher_common._IGNORED_REGEX = regex
            watcher_common.ignore_file = ignore_file
            watcher_common.skip_ignored_dirs = skip_ignored_dirs

        regex = sandbox._CONFIG.modules[0].skip_files
        if regex:
            fix_watcher_files(regex)

        def logging_wrapper(func):
            """
                Changes logging to use the DJANGO_COLORS settings
            """
            def _wrapper(level, format, *args, **kwargs):
                if args and len(args) == 1 and isinstance(args[0], dict):
                    args = args[0]
                    status = str(args.get("status", 200))
                else:
                    status = "200"

                try:
                    msg = format % args
                except UnicodeDecodeError:
                    msg += "\n" # This is what Django does in WSGIRequestHandler.log_message

                # Utilize terminal colors, if available
                if status[0] == '2':
                    # Put 2XX first, since it should be the common case
                    msg = self.style.HTTP_SUCCESS(msg)
                elif status[0] == '1':
                    msg = self.style.HTTP_INFO(msg)
                elif status == '304':
                    msg = self.style.HTTP_NOT_MODIFIED(msg)
                elif status[0] == '3':
                    msg = self.style.HTTP_REDIRECT(msg)
                elif status == '404':
                    msg = self.style.HTTP_NOT_FOUND(msg)
                elif status[0] == '4':
                    # 0x16 = Handshake, 0x03 = SSL 3.0 or TLS 1.x
                    if status.startswith(str('\x16\x03')):
                        msg = ("You're accessing the development server over HTTPS, "
                            "but it only supports HTTP.\n")
                    msg = self.style.HTTP_BAD_REQUEST(msg)
                else:
                    # Any 5XX, or any other response
                    msg = self.style.HTTP_SERVER_ERROR(msg)

                return func(level, msg)
            return _wrapper

        module.logging.log = logging_wrapper(module.logging.log)

        python_runtime._RUNTIME_PATH = os.path.join(sdk_path, '_python_runtime.py')
        python_runtime._RUNTIME_ARGS = [sys.executable, python_runtime._RUNTIME_PATH]

        dev_server = NoConfigDevServer()

        try:
            dev_server.start(sandbox._OPTIONS)
            try:
                shutdown.wait_until_shutdown()
            except KeyboardInterrupt:
                pass
        finally:
            dev_server.stop()


        if shutdown_message:
            sys.stdout.write(shutdown_message)

        return
