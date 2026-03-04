"""URL configuration for the notifications app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificationTemplateViewSet, NotificationViewSet

app_name = "notifications"

router = DefaultRouter()
router.register("", NotificationViewSet, basename="notification")
router.register("templates", NotificationTemplateViewSet, basename="notification-template")

urlpatterns = [
    path("", include(router.urls)),
]
