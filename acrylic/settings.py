"""
Django settings for acrylic project.
"""
import os
from datetime import timedelta
from decouple import config
import django_heroku
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-i7!0w_w7d=x+h*v@n)_lr)_onr!5(la3-1wzca=6mz^_jl0^em'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['dev.platform.acrylic.la', 'platform.acrylic.la']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    # 3rd. party apps
    'django_countries',
    'taggit',
    'drf_spectacular',
    'rest_framework',
    'django_filters',
    'social_django',  # django social auth
    'rest_social_auth',
    'rest_framework_simplejwt',
    # project apps
    'common',
    'account',
    'artist',
    'legal',
    'catalog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    's3file.middleware.S3FileMiddleware',
    #'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'acrylic.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'acrylic.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# https://medium.com/@bfirsh/squeezing-every-drop-of-performance-out-of-a-django-app-on-heroku-4b5b1e5a3d44

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 
# https://github.com/jneight/django-db-geventpool

DATABASES['OPTIONS'] = {
    'MAX_CONNS': 4,
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# django-tagging
FORCE_LOWERCASE_TAGS = True


REST_FRAMEWORK = {
    # YOUR SETTINGS
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'Acrylic API',
    'DESCRIPTION': 'Acrylic Platform API',
    'VERSION': '1.0',
    'SERVE_INCLUDE_SCHEMA': True,
    'SCHEMA_PATH_PREFIX': r'^/api/v[0-9]',
    'SCHEMA_PATH_PREFIX_TRIM': True,
    'SERVERS': [
        #{'url': 'https://dev.platform.acrylic.la/api/v1/', 'description': 'Development'},
        {'url': 'https://platform.acrylic.la/api/v1/', 'description': 'Production'},
    ]
    #'SERVERS': [{'url': 'http://127.0.0.1:8000/api/v1/', 'description': 'Development'},]
    
    # OTHER SETTINGS
    
}


# prevent whitenoise: prevent Django throwing an error for references of static files which don't exist
WHITENOISE_MANIFEST_STRICT = False

FRONTEND_BASE_URL = 'https://app.acrylic.la/'

REST_REGISTRATION = {
    # user profile
    'PROFILE_SERIALIZER_CLASS': 'account.serializers.UserProfileSerializer',
    # user registration
    'REGISTER_SERIALIZER_CLASS': 'artist.serializers.RegisterArtistSerializer',
    'REGISTER_OUTPUT_SERIALIZER_CLASS': 'account.serializers.UserProfileSerializer',


    'REGISTER_VERIFICATION_URL': f'{FRONTEND_BASE_URL}verify-user/',
    'RESET_PASSWORD_VERIFICATION_URL': f'{FRONTEND_BASE_URL}reset-password/',
    'REGISTER_EMAIL_VERIFICATION_URL': f'{FRONTEND_BASE_URL}verify-email/',
    'VERIFICATION_FROM_EMAIL': 'no-reply@acrylic.la',
}

# JWT auth settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}


# SSL/TLS settings
#SECURE_SSL_REDIRECT = True
#SESSION_COOKIE_SECURE = True
#CSRF_COOKIE_SECURE = True

# Dropbox Sign
DROPBOX_SIGN_API_KEY = config('DROPBOX_SIGN_API_KEY', default='')


# Activate Django-Heroku.
django_heroku.settings(locals())

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=config('SENTRY_DSN', default=''),
    integrations=[DjangoIntegration()],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)
