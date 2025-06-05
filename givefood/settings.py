import os, logging

from pathlib import Path
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/{{ docs_version }}/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

APPEND_SLASH = True

TEMPLATE_DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

ALLOWED_HOSTS = [
    "localhost",
    "www.givefood.org.uk",
    "origin.givefood.org.uk",
    os.getenv("COOLIFY_FQDN"),
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'cspreports',
    'bulma',

    'gfadmin',
    'gfapi1',
    'gfapi2',
    'gfdash',
    'gfoffline',
    'gfwfbn',
    'gfwrite',
    'gfapp',
    'gfauth',
    'givefood',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'csp.middleware.CSPMiddleware',
    'givefood.middleware.LoginRequiredAccess',
    'givefood.middleware.OfflineKeyCheck',
    'givefood.middleware.RenderTime',
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
                'django.template.context_processors.i18n',
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASS"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': '5432',
    }
}
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField' 


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


# Internationalization

LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = False
LANGUAGE_BIDI = True

LANGUAGES = [
    ("en", "English"),
    ("cy", "Cymraeg"),
    ("gd", "Gàidhlig"),
    ("ga", "Gaeilge"),
    ("pl", "Polski"),
    ("ro", "Română"),
    ("pa", "ਪੰਜਾਬੀ"),
    ("ur", "اردو"),
    ("pt", "Português"),
    ("es", "Español"),
    ("ar", "العربية"),
]

LOCALE_PATHS = (
    os.path.abspath(os.path.join(BASE_DIR, "locale")),
)



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/{{ docs_version }}/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.abspath(os.path.join(BASE_DIR, "givefood", "static"))
WHITENOISE_MAX_AGE = 60 * 60 * 24

# CSP Configuration
# https://django-csp.readthedocs.io/en/latest/configuration.html

CSP_REPORT_ONLY = True

# sensible default CSP settings, feel free to modify them
CSP_DEFAULT_SRC = ("'self'", "*.gstatic.com", "syndication.twitter.com")
# Inline styles are unsafe, but Django error pages use them. We later remove
# `unsafe-inline` in settings_live.py
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com", "*.gstatic.com", "cdnjs.cloudflare.com", "platform.twitter.com", "ton.twimg.com", "*.foodbank.org.uk", "accounts.google.com")
CSP_FONT_SRC = ("'self'", "themes.googleusercontent.com", "*.gstatic.com", "maps.googleapis.com")
CSP_FRAME_SRC = ("'self'", "*")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'", "*.googleanalytics.com", "*.google-analytics.com", "ajax.googleapis.com", "*.cloudflare.com", "www.gstatic.com", "www.googletagmanager.com", "maps.googleapis.com", "connect.facebook.net", "platform.twitter.com", "cdn.syndication.twimg.com", "syndication.twitter.com", "www.googleadservices.com", "googleads.g.doubleclick.net", "plausible.io", "*.clarity.ms", "c.bing.com", "static.cloudflareinsights.com", "instant.page", "ratings.food.gov.uk", "accounts.google.com")
CSP_IMG_SRC = ("'self'", "data:", "s.ytimg.com", "*.googleusercontent.com", "*.gstatic.com", "*.google-analytics.com", "www.googletagmanager.com", "abs.twimg.com", "platform.twitter.com", "syndication.twitter.com", "pbs.twimg.com", "ton.twimg.com", "digitalcontent.api.tesco.com", "*.googleapis.com", "storage.googleapis.com", "www.google.com", "www.google.co.uk", "assets.sainsburys-groceries.co.uk", "*.ggpht.com", "googleads.g.doubleclick.net", "*.clarity.ms", "c.bing.com", "photos.givefood.org.uk", "ratings.food.gov.uk")
CSP_CONNECT_SRC = ("'self'", "*.google-analytics.com", "maps.googleapis.com", "stats.g.doubleclick.net", "plausible.io", "*.clarity.ms", "c.bing.com", "api.ratings.food.gov.uk")
