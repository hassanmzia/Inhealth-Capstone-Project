"""Standalone appointments URL wired as /api/v1/appointments/."""

from django.urls import path

from .views import AppointmentsListView

urlpatterns = [
    path("", AppointmentsListView.as_view(), name="appointments-list"),
]
