"""
Tests for the billing app — claims, RPM episode billing eligibility.
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.billing.models import Claim, RPMEpisode


@pytest.mark.django_db
class TestClaimCreate:
    """Claim creation tests."""

    def test_create_claim(self, billing_client, patient, tenant):
        url = reverse("billing:claim-list")
        payload = {
            "patient": str(patient.pk),
            "cpt_codes": [{"code": "99213", "description": "E/M Office Visit Level 3", "units": 1, "fee": 150.00}],
            "icd10_codes": ["E11.9"],
            "billed_amount": "150.00",
            "payer_name": "Test Insurance Co",
            "service_date": timezone.now().date().isoformat(),
        }
        resp = billing_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_create_claim_unauthenticated(self, api_client, patient):
        url = reverse("billing:claim-list")
        payload = {
            "patient": str(patient.pk),
            "billed_amount": "100.00",
        }
        resp = api_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_list_claims(self, billing_client):
        url = reverse("billing:claim-list")
        resp = billing_client.get(url)
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRPMEpisodeBilling:
    """RPM episode billing eligibility tests."""

    def test_create_rpm_episode(self, billing_client, patient, tenant):
        url = reverse("billing:rpm-episode-list")
        payload = {
            "patient": str(patient.pk),
            "start_date": timezone.now().date().isoformat(),
            "devices_used": [
                {"device_type": "cgm", "device_id": "DEX-001", "manufacturer": "Dexcom"},
            ],
        }
        resp = billing_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

    def test_rpm_billing_codes_defined(self):
        """Verify RPM billing codes are defined on the model."""
        assert "99453" in RPMEpisode.RPM_BILLING_CODES
        assert "99454" in RPMEpisode.RPM_BILLING_CODES
        assert "99457" in RPMEpisode.RPM_BILLING_CODES
        assert "99458" in RPMEpisode.RPM_BILLING_CODES

    def test_list_rpm_episodes(self, billing_client):
        url = reverse("billing:rpm-episode-list")
        resp = billing_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
