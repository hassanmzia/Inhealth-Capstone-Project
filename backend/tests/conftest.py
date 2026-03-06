"""
Shared pytest fixtures for InHealth backend tests.
"""

import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.fhir.models import FHIRPatient
from apps.tenants.models import Organization


@pytest.fixture
def tenant(db):
    """Create a test organization / tenant."""
    return Organization.objects.create(
        name="Test Health System",
        slug="test-health",
        schema_name="test_health",
        subscription_tier=Organization.SubscriptionTier.ENTERPRISE,
        is_active=True,
    )


@pytest.fixture
def other_tenant(db):
    """Create a second tenant for isolation tests."""
    return Organization.objects.create(
        name="Other Health System",
        slug="other-health",
        schema_name="other_health",
        subscription_tier=Organization.SubscriptionTier.BASIC,
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """Create a physician user linked to the test tenant."""
    return User.objects.create_user(
        email="drsmith@test.com",
        password="SecureP@ssw0rd!123",
        first_name="Jane",
        last_name="Smith",
        role=User.Role.PHYSICIAN,
        tenant=tenant,
    )


@pytest.fixture
def nurse_user(db, tenant):
    """Create a nurse user linked to the test tenant."""
    return User.objects.create_user(
        email="nurse@test.com",
        password="SecureP@ssw0rd!123",
        first_name="Mary",
        last_name="Johnson",
        role=User.Role.NURSE,
        tenant=tenant,
    )


@pytest.fixture
def patient_user(db, tenant):
    """Create a patient user linked to the test tenant."""
    return User.objects.create_user(
        email="patient@test.com",
        password="SecureP@ssw0rd!123",
        first_name="John",
        last_name="Doe",
        role=User.Role.PATIENT,
        tenant=tenant,
    )


@pytest.fixture
def billing_user(db, tenant):
    """Create a billing specialist user."""
    return User.objects.create_user(
        email="billing@test.com",
        password="SecureP@ssw0rd!123",
        first_name="Bob",
        last_name="Biller",
        role=User.Role.BILLING,
        tenant=tenant,
    )


@pytest.fixture
def other_tenant_user(db, other_tenant):
    """Create a user belonging to a different tenant."""
    return User.objects.create_user(
        email="other@other.com",
        password="SecureP@ssw0rd!123",
        first_name="Other",
        last_name="User",
        role=User.Role.PHYSICIAN,
        tenant=other_tenant,
    )


@pytest.fixture
def patient(db, tenant):
    """Create a FHIR Patient resource."""
    return FHIRPatient.objects.create(
        tenant=tenant,
        fhir_id=str(uuid.uuid4()),
        mrn="MRN-TEST-001",
        first_name="John",
        last_name="Doe",
        birth_date="1985-06-15",
        gender="male",
        phone="555-0100",
        email="john.doe@example.com",
        active=True,
    )


@pytest.fixture
def other_tenant_patient(db, other_tenant):
    """Create a FHIR Patient in the other tenant for isolation tests."""
    return FHIRPatient.objects.create(
        tenant=other_tenant,
        fhir_id=str(uuid.uuid4()),
        mrn="MRN-OTHER-001",
        first_name="Other",
        last_name="Patient",
        birth_date="1990-01-01",
        gender="female",
        active=True,
    )


@pytest.fixture
def api_client():
    """Unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """API client authenticated as the physician user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def nurse_client(api_client, nurse_user):
    """API client authenticated as a nurse."""
    client = APIClient()
    client.force_authenticate(user=nurse_user)
    return client


@pytest.fixture
def patient_client(api_client, patient_user):
    """API client authenticated as a patient."""
    client = APIClient()
    client.force_authenticate(user=patient_user)
    return client


@pytest.fixture
def billing_client(api_client, billing_user):
    """API client authenticated as a billing specialist."""
    client = APIClient()
    client.force_authenticate(user=billing_user)
    return client


@pytest.fixture
def other_tenant_client(api_client, other_tenant_user):
    """API client authenticated as a user from a different tenant."""
    client = APIClient()
    client.force_authenticate(user=other_tenant_user)
    return client
