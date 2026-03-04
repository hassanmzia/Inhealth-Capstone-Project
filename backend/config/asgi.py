"""
ASGI configuration for InHealth Chronic Care.
Supports both HTTP (via Django) and WebSocket (via Django Channels).
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# Initialize Django ASGI application early to ensure AppRegistry is populated
django_asgi_app = get_asgi_application()

# Import WebSocket routing AFTER Django setup
from apps.a2a_bridge.routing import websocket_urlpatterns as a2a_ws_patterns  # noqa: E402
from apps.notifications.routing import websocket_urlpatterns as notification_ws_patterns  # noqa: E402

# Combine all WebSocket URL patterns
from django.urls import path  # noqa: E402

all_websocket_patterns = (
    notification_ws_patterns
    + a2a_ws_patterns
    + [
        # Patient vitals real-time stream
        path("ws/vitals/<uuid:patient_id>/", __import__("apps.a2a_bridge.consumers", fromlist=["VitalsConsumer"]).VitalsConsumer.as_asgi()),
        # Clinical alerts stream
        path("ws/alerts/", __import__("apps.notifications.consumers", fromlist=["AlertConsumer"]).AlertConsumer.as_asgi()),
    ]
)

application = ProtocolTypeRouter(
    {
        # HTTP — standard Django ASGI
        "http": django_asgi_app,
        # WebSocket — Channels with JWT auth middleware
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(all_websocket_patterns)
            )
        ),
    }
)
