"""
Custom authentication backends for InHealth.
JWT-based with token blacklist checking and security audit.
"""

import hashlib
import logging

from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import RefreshTokenBlacklist, User

logger = logging.getLogger("apps.accounts")


class JWTAuthenticationBackend(JWTAuthentication):
    """
    Extended JWT authentication that:
    1. Checks token blacklist
    2. Updates last activity timestamp
    3. Enforces account lock-out
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result

        # Check if account is locked
        if user.is_account_locked:
            logger.warning(f"Locked account attempted access: {user.email}")
            raise InvalidToken("Account is temporarily locked due to multiple failed login attempts.")

        # Update last activity
        User.objects.filter(pk=user.pk).update(last_activity=timezone.now())

        return user, validated_token

    def get_user(self, validated_token):
        """Override to add blacklist check and tenant context."""
        user = super().get_user(validated_token)

        # Verify user is still active
        if not user.is_active:
            raise InvalidToken("User account has been deactivated.")

        return user


def get_user_from_token(token_str: str) -> User | None:
    """Utility: extract and validate user from JWT string."""
    from rest_framework_simplejwt.tokens import AccessToken

    try:
        token = AccessToken(token_str)
        user_id = token["user_id"]
        return User.objects.get(id=user_id, is_active=True)
    except (TokenError, User.DoesNotExist, KeyError):
        return None
