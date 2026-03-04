"""
Production settings for InHealth Chronic Care.
HIPAA-compliant, hardened, performance-optimized.
"""

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa: F401, F403
from .base import CACHES, LOGGING, env

DEBUG = False

# ---------------------------------------------------------------------------
# Security — HIPAA / HTTPS hardening
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"

X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "strict-origin-when-cross-origin"

# Content Security Policy
CONTENT_SECURITY_POLICY = {
    "EXCLUDE_URL_PREFIXES": ["/admin/"],
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "https:"],
        "font-src": ["'self'"],
        "connect-src": ["'self'", "wss:"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    },
}

# ---------------------------------------------------------------------------
# Allowed hosts — read from env in production
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["api.inhealth.care"])

# ---------------------------------------------------------------------------
# CORS — restrict to known origins in production
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "https://app.inhealth.care",
    "https://provider.inhealth.care",
])

# ---------------------------------------------------------------------------
# Database — connection pooling optimizations
# ---------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = 120  # noqa: F405
DATABASES["default"]["OPTIONS"] = {  # noqa: F405
    "sslmode": "require",
    "connect_timeout": 10,
    "options": "-c default_transaction_isolation=read\ committed",
}

# ---------------------------------------------------------------------------
# Cache — Redis with TLS in production
# ---------------------------------------------------------------------------
CACHES["default"]["OPTIONS"]["CONNECTION_POOL_KWARGS"] = {  # noqa: F405
    "max_connections": 50,
    "retry_on_timeout": True,
}

# ---------------------------------------------------------------------------
# Email — SendGrid in production
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
SENDGRID_SANDBOX_MODE_IN_DEBUG = False
SENDGRID_ECHO_TO_STDOUT = False

# ---------------------------------------------------------------------------
# Logging — production JSON logging with Sentry integration
# ---------------------------------------------------------------------------
LOGGING["handlers"]["console"]["formatter"] = "json"
LOGGING["root"]["level"] = "WARNING"
LOGGING["loggers"]["django"]["level"] = "WARNING"
LOGGING["loggers"]["apps"]["level"] = "INFO"

# ---------------------------------------------------------------------------
# Sentry — error tracking and performance monitoring
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            CeleryIntegration(monitor_beat_tasks=True),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of requests for performance monitoring
        profiles_sample_rate=0.05,
        send_default_pii=False,  # HIPAA: no PII in Sentry
        environment="production",
        before_send=_strip_pii_from_event,
    )


def _strip_pii_from_event(event, hint):
    """Remove any potential PHI/PII from Sentry events before sending."""
    # Strip request bodies that might contain PHI
    if "request" in event:
        event["request"].pop("data", None)
        # Remove sensitive headers
        headers = event["request"].get("headers", {})
        for header in ["Authorization", "Cookie", "X-API-Key"]:
            headers.pop(header, None)
    return event


# ---------------------------------------------------------------------------
# WhiteNoise — compressed static files
# ---------------------------------------------------------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ---------------------------------------------------------------------------
# Celery — production tuning
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200
CELERY_WORKER_CONCURRENCY = 8

# ---------------------------------------------------------------------------
# Rate limiting — stricter in production
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {  # noqa: F405
    **globals()["REST_FRAMEWORK"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "50/hour",
        "user": "3000/hour",
        "auth": "10/minute",
        "fhir": "500/hour",
    },
}
