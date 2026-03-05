"""URL configuration for the analytics app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClinicalKPIViewSet, PopulationCohortViewSet, PopulationHealthView, RiskScoreViewSet

app_name = "analytics"

router = DefaultRouter()
router.register("cohorts", PopulationCohortViewSet, basename="cohort")
router.register("risk-scores", RiskScoreViewSet, basename="risk-score")
router.register("kpis", ClinicalKPIViewSet, basename="kpi")

urlpatterns = [
    path("population/", PopulationHealthView.as_view(), name="population-health"),
    path("", include(router.urls)),
]
