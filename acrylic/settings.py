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

ADMINS = [
    ('Antonio Melé', 'antonio.mele@zenxit.com',),
]

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-i7!0w_w7d=x+h*v@n)_lr)_onr!5(la3-1wzca=6mz^_jl0^em'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['dev.platform.acrylic.la', 'platform.acrylic.la']


# Application definition

INSTALLED_APPS = [
    'common',
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
    'django_ses',
    'corsheaders',
    'import_export',
    'sorl.thumbnail',
    # project apps
    'account',
    'artist',
    'content',
    'legal',
    'catalog',
    'chartmetric',
    'spotify',
    'buyer',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
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
                'common.context_processor.django_settings',
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

#DATABASES['OPTIONS'] = {
#    'MAX_CONNS': 4,
#}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'common.auth.EmailAuthBackend',
]

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


# Override datetime formatting
from django.conf.locale.en import formats as en_formats
en_formats.DATETIME_FORMAT = 'Y/m/d H:i'
en_formats.SHORT_DATETIME_FORMAT = 'Y/m/d H:i'
en_formats.DATE_FORMAT = 'Y/m/d'
en_formats.SHORT_DATE_FORMAT = 'Y/m/d'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'


MEDIA_URL = os.environ.get('MEDIA_URL', '')

APPEND_SLASH = True


# CORS
CORS_ALLOWED_ORIGINS = [
    'https://app.acrylic.la',
    'https://app.acrylic.la:4200',
    'http://app.acrylic.la:4200',
    'https://dev.app.acrylic.la',
    'https://dev.app.acrylic.la:4200',
    'http://dev.app.acrylic.la:4200',
    'http://localhost:4200',
    'http://127.0.0.1:4200',
]

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    'Baggage',
    'Sentry-Trace',
]


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


ENVIRONMENT = config('ENVIRONMENT', 'DEV')

# Email settings
EMAIL_BACKEND = 'django_ses.SESBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = 25
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = True
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'noreply@acrylic.la')
DEFAULT_FROM_EMAIL = EMAIL_FROM
AWS_SES_REGION_NAME = os.environ.get('AWS_SES_REGION_NAME', '')
AWS_SES_REGION_ENDPOINT = os.environ.get('AWS_SES_REGION_ENDPOINT', '')
# server mail for errors
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', '')

# django-storages
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage'
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')

PUBLIC_S3_BUCKET = os.environ.get('PUBLIC_S3_BUCKET', '')

# AWS_DEFAULT_ACL = 'private'
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', '')
AWS_IS_GZIPPED = True
AWS_S3_ENDPOINT_URL = f'https://s3.{AWS_S3_REGION_NAME}.amazonaws.com'
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600 * 24 # 1 day

# django-tagging
FORCE_LOWERCASE_TAGS = True
"""
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDISCLOUD_URL', ''),
        'TIMEOUT': 600, # 10 min
        'KEY_PREFIX': 'cache',
        'OPTIONS': {
            'db': '0', # Redis DB nr. 0
        }
    }
}
"""

