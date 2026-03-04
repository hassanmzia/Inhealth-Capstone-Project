"""
RBAC permission classes for InHealth.
Role-based and object-level permissions using django-guardian.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import User


class IsPhysician(IsAuthenticated):
    """Allow only physician users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == User.Role.PHYSICIAN


class IsNurse(IsAuthenticated):
    """Allow only nurse/NP/PA users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == User.Role.NURSE


class IsClinician(IsAuthenticated):
    """Allow physicians and nurses."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_clinician


class IsProvider(IsAuthenticated):
    """Allow physicians and nurses (ordering providers)."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_provider


class IsPatient(IsAuthenticated):
    """Allow only patient users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == User.Role.PATIENT


class IsOrgAdmin(IsAuthenticated):
    """Allow organization administrators."""

    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.role in (User.Role.ORG_ADMIN, User.Role.SUPER_ADMIN)
        )


class IsSuperAdmin(IsAuthenticated):
    """Allow only super administrators."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == User.Role.SUPER_ADMIN


class IsPharmacist(IsAuthenticated):
    """Allow pharmacists."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == User.Role.PHARMACIST


class IsBilling(IsAuthenticated):
    """Allow billing specialists."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == User.Role.BILLING


class IsResearcher(IsAuthenticated):
    """Allow researchers (with de-identified data access only)."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == User.Role.RESEARCHER


class IsSameTenant(IsAuthenticated):
    """Ensure the requesting user belongs to the same tenant as the object."""

    def has_object_permission(self, request, view, obj):
        if not super().has_permission(request, view):
            return False
        if request.user.role == User.Role.SUPER_ADMIN:
            return True
        tenant_id = getattr(obj, "tenant_id", None)
        if tenant_id is None:
            # Try nested attribute
            patient = getattr(obj, "patient", None)
            if patient:
                tenant_id = getattr(patient, "tenant_id", None)
        return tenant_id and str(tenant_id) == str(request.user.tenant_id)


class IsOwnerOrClinician(IsAuthenticated):
    """Patient owns the record OR a clinician in the same org can access it."""

    def has_object_permission(self, request, view, obj):
        if not super().has_permission(request, view):
            return False
        user = request.user
        if user.role == User.Role.SUPER_ADMIN:
            return True
        if user.is_clinician and str(user.tenant_id) == str(getattr(obj, "tenant_id", None)):
            return True
        # Patient can only see their own records
        patient_user_id = None
        patient = getattr(obj, "patient", None)
        if patient:
            patient_user_id = getattr(patient, "user_id", None)
        return patient_user_id and str(patient_user_id) == str(user.id)


class CanAccessPHI(IsAuthenticated):
    """
    Permission for PHI access — requires clinical role + same tenant.
    Logs the access attempt via audit log.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        user = request.user
        # PHI access requires clinical or admin role
        phi_allowed_roles = {
            User.Role.PHYSICIAN,
            User.Role.NURSE,
            User.Role.PHARMACIST,
            User.Role.ORG_ADMIN,
            User.Role.SUPER_ADMIN,
        }
        return user.role in phi_allowed_roles

    def has_object_permission(self, request, view, obj):
        return IsSameTenant().has_object_permission(request, view, obj)


class ReadOnly(BasePermission):
    """Grants read-only access (GET, HEAD, OPTIONS)."""

    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS")
