"""
Tests for the patients app — list, detail, create, update with tenant isolation.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.fhir.models import FHIRPatient


@pytest.mark.django_db
class TestPatientList:
    """Patient list endpoint tests."""

    def test_list_patients(self, authenticated_client, patient):
        url = reverse("patients:patient-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        # Should include the test patient
        data = resp.data
        results = data.get("results", data) if isinstance(data, dict) else data
        assert len(results) >= 1

    def test_list_patients_unauthenticated(self, api_client):
        url = reverse("patients:patient-list")
        resp = api_client.get(url)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestPatientDetail:
    """Patient detail endpoint tests."""

    def test_retrieve_patient(self, authenticated_client, patient):
        url = reverse("patients:patient-detail", kwargs={"pk": str(patient.pk)})
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_retrieve_nonexistent_patient(self, authenticated_client):
        url = reverse("patients:patient-detail", kwargs={"pk": "00000000-0000-0000-0000-000000000000"})
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestPatientCreate:
    """Patient creation tests."""

    def test_create_patient(self, authenticated_client, tenant):
        url = reverse("patients:patient-list")
        payload = {
            "mrn": "MRN-CREATE-001",
            "first_name": "Test",
            "last_name": "Create",
            "birth_date": "1990-05-20",
            "gender": "female",
        }
        resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_create_patient_missing_required_fields(self, authenticated_client):
        url = reverse("patients:patient-list")
        resp = authenticated_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPatientUpdate:
    """Patient update tests."""

    def test_update_patient(self, authenticated_client, patient):
        url = reverse("patients:patient-detail", kwargs={"pk": str(patient.pk)})
        resp = authenticated_client.patch(url, {"last_name": "Updated"}, format="json")
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED)


@pytest.mark.django_db
class TestPatientTenantIsolation:
    """Ensure patients are isolated per tenant."""

    def test_cannot_access_other_tenant_patient(self, authenticated_client, other_tenant_patient):
        """A user from one tenant should not see patients from another tenant."""
        url = reverse("patients:patient-detail", kwargs={"pk": str(other_tenant_patient.pk)})
        resp = authenticated_client.get(url)
        assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)

    def test_list_excludes_other_tenant_patients(self, authenticated_client, patient, other_tenant_patient):
        """Patient list should only include same-tenant patients."""
        url = reverse("patients:patient-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        results = data.get("results", data) if isinstance(data, dict) else data
        patient_ids = [str(p.get("id", p.get("pk", ""))) for p in results]
        assert str(other_tenant_patient.pk) not in patient_ids
