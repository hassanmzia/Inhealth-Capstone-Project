"""Self-service patient endpoints (authenticated patient acting on own data)."""

from django.urls import path

from .views import PatientHealthSummaryView

urlpatterns = [
    path("health-summary/", PatientHealthSummaryView.as_view(), name="patient-health-summary"),
]
