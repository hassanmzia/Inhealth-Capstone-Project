"""
Views for tenant / organization management.
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsOrgAdmin, IsSuperAdmin

from .models import APIKey, Organization, TenantConfig
from .serializers import (
    APIKeyCreateSerializer,
    APIKeySerializer,
    OrganizationSerializer,
    TenantConfigSerializer,
)


class OrganizationViewSet(ModelViewSet):
    """CRUD for organizations (super admin only)."""

    serializer_class = OrganizationSerializer
    permission_classes = [IsSuperAdmin]
    queryset = Organization.objects.all()
    lookup_field = "slug"

    def get_queryset(self):
        return Organization.objects.all().order_by("name")


class CurrentOrganizationView(generics.RetrieveUpdateAPIView):
    """GET/PATCH the current user's organization (org admin)."""

    serializer_class = OrganizationSerializer
    permission_classes = [IsOrgAdmin]

    def get_object(self):
        return (getattr(self.request, 'tenant', None) or self.request.user.tenant)


class TenantConfigView(generics.RetrieveUpdateAPIView):
    """GET/PATCH tenant configuration."""

    serializer_class = TenantConfigSerializer
    permission_classes = [IsOrgAdmin]

    def get_object(self):
        config, _ = TenantConfig.objects.get_or_create(
            organization=(getattr(self.request, 'tenant', None) or self.request.user.tenant)
        )
        return config


class APIKeyViewSet(ModelViewSet):
    """API key management for the current tenant."""

    permission_classes = [IsOrgAdmin]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "create":
            return APIKeyCreateSerializer
        return APIKeySerializer

    def get_queryset(self):
        return APIKey.objects.filter(
            organization=(getattr(self.request, 'tenant', None) or self.request.user.tenant)
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            organization=(getattr(self.request, 'tenant', None) or self.request.user.tenant),
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def revoke(self, request, id=None):
        """Immediately revoke an API key."""
        api_key = self.get_object()
        api_key.is_active = False
        api_key.save(update_fields=["is_active"])
        return Response({"message": "API key revoked successfully."})
