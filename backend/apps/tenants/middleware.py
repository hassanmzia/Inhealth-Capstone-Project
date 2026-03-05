"""
Custom tenant middleware for InHealth.

Extends TenantMainMiddleware with two fallback strategies:

1. JWT-based tenant resolution: when the HTTP domain is not registered as a
   tenant (common in local dev / Docker environments where requests arrive via
   localhost, 127.0.0.1, or a container IP), the middleware decodes the Bearer
   token from the Authorization header and reads the ``tenantId`` claim that is
   embedded at login time.  This allows every authenticated API request to be
   served from the correct tenant schema even when no domain row exists.

2. Public-schema fallback: unauthenticated requests (health-checks, login,
   token-refresh, etc.) that arrive without a valid JWT still fall back to the
   public schema so that shared-app endpoints continue to work.
"""

import logging

from django.db import connection
from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name

logger = logging.getLogger("apps.tenants")


class PublicFallbackTenantMiddleware(TenantMainMiddleware):
    """
    Drop-in replacement for TenantMainMiddleware.

    Resolution order for requests whose HTTP domain is not in tenants_domain:
      1. Bearer token  →  tenantId claim  →  Organization.schema_name
      2. Public schema (unauthenticated / no valid token)
    """

    def process_request(self, request):
        try:
            super().process_request(request)
        except self.TENANT_NOT_FOUND_EXCEPTION:
            if self._set_schema_from_jwt(request):
                return
            if self._set_schema_from_primary_domain(request):
                return
            connection.set_schema(get_public_schema_name())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_schema_from_jwt(self, request) -> bool:
        """
        Decode the Bearer token and switch the DB connection to the tenant
        schema indicated by the ``tenantId`` claim.

        Returns True on success, False on any failure.
        """
        try:
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if not auth_header.startswith("Bearer "):
                return False

            raw_token = auth_header.split(" ", 1)[1]

            # Use simplejwt's UntypedToken so we don't need to import the
            # concrete token class (avoids circular-import risks).
            from rest_framework_simplejwt.tokens import UntypedToken

            validated = UntypedToken(raw_token)
            tenant_id = validated.get("tenantId")
            if not tenant_id:
                return False

            from apps.tenants.models import Organization

            org = Organization.objects.get(pk=tenant_id)
            connection.set_schema(org.schema_name)
            request.tenant = org
            logger.debug(
                "Tenant schema set from JWT: schema=%s (tenant_id=%s)",
                org.schema_name,
                tenant_id,
            )
            return True

        except Exception as exc:  # noqa: BLE001
            logger.debug("JWT-based tenant resolution failed: %s", exc)
            return False

    def _set_schema_from_primary_domain(self, request) -> bool:
        """
        Last-resort fallback: use the primary domain's tenant.

        Handles the case where an admin user (tenant_id=None) accesses the API
        via a non-registered hostname (e.g. the server's LAN IP in dev).
        Only activates when exactly one active organization exists, to avoid
        silently routing requests to the wrong tenant in multi-tenant setups.
        """
        try:
            from apps.tenants.models import Domain, Organization

            active_orgs = Organization.objects.filter(is_active=True)
            # Safety: only fall back automatically in single-tenant deployments
            if active_orgs.count() != 1:
                return False

            primary = (
                Domain.objects.filter(is_primary=True)
                .select_related("tenant")
                .first()
            )
            if primary is None:
                return False

            connection.set_schema(primary.tenant.schema_name)
            request.tenant = primary.tenant
            logger.debug(
                "Tenant schema set from primary-domain fallback: schema=%s",
                primary.tenant.schema_name,
            )
            return True

        except Exception as exc:  # noqa: BLE001
            logger.debug("Primary-domain fallback failed: %s", exc)
            return False