REST_FRAMEWORK = {
    # YOUR SETTINGS
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    #'DEFAULT_PAGINATION_CLASS': 'common.api.pagination.StandardPagination',
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

BASE_URL = os.environ.get('BASE_URL', 'https://platform.acrylic.la/')
FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL', 'https://app.acrylic.la/')

REST_REGISTRATION = {
    # user profile
    'PROFILE_SERIALIZER_CLASS': 'account.serializers.UserProfileSerializer',
    # user registration
    'REGISTER_SERIALIZER_CLASS': 'account.serializers.RegisterSerializer',
    'REGISTER_OUTPUT_SERIALIZER_CLASS': 'account.serializers.RegisterDoneSerializer',
    'USER_LOGIN_FIELDS': ['email', 'username'],
    'USER_HIDDEN_FIELDS': ['id', 'username', 'last_login', 'is_active', 'is_staff', 'is_superuser', 'user_permissions', 'groups', 'date_joined'],
    'USER_PUBLIC_FIELDS': ['email', 'first_name', 'last_name'],
    'USER_EDITABLE_FIELDS': ['email', 'first_name', 'last_name', 'password', 'password_confirm', 'type'],
    'RESET_PASSWORD_VERIFICATION_ENABLED': True,
    'SEND_RESET_PASSWORD_LINK_SERIALIZER_USE_EMAIL': True,
    'REGISTER_VERIFICATION_ENABLED': False,
    'REGISTER_VERIFICATION_URL': f'{FRONTEND_BASE_URL}auth/verify-user/',
    'RESET_PASSWORD_VERIFICATION_URL': f'{FRONTEND_BASE_URL}auth/reset-password/',
    'REGISTER_EMAIL_VERIFICATION_ENABLED': False,
    #'REGISTER_EMAIL_VERIFICATION_URL': f'{FRONTEND_BASE_URL}auth/verify-email/',
    'VERIFICATION_FROM_EMAIL': 'noreply@acrylic.la',
    'NOT_AUTHENTICATED_PERMISSION_CLASSES': [],
}



# JWT auth settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}


# SSL/TLS settings
#SECURE_SSL_REDIRECT = True
#SESSION_COOKIE_SECURE = True
#CSRF_COOKIE_SECURE = True

# Sorl thumbnail settings 
THUMBNAIL_FORCE_OVERWRITE = True

# SignWell
SIGNWELL_API_KEY = config('SIGNWELL_API_KEY', default='')
SIGNWELL_WEBHOOK_KEY = config('SIGNWELL_WEBHOOK_KEY', default='')
SIGNWELL_TEST_MODE = False

# Dropbox Sign
DROPBOX_SIGN_API_KEY = config('DROPBOX_SIGN_API_KEY', default='')

# Husbpot
HUBSPOT_PORTAL_ID = config('HUBSPOT_PORTAL_ID', default='')
HUBSPOT_ACCESS_TOKEN = config('HUBSPOT_ACCESS_TOKEN', default='')

# Chartmetric API
CHARTMETRIC_REFRESH_TOKEN = config('CHARTMETRIC_REFRESH_TOKEN', default='sZBgq3RceskBkFnjc8YNDm0LUJ7swpuqk6NL4CyEYnlkL5NVpFx2WU8cGwAD7XlZ')
# jeremy: O7gYTjDXBHdLeHEcHH5WVBTFFDrJpPeev6HCjk5LHZ8sBCJFhYfIWmCDGxIU64OS

# Spotify API

SPOTIFY_CLIENT_ID = config('SPOTIFY_CLIENT_ID', default='')
SPOTIFY_CLIENT_SECRET = config('SPOTIFY_CLIENT_SECRET', default='')

# Social auth: Spotify
SOCIAL_AUTH_SPOTIFY_KEY = os.environ.get('SOCIAL_AUTH_SPOTIFY_KEY', '')
SOCIAL_AUTH_SPOTIFY_SECRET = os.environ.get('SOCIAL_AUTH_SPOTIFY_SECRET', '')

# Social auth: Facebook
SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get('SOCIAL_AUTH_FACEBOOK_KEY', '')
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get('SOCIAL_AUTH_FACEBOOK_SECRET', '')
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {
    'fields': 'id, name, email'
}

# Social auth: Google
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

ARTIST_PROFILE_BASE_URL = os.environ.get('ARTIST_PROFILE_BASE_URL', 'https://app.acrylic.la/profile')

# django-import-export
from import_export.formats.base_formats import CSV, XLSX
IMPORT_FORMATS = [CSV, XLSX]
EXPORT_FORMATS = [CSV, XLSX]

# Activate Django-Heroku.
django_heroku.settings(locals())

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# fix django-heroku clash with STORAGES
local_config = locals()
del local_config['STATICFILES_STORAGE']

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
