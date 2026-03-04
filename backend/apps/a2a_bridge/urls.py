"""URL configuration for the A2A bridge."""

from django.urls import path

from .views import A2ABroadcastView, A2ASendMessageView

app_name = "a2a"

urlpatterns = [
    path("send/", A2ASendMessageView.as_view(), name="a2a-send"),
    path("broadcast/", A2ABroadcastView.as_view(), name="a2a-broadcast"),
]
