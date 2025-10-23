import os

from pathlib import Path
from dotenv import load_dotenv
import sentry_sdk

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
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

sentry_sdk.init(
    dsn = os.getenv("SENTRY_DSN"),
    send_default_pii = True,
    traces_sample_rate = 1.0,
)

ALLOWED_HOSTS = [
    "localhost",
    "www.givefood.org.uk",
    "origin.givefood.org.uk",
    os.getenv("COOLIFY_FQDN"),
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    "bulma",
    "django_tasks",
    "django_tasks.backends.database",

    "gfadmin",
    "gfapi1",
    "gfapi2",
    "gfdash",
    "gfdumps",
    "gfoffline",
    "gfwfbn",
    "gfwrite",
    "gfapp",
    "gfauth",
    "givefood",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "givefood.middleware.LoginRequiredAccess",
    "givefood.middleware.OfflineKeyCheck",
    "givefood.middleware.RenderTime",
    "givefood.middleware.RedirectToWWW",
]

TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.database.DatabaseBackend"
    }
}

ROOT_URLCONF = "givefood.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "gfadmin.context_processors.gmap_keys",
                "givefood.context_processors.context",
            ],
        },
    },
]

WSGI_APPLICATION = "givefood.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASS"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": "5432",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField" 


# Password validation
# https://docs.djangoproject.com/en/{{ docs_version }}/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
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

STATIC_URL = "/static/"
STATIC_ROOT = os.path.abspath(os.path.join(BASE_DIR, "givefood", "static"))
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year
