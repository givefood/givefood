import os, logging

from pathlib import Path
from djangae.contrib.secrets import get
from djangae.environment import project_id
from djangae.settings_base import *  # noqa

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/{{ docs_version }}/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get().secret_key

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'djangae',
    'djangae.tasks',
    'djangae.contrib.googleauth',
    'djangae.contrib.security',

    'cspreports',
    'bulma',

    'gfadmin',
    'gfapi1',
    'gfapi2',
    'gfdash',
    'gfoffline',
    'gfwfbn',
    'gfwrite',
    'givefood',
]

MIDDLEWARE = [
    'djangae.contrib.common.middleware.RequestStorageMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'djangae.contrib.googleauth.middleware.LocalIAPLoginMiddleware',
    'djangae.contrib.googleauth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',
]

ROOT_URLCONF = 'givefood.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "gfadmin.context_processors.all_foodbanks",
                "gfadmin.context_processors.gmap_keys",
                "givefood.context_processors.context",
            ],
            'libraries':{
                'product_image': 'givefood.templatetags.custom_tags',
            },
        },
    },
]

WSGI_APPLICATION = 'givefood.wsgi.application'


# Database
# https://docs.djangoproject.com/en/{{ docs_version }}/ref/settings/#databases

DATASTORE_INDEX_YAML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "dsindex.yaml"
)

DATABASES = {
    'default': {
        'ENGINE': 'gcloudc.db.backends.datastore',
        'PROJECT': project_id(default='givefood'),
        'INDEXES_FILE': DATASTORE_INDEX_YAML,
    }
}


# Password validation
# https://docs.djangoproject.com/en/{{ docs_version }}/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Enable the Djangae IAP backend, but not Django's username/password one by default
AUTHENTICATION_BACKENDS = (
    "djangae.contrib.googleauth.backends.iap.IAPBackend",
)

AUTH_USER_MODEL = 'googleauth.User'


# Internationalization
# https://docs.djangoproject.com/en/{{ docs_version }}/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/{{ docs_version }}/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.abspath(os.path.join(BASE_DIR, "static"))

# Djangae Specific settings

# Set this to the location where your app is deployed.
# Available on the App Engine dashboard.
CLOUD_TASKS_LOCATION = "europe-west"


# CSP Configuration
# https://django-csp.readthedocs.io/en/latest/configuration.html

CSP_REPORT_ONLY = True

# sensible default CSP settings, feel free to modify them
CSP_DEFAULT_SRC = ("'self'", "*.gstatic.com", "syndication.twitter.com")
# Inline styles are unsafe, but Django error pages use them. We later remove
# `unsafe-inline` in settings_live.py
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com", "*.gstatic.com", "cdnjs.cloudflare.com", "platform.twitter.com", "ton.twimg.com", "cdn.jsdelivr.net")
CSP_FONT_SRC = ("'self'", "themes.googleusercontent.com", "*.gstatic.com", "maps.googleapis.com")
CSP_FRAME_SRC = ("'self'", "*")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'", "instant.page", "*.googleanalytics.com", "*.google-analytics.com", "ajax.googleapis.com", "cdnjs.cloudflare.com", "www.gstatic.com", "www.googletagmanager.com", "maps.googleapis.com", "connect.facebook.net","platform.twitter.com", "cdn.syndication.twimg.com", "syndication.twitter.com", "www.googleadservices.com", "googleads.g.doubleclick.net", "plausible.io", "*.clarity.ms", "c.bing.com", "*.cookiepro.com", "www.paypalobjects.com")
CSP_IMG_SRC = ("'self'", "data:", "s.ytimg.com", "*.googleusercontent.com", "*.gstatic.com", "www.google-analytics.com", "www.googletagmanager.com", "abs.twimg.com", "platform.twitter.com", "syndication.twitter.com", "pbs.twimg.com", "ton.twimg.com", "digitalcontent.api.tesco.com", "*.googleapis.com", "storage.googleapis.com", "www.google.com", "www.google.co.uk", "assets.sainsburys-groceries.co.uk", "*.ggpht.com", "googleads.g.doubleclick.net", "*.clarity.ms", "c.bing.com", "*.cookiepro.com", "www.paypalobjects.com")
CSP_CONNECT_SRC = ("'self'", "www.google-analytics.com", "maps.googleapis.com", "stats.g.doubleclick.net", "plausible.io", "*.clarity.ms", "c.bing.com", "*.cookiepro.com", "*.onetrust.com")
