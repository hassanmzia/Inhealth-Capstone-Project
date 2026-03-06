"""
Tests for the clinical app — encounters, vitals, care gaps.
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status


@pytest.mark.django_db
class TestEncounterCreate:
    """Encounter creation tests."""

    def test_create_encounter(self, authenticated_client, patient, tenant):
        url = reverse("clinical:encounter-list")
        payload = {
            "patient": str(patient.pk),
            "encounter_type": "outpatient",
            "start_datetime": timezone.now().isoformat(),
            "chief_complaint": "Follow-up for diabetes management",
        }
        resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_create_encounter_missing_patient(self, authenticated_client):
        url = reverse("clinical:encounter-list")
        payload = {
            "encounter_type": "outpatient",
            "start_datetime": timezone.now().isoformat(),
        }
        resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_encounter_unauthenticated(self, api_client, patient):
        url = reverse("clinical:encounter-list")
        payload = {
            "patient": str(patient.pk),
            "encounter_type": "outpatient",
            "start_datetime": timezone.now().isoformat(),
        }
        resp = api_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestVitalsCreateList:
    """Vital sign (observation) creation and listing."""

    def test_create_vital_observation(self, authenticated_client, patient, tenant):
        url = reverse("fhir:observation-list")
        payload = {
            "patient": str(patient.pk),
            "status": "final",
            "category": "vital-signs",
            "code": "8480-6",
            "code_display": "Systolic blood pressure",
            "value_quantity": 128,
            "value_unit": "mmHg",
        }
        resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_list_vitals(self, authenticated_client):
        url = reverse("fhir:observation-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCareGapList:
    """Care gap listing tests."""

    def test_list_care_gaps(self, authenticated_client):
        url = reverse("clinical:care-gap-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_list_care_gaps_unauthenticated(self, api_client):
        url = reverse("clinical:care-gap-list")
        resp = api_client.get(url)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
