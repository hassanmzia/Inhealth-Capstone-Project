"""URL configuration for the telemedicine app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import VideoSessionViewSet

app_name = "telemedicine"

router = DefaultRouter()
router.register("sessions", VideoSessionViewSet, basename="video-session")

urlpatterns = [
    path("", include(router.urls)),
]
