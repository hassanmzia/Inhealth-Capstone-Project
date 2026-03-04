"""WebSocket URL routing for the A2A bridge."""

from django.urls import path

from .consumers import A2AConsumer, VitalsConsumer

websocket_urlpatterns = [
    path("ws/a2a/", A2AConsumer.as_asgi()),
    path("ws/a2a/<str:agent_name>/", A2AConsumer.as_asgi()),
    path("ws/vitals/<uuid:patient_id>/", VitalsConsumer.as_asgi()),
]
