"""
Django signals for the accounts app.
"""

import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("apps.accounts")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    logger.info(f"User logged in: {user.email}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        logger.info(f"User logged out: {user.email}")


@receiver(user_login_failed)
def log_login_failure(sender, credentials, request, **kwargs):
    email = credentials.get("email", "unknown")
    logger.warning(f"Failed login attempt for: {email}")
    # Increment failed login counter
    from .models import User
    try:
        user = User.objects.get(email=email)
        user.record_failed_login()
    except User.DoesNotExist:
        pass
