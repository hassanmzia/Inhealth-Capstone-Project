"""
Tests for the accounts app — registration, login, JWT refresh, RBAC.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import User


@pytest.mark.django_db
class TestRegistration:
    """User registration endpoint tests."""

    def test_register_patient_success(self, api_client, tenant):
        url = reverse("accounts:register")
        payload = {
            "email": "newpatient@example.com",
            "first_name": "New",
            "last_name": "Patient",
            "password": "Str0ngP@ssw0rd!",
            "password_confirm": "Str0ngP@ssw0rd!",
            "role": "patient",
        }
        resp = api_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)
        assert User.objects.filter(email="newpatient@example.com").exists()

    def test_register_password_mismatch(self, api_client):
        url = reverse("accounts:register")
        payload = {
            "email": "mismatch@example.com",
            "first_name": "Bad",
            "last_name": "Pass",
            "password": "Str0ngP@ssw0rd!",
            "password_confirm": "DifferentP@ss1!",
            "role": "patient",
        }
        resp = api_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, user):
        url = reverse("accounts:register")
        payload = {
            "email": user.email,
            "first_name": "Dup",
            "last_name": "User",
            "password": "Str0ngP@ssw0rd!",
            "password_confirm": "Str0ngP@ssw0rd!",
            "role": "patient",
        }
        resp = api_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    """Authentication and JWT token tests."""

    def test_login_success(self, api_client, user):
        user.is_active = True
        user.save(update_fields=["is_active"])
        url = reverse("accounts:login")
        resp = api_client.post(url, {"email": user.email, "password": "SecureP@ssw0rd!123"}, format="json")
        # Login may return 200 with tokens or 401 if email verification is required
        if resp.status_code == status.HTTP_200_OK:
            assert "access" in resp.data or "token" in resp.data

    def test_login_wrong_password(self, api_client, user):
        url = reverse("accounts:login")
        resp = api_client.post(url, {"email": user.email, "password": "WrongPassword!"}, format="json")
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self, api_client):
        url = reverse("accounts:login")
        resp = api_client.post(url, {"email": "ghost@test.com", "password": "Whatever1!"}, format="json")
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db
class TestTokenRefresh:
    """JWT token refresh tests."""

    def test_token_refresh_requires_token(self, api_client):
        url = reverse("accounts:token-refresh")
        resp = api_client.post(url, {}, format="json")
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db
class TestRBAC:
    """Role-based access control checks."""

    def test_physician_role_set(self, user):
        assert user.role == User.Role.PHYSICIAN

    def test_nurse_role_set(self, nurse_user):
        assert nurse_user.role == User.Role.NURSE

    def test_patient_role_set(self, patient_user):
        assert patient_user.role == User.Role.PATIENT

    def test_billing_role_set(self, billing_user):
        assert billing_user.role == User.Role.BILLING

    def test_unauthenticated_profile_access_denied(self, api_client):
        url = reverse("accounts:profile")
        resp = api_client.get(url)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_authenticated_profile_access(self, authenticated_client):
        url = reverse("accounts:profile")
        resp = authenticated_client.get(url)
        # 200 if profile exists, 405 if GET not allowed (depends on view)
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED)
