"""URL configuration for the research app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClinicalTrialViewSet, MedicalEvidenceViewSet, ResearchQueryViewSet

app_name = "research"

router = DefaultRouter()
router.register("queries", ResearchQueryViewSet, basename="research-query")
router.register("trials", ClinicalTrialViewSet, basename="clinical-trial")
router.register("evidence", MedicalEvidenceViewSet, basename="medical-evidence")

urlpatterns = [
    path("", include(router.urls)),
]
