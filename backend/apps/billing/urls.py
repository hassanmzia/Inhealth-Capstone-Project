"""URL configuration for the billing app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClaimViewSet, RPMEpisodeViewSet

app_name = "billing"

router = DefaultRouter()
router.register("claims", ClaimViewSet, basename="claim")
router.register("rpm", RPMEpisodeViewSet, basename="rpm-episode")

urlpatterns = [
    path("", include(router.urls)),
]
