"""URL configuration for the patients app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from .views import (
    DeviceRegistrationViewSet,
    PatientDemographicsView,
    PatientEngagementView,
    PatientViewSet,
)

app_name = "patients"

router = DefaultRouter()
router.register("", PatientViewSet, basename="patient")

patient_router = nested_routers.NestedDefaultRouter(router, "", lookup="patient")
patient_router.register("devices", DeviceRegistrationViewSet, basename="patient-device")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(patient_router.urls)),
    path("<uuid:patient_pk>/demographics/", PatientDemographicsView.as_view(), name="patient-demographics"),
    path("<uuid:patient_pk>/engagement/", PatientEngagementView.as_view(), name="patient-engagement"),
]
