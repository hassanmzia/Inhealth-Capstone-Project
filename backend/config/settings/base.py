"""
Base Django settings for InHealth Chronic Care platform.
Multi-tenant, FHIR-compliant, AI-powered chronic disease management.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    DJANGO_SECRET_KEY=(str, "change-me-in-production-use-strong-random-value"),
    DATABASE_URL=(str, "postgis://inhealth:inhealth@localhost:5432/inhealth"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    NEO4J_URI=(str, "bolt://localhost:7687"),
    NEO4J_USER=(str, "neo4j"),
    NEO4J_PASSWORD=(str, "password"),
    QDRANT_HOST=(str, "localhost"),
    QDRANT_PORT=(int, 6333),
    MINIO_ENDPOINT=(str, "localhost:9000"),
    MINIO_ACCESS_KEY=(str, "minioadmin"),
    MINIO_SECRET_KEY=(str, "minioadmin"),
    MINIO_BUCKET_NAME=(str, "inhealth-media"),
    FHIR_BASE_URL=(str, "http://localhost:8080/fhir/R4"),
    LANGFUSE_HOST=(str, "https://cloud.langfuse.com"),
    LANGFUSE_PUBLIC_KEY=(str, ""),
    LANGFUSE_SECRET_KEY=(str, ""),
    OPENAI_API_KEY=(str, ""),
    ANTHROPIC_API_KEY=(str, ""),
    SENTRY_DSN=(str, ""),
    TWILIO_ACCOUNT_SID=(str, ""),
    TWILIO_AUTH_TOKEN=(str, ""),
    TWILIO_FROM_NUMBER=(str, ""),
    SENDGRID_API_KEY=(str, ""),
    DEFAULT_FROM_EMAIL=(str, "noreply@inhealth.care"),
    ENCRYPTION_KEY=(str, ""),
)

# Load .env file if present
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# django-tenants MUST come first, followed by content_types
# ---------------------------------------------------------------------------
SHARED_APPS = [
    # django-tenants
    "django_tenants",
    # Django core (shared)
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.gis",
    # Shared InHealth apps
    "apps.tenants",
    "apps.accounts",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "guardian",
    "channels",
    "django_celery_beat",
    "storages",
    "drf_spectacular",
    "django_prometheus",
]

TENANT_APPS = [
    # Per-tenant apps
    "apps.fhir",
    "apps.hl7",
    "apps.patients",
    "apps.clinical",
    "apps.notifications",
    "apps.analytics",
    "apps.research",
    "apps.billing",
    "apps.sdoh",
    "apps.mcp_bridge",
    "apps.a2a_bridge",
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "tenants.Organization"
TENANT_DOMAIN_MODEL = "tenants.Domain"

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "apps.tenants.middleware.PublicFallbackTenantMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
    "apps.accounts.middleware.AuditMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL with PostGIS + pgvector
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": env.db("DATABASE_URL")["NAME"],
        "USER": env.db("DATABASE_URL")["USER"],
        "PASSWORD": env.db("DATABASE_URL")["PASSWORD"],
        "HOST": env.db("DATABASE_URL").get("HOST", "localhost"),
        "PORT": env.db("DATABASE_URL").get("PORT", "5432"),
        "OPTIONS": {
            "sslmode": "prefer",
        },
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

# ---------------------------------------------------------------------------
# Cache — Redis
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "inhealth",
        "TIMEOUT": 300,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 24 hours

# ---------------------------------------------------------------------------
# Django Channels — WebSocket layer
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_TASK_ROUTES = {
    "apps.*.tasks.send_*": {"queue": "notifications"},
    "apps.analytics.tasks.*": {"queue": "analytics"},
    "apps.research.tasks.*": {"queue": "research"},
    "apps.clinical.tasks.*": {"queue": "clinical"},
}

CELERY_BEAT_SCHEDULE = {
    "monitor-all-patients": {
        "task": "apps.clinical.tasks.monitor_all_patients",
        "schedule": 300.0,  # every 5 minutes
        "options": {"queue": "clinical"},
    },
    "sync-device-data": {
        "task": "apps.patients.tasks.sync_device_data",
        "schedule": 60.0,  # every 1 minute
        "options": {"queue": "clinical"},
    },
    "generate-population-analytics": {
        "task": "apps.analytics.tasks.generate_population_analytics",
        "schedule": 3600.0,  # every hour
        "options": {"queue": "analytics"},
    },
    "check-care-gaps": {
        "task": "apps.clinical.tasks.check_care_gaps",
        "schedule": {"hour": 0, "minute": 0},  # daily midnight
        "options": {"queue": "clinical"},
    },
    "sync-clinical-guidelines": {
        "task": "apps.research.tasks.sync_clinical_guidelines",
        "schedule": {"day_of_week": 0, "hour": 2, "minute": 0},  # weekly Sunday 2AM
        "options": {"queue": "research"},
    },
    "cleanup-expired-sessions": {
        "task": "apps.accounts.tasks.cleanup_expired_tokens",
        "schedule": {"hour": 3, "minute": 0},  # daily 3AM
        "options": {"queue": "default"},
    },
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.authentication.JWTAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "MAX_PAGE_SIZE": 100,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "5000/hour",
        "auth": "20/minute",
        "fhir": "1000/hour",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.accounts.exceptions.custom_exception_handler",
}

# ---------------------------------------------------------------------------
# SimpleJWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.CustomTokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-tenant-id",
    "x-api-key",
]

# ---------------------------------------------------------------------------
# Storage — MinIO / S3-compatible
# ---------------------------------------------------------------------------
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": env("MINIO_ACCESS_KEY"),
            "secret_key": env("MINIO_SECRET_KEY"),
            "bucket_name": env("MINIO_BUCKET_NAME"),
            "endpoint_url": f"http://{env('MINIO_ENDPOINT')}",
            "region_name": "us-east-1",
            "default_acl": "private",
            "querystring_auth": True,
            "querystring_expire": 3600,
            "file_overwrite": False,
            "object_parameters": {
                "ServerSideEncryption": "AES256",
            },
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
SENDGRID_API_KEY = env("SENDGRID_API_KEY")

# ---------------------------------------------------------------------------
# External services
# ---------------------------------------------------------------------------
FHIR_BASE_URL = env("FHIR_BASE_URL")

NEO4J_URI = env("NEO4J_URI")
NEO4J_USER = env("NEO4J_USER")
NEO4J_PASSWORD = env("NEO4J_PASSWORD")

QDRANT_HOST = env("QDRANT_HOST")
QDRANT_PORT = env("QDRANT_PORT")

OPENAI_API_KEY = env("OPENAI_API_KEY")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")

LANGFUSE_HOST = env("LANGFUSE_HOST")
LANGFUSE_PUBLIC_KEY = env("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = env("LANGFUSE_SECRET_KEY")

TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER")

ENCRYPTION_KEY = env("ENCRYPTION_KEY")

# ---------------------------------------------------------------------------
# DRF Spectacular (OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "InHealth Chronic Care API",
    "DESCRIPTION": "Production-grade multi-tenant chronic disease management platform API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "SECURITY": [{"Bearer": []}],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
}

# ---------------------------------------------------------------------------
# Structured JSON Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d",
        },
        "verbose": {
            "format": "[{levelname}] {asctime} {name} {module}:{lineno} — {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "file_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "error.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 10,
            "formatter": "json",
            "level": "ERROR",
        },
        "file_audit": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "audit.log",
            "maxBytes": 50 * 1024 * 1024,
            "backupCount": 30,
            "formatter": "json",
        },
        "null": {"class": "logging.NullHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "file_error"],
            "level": "WARNING",
            "propagate": False,
        },
        "inhealth.audit": {
            "handlers": ["file_audit", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file_error"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Ensure log directory exists
(BASE_DIR / "logs").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Guardian
# ---------------------------------------------------------------------------
ANONYMOUS_USER_NAME = None  # Disable anonymous user in guardian
GUARDIAN_RAISE_403 = True

# ---------------------------------------------------------------------------
# FHIR Settings
# ---------------------------------------------------------------------------
FHIR_VERSION = "R4"
FHIR_VALIDATION_ENABLED = True
FHIR_SUPPORTED_RESOURCE_TYPES = [
    "Patient", "Observation", "Condition", "MedicationRequest",
    "DiagnosticReport", "Appointment", "CarePlan", "AllergyIntolerance",
    "Encounter", "Procedure", "Immunization", "DocumentReference",
]

# ---------------------------------------------------------------------------
# Security base (overridden in production.py)
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
