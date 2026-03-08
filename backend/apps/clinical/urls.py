"""URL configuration for the clinical app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CareGapViewSet, EncounterViewSet, SmartOrderSetViewSet, VitalTargetPolicyViewSet, VitalsIngestView

app_name = "clinical"

router = DefaultRouter()
router.register("encounters", EncounterViewSet, basename="encounter")
router.register("care-gaps", CareGapViewSet, basename="care-gap")
router.register("order-sets", SmartOrderSetViewSet, basename="smart-order-set")
router.register("vital-targets", VitalTargetPolicyViewSet, basename="vital-target")

urlpatterns = [
    path("vitals/", VitalsIngestView.as_view(), name="vitals-ingest"),
    path("", include(router.urls)),
]
