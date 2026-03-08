"""
Development settings for InHealth Chronic Care.
"""

from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, LOGGING, MIDDLEWARE

DEBUG = True
SECRET_KEY = "dev-secret-key-do-not-use-in-production-abc123xyz789"

ALLOWED_HOSTS = ["*"]

# Allow all CORS in development
CORS_ALLOW_ALL_ORIGINS = True

# Disable SSL/HTTPS requirements in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Debug toolbar
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

INTERNAL_IPS = ["127.0.0.1", "localhost"]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}

# Console email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Override storage to use local filesystem in development
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Override logging for development — colorful console output
LOGGING["handlers"]["console"]["formatter"] = "verbose"
LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
LOGGING["loggers"]["django"]["level"] = "INFO"
# Silence per-query SQL logging (extremely noisy with celery-beat ticks)
LOGGING["loggers"]["django.db.backends"] = {
    "level": "WARNING",
    "handlers": ["console"],
    "propagate": False,
}

# Disable file handlers in development (no logs directory required)
for logger in LOGGING["loggers"].values():
    logger["handlers"] = [h for h in logger.get("handlers", []) if not h.startswith("file")]

# Celery — execute tasks eagerly in tests / dev shell
CELERY_TASK_ALWAYS_EAGER = False  # Set to True to run tasks synchronously
CELERY_TASK_EAGER_PROPAGATES = True

# Shorter token lifetimes for testing
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    **globals().get("SIMPLE_JWT", {}),
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

# Django Extensions shell_plus settings
SHELL_PLUS = "ipython"
SHELL_PLUS_PRINT_SQL = True
IPYTHON_ARGUMENTS = [
    "--ext",
    "autoreload",
    "--ext",
    "django_extensions.management.notebook_extension",
]
