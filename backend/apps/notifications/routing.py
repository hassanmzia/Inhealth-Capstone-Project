"""WebSocket URL routing for the notifications app."""

from django.urls import path

from .consumers import AlertConsumer

websocket_urlpatterns = [
    path("ws/alerts/", AlertConsumer.as_asgi()),
    path("ws/alerts/<str:room>/", AlertConsumer.as_asgi()),
]
