"""
Custom tenant middleware for InHealth.

Extends TenantMainMiddleware to fall back to the public schema when a
request arrives from a domain that is not registered as a tenant (e.g.
internal health-check probes from Docker / Kubernetes, or Prometheus
scraping via the container hostname).  Without this, every such request
receives a bare 404 before URL routing even runs, which prevents the
Docker health check from ever succeeding.
"""

from django.db import connection
from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name


class PublicFallbackTenantMiddleware(TenantMainMiddleware):
    """
    Drop-in replacement for TenantMainMiddleware.

    Behaviour is identical for recognised tenant domains.  For any domain
    that has no matching row in tenants_domain, the request is served from
    the public schema instead of raising Http404.  Authentication and
    permission checks still apply to all views.
    """

    def process_request(self, request):
        try:
            super().process_request(request)
        except self.TENANT_NOT_FOUND_EXCEPTION:
            connection.set_schema(get_public_schema_name())
