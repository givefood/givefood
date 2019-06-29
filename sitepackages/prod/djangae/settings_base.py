DEFAULT_FILE_STORAGE = 'djangae.storage.BlobstoreStorage'
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = (
    'djangae.storage.BlobstoreFileUploadHandler',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
)

DATABASES = {
    'default': {
        'ENGINE': 'djangae.db.backends.appengine'
    }
}

GENERATE_SPECIAL_INDEXES_DURING_TESTING = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'djangae': {
            'level': 'WARN'
        }
    }
}

EMAIL_BACKEND = 'djangae.mail.AsyncEmailBackend'

# Setting to * is OK, because GAE takes care of domain routing - setting it to anything
# else just causes unnecessary pain when something isn't accessible under a custom domain
ALLOWED_HOSTS = ("*",)

DJANGAE_RUNSERVER_IGNORED_FILES_REGEXES = ['^.+$(?<!\.py)(?<!\.yaml)(?<!\.html)']
# Note that these should match a directory name, not directory path:
DJANGAE_RUNSERVER_IGNORED_DIR_REGEXES = [r"^google_appengine$"]
