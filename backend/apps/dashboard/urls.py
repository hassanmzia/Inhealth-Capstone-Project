"""Dashboard aggregate URL configuration."""

from django.urls import path

from .views import (
    AppointmentsListView,
    ClinicalDashboardStatsView,
    NurseDashboardStatsView,
    ResearcherDashboardView,
)

urlpatterns = [
    # Clinician / admin dashboard stats — GET /api/v1/dashboard/stats/
    path("stats/", ClinicalDashboardStatsView.as_view(), name="dashboard-stats"),
    # Nurse-specific stats — GET /api/v1/dashboard/nurse-stats/
    path("nurse-stats/", NurseDashboardStatsView.as_view(), name="dashboard-nurse-stats"),
    # Researcher dashboard — GET /api/v1/dashboard/researcher/
    path("researcher/", ResearcherDashboardView.as_view(), name="dashboard-researcher"),
]

# Also export the appointments view so config/urls.py can wire it separately
appointments_urlpatterns = [
    # GET /api/v1/appointments/
    path("", AppointmentsListView.as_view(), name="appointments-list"),
]
