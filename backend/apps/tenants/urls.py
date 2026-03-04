"""URL configuration for the tenants app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import APIKeyViewSet, CurrentOrganizationView, OrganizationViewSet, TenantConfigView

app_name = "tenants"

router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("api-keys", APIKeyViewSet, basename="api-key")

urlpatterns = [
    path("", include(router.urls)),
    path("current/", CurrentOrganizationView.as_view(), name="current-org"),
    path("current/config/", TenantConfigView.as_view(), name="tenant-config"),
]
