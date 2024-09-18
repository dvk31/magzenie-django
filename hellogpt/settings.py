import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv
from decouple import config
from supabase import create_client, Client

# -------------------------------------------------------------------
# Base Directory and Environment Variables
# -------------------------------------------------------------------

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# -------------------------------------------------------------------
# Security Settings
# -------------------------------------------------------------------

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '0.0.0.0',
    'localhost:5173',
    '192.168.87.255',
    'dev.withgpt.com',
    '192.168.87.31',
    'localhost:3000',
    '127.0.0.1',
    'web',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# -------------------------------------------------------------------
# Application Definition
# -------------------------------------------------------------------

INSTALLED_APPS = [
    # Django Apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-Party Apps
    'rest_framework',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'django_extensions',
    'corsheaders',
    'rest_framework_simplejwt',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'rest_framework_simplejwt.token_blacklist',
    'allauth.socialaccount.providers.google',
    'django_filters',
    'channels',

    # Local Apps
    'magazines.apps.MagazinesConfig',
    'payments.apps.PaymentsConfig',
    'analytics.apps.AnalyticsConfig',
    'notifications.apps.NotificationsConfig',
    'support.apps.SupportConfig',
    'media.apps.MediaConfig',
    'users.apps.UsersConfig',
    'print_orders.apps.PrintOrdersConfig',
    'digital_setup.apps.DigitalSetupConfig',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'corsheaders.middleware.CorsMiddleware',  # Should be high in the stack
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    'allauth.account.middleware.AccountMiddleware',
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "core.middleware.supabase_auth.SupabaseAuthMiddleware",  # Uncomment if needed
]

ROOT_URLCONF = "hellogpt.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # Add your template directories here
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hellogpt.wsgi.application"
ASGI_APPLICATION = "hellogpt.asgi.application"

# -------------------------------------------------------------------
# Database Configuration
# -------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": config("POSTGRES_DB", default="postgres"),
        "USER": config("POSTGRES_USER", default="postgres"),
        "PASSWORD": config("POSTGRES_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "OPTIONS": {
            "sslmode": "require",
            "options": "-c search_path=public,auth",
        },
    }
}

# -------------------------------------------------------------------
# Password Validation
# -------------------------------------------------------------------

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

# -------------------------------------------------------------------
# Internationalization
# -------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------------
# Static Files
# -------------------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# -------------------------------------------------------------------
# Default Primary Key Field Type
# -------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------------------------
# Custom User Model
# -------------------------------------------------------------------

AUTH_USER_MODEL = 'users.User'

# -------------------------------------------------------------------
# Sites Framework
# -------------------------------------------------------------------

SITE_ID = 1

# -------------------------------------------------------------------
# Authentication Backends
# -------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
       'users.auth_backends.SupabaseAuthBackend',
       #'allauth.account.auth_backends.AuthenticationBackend',
       #'django.contrib.auth.backends.ModelBackend',
   ]

# -------------------------------------------------------------------
# REST Framework Configuration
# -------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        # 'userapp.authentication.APIKeyAuthentication',  # Uncomment if needed
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    # 'EXCEPTION_HANDLER': 'hellogpt.exceptions.custom_exception_handler',
}

# -------------------------------------------------------------------
# Simple JWT Configuration
# -------------------------------------------------------------------

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=360),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JSON_ENCODER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=360),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}

# -------------------------------------------------------------------
# Django-Allauth Configuration
# -------------------------------------------------------------------

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'key': ''
        }
    }
}

# -------------------------------------------------------------------
# CORS Configuration
# -------------------------------------------------------------------

CORS_ALLOW_ALL_ORIGINS = True  # For development only. Remove in production.
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:19006",
    "http://localhost:19000",
    "exp://localhost:19000",
    'https://ffd9bd4542ae.ngrok.app',
    'https://dev.withgpt.com',
    "http://192.168.1.255:19000",
    "http://192.168.1.31:19000",
    "http://localhost:5173",
    'https://d8a8d2-34.myshopify.com',
]

# -------------------------------------------------------------------
# Celery Configuration
# -------------------------------------------------------------------

CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

REDIS_URL = os.getenv('REDIS_URL')
print(f"REDIS_URL: {REDIS_URL}")  # Consider removing or using logging in production
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# -------------------------------------------------------------------
# Channels Configuration
# -------------------------------------------------------------------

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# -------------------------------------------------------------------
# Supabase Configuration
# -------------------------------------------------------------------

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------------------------------------------------
# External API Keys and Services
# -------------------------------------------------------------------

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
MAPBOX_API_KEY = os.getenv('MAPBOX_API_KEY')
SUPABASE_PUBLIC_BUCKET_NAME = os.getenv('SUPABASE_PUBLIC_BUCKET_NAME')

# -------------------------------------------------------------------
# Base URL
# -------------------------------------------------------------------

BASE_URL = 'http://localhost:8000'

# -------------------------------------------------------------------
# DRF Spectacular (API Documentation) Configuration
# -------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    'TITLE': 'Digital Magazine Platform API',
    'DESCRIPTION': 'API for managing digital magazines, templates, pages, AI-generated content, payments, subscriptions, print orders, media uploads, support, and analytics.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PUBLIC': True,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],

    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',

    'SECURITY': [{'Bearer': []}],
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Enter your bearer token in the format **Bearer <token>**'
        }
    },

    'TAGS': [
        {'name': 'users', 'description': 'User management and authentication'},
        {'name': 'magazines', 'description': 'Magazine management operations'},
        {'name': 'templates', 'description': 'Template management operations'},
        {'name': 'pages', 'description': 'Page content and management'},
        {'name': 'ai-processes', 'description': 'AI content generation processes'},
        {'name': 'payments', 'description': 'Payment and subscription operations'},
        {'name': 'print-orders', 'description': 'Print order processing and management'},
        {'name': 'media', 'description': 'Media uploads and management'},
        {'name': 'support', 'description': 'Support tickets and help articles'},
        {'name': 'analytics', 'description': 'User behavior and content analytics'},
        {'name': 'notifications', 'description': 'Notification management'},
    ],

    'SORT_OPERATIONS': False,
    'OPERATION_SORTER': 'alpha',

    'SERVERS': [
        {'url': 'https://dev.withgpt.com.com/', 'description': 'Development server'},
        {'url': 'https://api.yourmagazineplatform.com/v1', 'description': 'Production server'},
        {'url': 'https://staging-api.yourmagazineplatform.com/v1', 'description': 'Staging server'},
        {'url': 'http://127.0.0.1:8000/', 'description': 'Local development server'},
    ],

    'COMPONENT_SPLIT_REQUEST': True,

    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            },
        },
    },
}

# -------------------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------------------

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'users': {  # Replace 'users' with your app name
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Add other loggers as needed
    },
}
