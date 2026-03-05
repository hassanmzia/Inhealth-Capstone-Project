"""
Celery tasks for the accounts app.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.accounts")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(self, user_id: str):
    """Send email verification link to a newly registered user."""
    try:
        from .models import User
        from django.core.mail import send_mail
        from django.conf import settings

        user = User.objects.get(id=user_id)
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={user.email_verification_token}"

        send_mail(
            subject="Verify your InHealth account",
            message=f"""
Dear {user.get_full_name()},

Thank you for registering with InHealth Chronic Care!

Please verify your email address by clicking the link below:
{verify_url}

This link will remain active until you verify your account.

If you did not create this account, please ignore this email.

Best regards,
The InHealth Team
            """.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Verification email sent to {user.email}")
        return {"status": "sent", "user_id": user_id}
    except Exception as exc:
        logger.error(f"Failed to send verification email to user {user_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, user_id: str):
    """Send a welcome email after email is verified."""
    try:
        from .models import User
        from django.core.mail import send_mail
        from django.conf import settings

        user = User.objects.get(id=user_id)

        send_mail(
            subject="Welcome to InHealth Chronic Care",
            message=f"""
Dear {user.get_full_name()},

Your InHealth Chronic Care account is now active.

Your role: {user.get_role_display()}

To get started, please log in at: {settings.FRONTEND_URL}/login

If you have any questions, please contact your care coordinator.

Best regards,
The InHealth Team
            """.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to {user.email}")
        return {"status": "sent", "user_id": user_id}
    except Exception as exc:
        logger.error(f"Failed to send welcome email to user {user_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset(self, user_id: str, reset_token: str):
    """Send password reset email."""
    try:
        from .models import User
        from django.core.mail import send_mail
        from django.conf import settings

        user = User.objects.get(id=user_id)
        reset_url = f"https://app.inhealth.care/reset-password?token={reset_token}"

        send_mail(
            subject="InHealth - Password Reset Request",
            message=f"""
Dear {user.get_full_name()},

You requested a password reset for your InHealth account.

Click the link below to reset your password (valid for 1 hour):
{reset_url}

If you did not request this, please ignore this email and contact support immediately.

Best regards,
The InHealth Security Team
            """.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user.email}")
        return {"status": "sent", "user_id": user_id}
    except Exception as exc:
        logger.error(f"Failed to send password reset email to user {user_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_tokens():
    """
    Remove expired blacklisted tokens and inactive sessions.
    Runs daily at 3 AM.
    """
    from .models import RefreshTokenBlacklist

    cutoff = timezone.now() - timedelta(days=7)
    deleted_count, _ = RefreshTokenBlacklist.objects.filter(
        blacklisted_at__lt=cutoff
    ).delete()

    # Also clean up simplejwt's built-in blacklist
    try:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
        expired_tokens = OutstandingToken.objects.filter(expires_at__lt=timezone.now())
        BlacklistedToken.objects.filter(token__in=expired_tokens).delete()
        expired_tokens.delete()
    except Exception as e:
        logger.warning(f"Could not clean simplejwt blacklist: {e}")

    logger.info(f"Cleaned up {deleted_count} expired blacklisted tokens")
    return {"deleted_tokens": deleted_count}


@shared_task(bind=True, max_retries=3)
def create_audit_log_async(
    self,
    user_id: str,
    action: str,
    resource_type: str,
    ip_address: str = "",
    user_agent: str = "",
    phi_accessed: bool = False,
    tenant_id: str = None,
    resource_id: str = None,
    details: dict = None,
):
    """Create an audit log entry asynchronously (non-blocking)."""
    try:
        from .models import AuditLog, User
        import uuid

        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass

        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=uuid.UUID(resource_id) if resource_id else None,
            ip_address=ip_address or None,
            user_agent=user_agent,
            phi_accessed=phi_accessed,
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            details=details or {},
        )
    except Exception as exc:
        logger.error(f"Failed to create audit log: {exc}")
        raise self.retry(exc=exc)
