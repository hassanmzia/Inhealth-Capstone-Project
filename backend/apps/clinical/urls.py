"""URL configuration for the clinical app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CareGapViewSet, EncounterViewSet, SmartOrderSetViewSet

app_name = "clinical"

router = DefaultRouter()
router.register("encounters", EncounterViewSet, basename="encounter")
router.register("care-gaps", CareGapViewSet, basename="care-gap")
router.register("order-sets", SmartOrderSetViewSet, basename="smart-order-set")

urlpatterns = [
    path("", include(router.urls)),
]
