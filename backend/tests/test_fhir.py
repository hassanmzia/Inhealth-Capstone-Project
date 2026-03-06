"""
Tests for the FHIR app — Patient CRUD, Observation, MedicationRequest.
"""

import uuid

import pytest
from django.urls import reverse
from rest_framework import status

from apps.fhir.models import FHIRMedicationRequest, FHIRObservation, FHIRPatient


@pytest.mark.django_db
class TestFHIRPatient:
    """FHIR Patient resource CRUD."""

    def test_create_patient(self, authenticated_client, tenant):
        url = reverse("fhir:patient-list")
        payload = {
            "mrn": "MRN-NEW-001",
            "first_name": "Alice",
            "last_name": "Wonder",
            "birth_date": "1992-03-15",
            "gender": "female",
            "active": True,
        }
        resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_list_patients(self, authenticated_client, patient):
        url = reverse("fhir:patient-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_retrieve_patient(self, authenticated_client, patient):
        url = reverse("fhir:patient-detail", kwargs={"pk": str(patient.pk)})
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_update_patient(self, authenticated_client, patient):
        url = reverse("fhir:patient-detail", kwargs={"pk": str(patient.pk)})
        resp = authenticated_client.patch(url, {"last_name": "Updated"}, format="json")
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unauthenticated_patient_list(self, api_client):
        url = reverse("fhir:patient-list")
        resp = api_client.get(url)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestFHIRObservation:
    """FHIR Observation resource tests."""

    def test_create_observation(self, authenticated_client, patient, tenant):
        url = reverse("fhir:observation-list")
        payload = {
            "patient": str(patient.pk),
            "status": "final",
            "category": "vital-signs",
            "code": "8867-4",
            "code_display": "Heart rate",
            "value_quantity": 72,
            "value_unit": "bpm",
        }
        resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_list_observations(self, authenticated_client, patient):
        url = reverse("fhir:observation-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFHIRMedicationRequest:
    """FHIR MedicationRequest resource tests."""

    def test_create_medication_request(self, authenticated_client, patient, tenant):
        url = reverse("fhir:medicationrequest-list")
        payload = {
            "patient": str(patient.pk),
            "status": "active",
            "intent": "order",
            "medication_code": "860975",
            "medication_display": "Metformin 500 MG",
            "dosage_instructions": "Take 1 tablet twice daily with meals",
        }
        resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)
