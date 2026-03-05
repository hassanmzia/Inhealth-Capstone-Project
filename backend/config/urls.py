"""
Root URL configuration for InHealth Chronic Care.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# Health check endpoint (no auth required)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Simple health check endpoint for load balancers."""
    return Response({"status": "healthy", "service": "inhealth-api", "version": "1.0.0"})


api_v1_patterns = [
    # Authentication
    path("auth/", include("apps.accounts.urls", namespace="accounts")),
    # FHIR R4 REST API
    path("fhir/", include("apps.fhir.urls", namespace="fhir")),
    # Patient management
    path("patients/", include("apps.patients.urls", namespace="patients")),
    # Clinical workflows
    path("clinical/", include("apps.clinical.urls", namespace="clinical")),
    # AI Agent control plane
    path("agents/", include("apps.mcp_bridge.urls", namespace="agents")),
    # Population analytics
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    # Research & evidence
    path("research/", include("apps.research.urls", namespace="research")),
    # Notifications
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    # Billing & RPM
    path("billing/", include("apps.billing.urls", namespace="billing")),
    # Tenant / organization management
    path("tenants/", include("apps.tenants.urls", namespace="tenants")),
    # MCP bridge (agent tool execution)
    path("mcp/", include("apps.mcp_bridge.urls", namespace="mcp")),
    # A2A bridge (agent-to-agent communication)
    path("a2a/", include("apps.a2a_bridge.urls", namespace="a2a")),
    # SDOH assessments
    path("sdoh/", include("apps.sdoh.urls", namespace="sdoh")),
    # OpenAPI schema
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-v1:schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="api-v1:schema"), name="redoc"),
]

urlpatterns = [
    # Django admin (only on public schema)
    path("admin/", admin.site.urls),
    # Health check — both /api/health/ (Docker healthcheck) and /api/v1/health/
    path("api/health/", health_check, name="health-check-bare"),
    path("api/v1/health/", health_check, name="health-check"),
    # API v1
    path("api/v1/", include((api_v1_patterns, "api-v1"))),
    # Prometheus metrics
    path("", include("django_prometheus.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
