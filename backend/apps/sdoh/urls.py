"""URL configuration for the SDOH app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SDOHAssessmentViewSet

app_name = "sdoh"

router = DefaultRouter()
router.register("", SDOHAssessmentViewSet, basename="sdoh-assessment")

urlpatterns = [
    path("", include(router.urls)),
]
