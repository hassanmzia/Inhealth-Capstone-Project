"""
FHIR R4 URL configuration.
Implements standard FHIR REST interactions for each resource type.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FHIRAllergyIntoleranceViewSet,
    FHIRAppointmentViewSet,
    FHIRCarePlanViewSet,
    FHIRConditionViewSet,
    FHIRDiagnosticReportViewSet,
    FHIRDocumentReferenceViewSet,
    FHIREncounterViewSet,
    FHIRImmunizationViewSet,
    FHIRMedicationRequestViewSet,
    FHIRObservationViewSet,
    FHIRPatientViewSet,
)

app_name = "fhir"

router = DefaultRouter()
router.register("Patient", FHIRPatientViewSet, basename="fhir-patient")
router.register("Observation", FHIRObservationViewSet, basename="fhir-observation")
router.register("Condition", FHIRConditionViewSet, basename="fhir-condition")
router.register("MedicationRequest", FHIRMedicationRequestViewSet, basename="fhir-medication-request")
router.register("AllergyIntolerance", FHIRAllergyIntoleranceViewSet, basename="fhir-allergy")
router.register("Appointment", FHIRAppointmentViewSet, basename="fhir-appointment")
router.register("CarePlan", FHIRCarePlanViewSet, basename="fhir-care-plan")
router.register("Encounter", FHIREncounterViewSet, basename="fhir-encounter")
router.register("Immunization", FHIRImmunizationViewSet, basename="fhir-immunization")
router.register("DiagnosticReport", FHIRDiagnosticReportViewSet, basename="fhir-diagnostic-report")
router.register("DocumentReference", FHIRDocumentReferenceViewSet, basename="fhir-document-reference")

urlpatterns = [
    path("", include(router.urls)),
]
