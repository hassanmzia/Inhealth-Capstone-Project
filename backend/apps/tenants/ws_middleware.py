"""
JWT authentication middleware for Django Channels WebSocket connections.

Django's AuthMiddlewareStack only supports session-based auth. This middleware
reads a JWT from the `?token=...` query string (which browsers can pass for
WebSocket connections since the WS API doesn't support custom headers) and
populates scope["user"] so consumers can trust request.user.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user_from_token(token: str):
    """Decode the JWT and return the matching User, or AnonymousUser."""
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        from apps.accounts.models import User

        payload = AccessToken(token)
        user_id = payload.get("user_id")
        if not user_id:
            return AnonymousUser()
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    Channels ASGI middleware that authenticates WebSocket connections via JWT.

    Usage: wrap the URLRouter with this middleware instead of
    AuthMiddlewareStack to support token-based auth.

    Accepts the token as:
      - ?token=<jwt>  (query string — standard for WS clients)
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            qs = parse_qs(scope.get("query_string", b"").decode())
            token = (qs.get("token") or [""])[0]
            if token:
                scope["user"] = await _get_user_from_token(token)
            else:
                scope["user"] = AnonymousUser()
        await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Drop-in replacement for AuthMiddlewareStack that uses JWT query-string auth."""
    return JWTAuthMiddleware(inner)
