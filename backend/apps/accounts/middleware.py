"""
Audit middleware for automatic PHI access logging.
"""

import logging
import re

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("inhealth.audit")

# URL patterns that indicate PHI access
PHI_URL_PATTERNS = [
    re.compile(r"/api/v1/patients/"),
    re.compile(r"/api/v1/fhir/"),
    re.compile(r"/api/v1/clinical/"),
    re.compile(r"/api/v1/research/"),
    re.compile(r"/api/v1/sdoh/"),
]


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware that logs all authenticated API requests for HIPAA audit compliance.
    PHI access is flagged based on URL pattern matching.
    """

    def process_response(self, request, response):
        # Only log authenticated API requests
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        if not request.path.startswith("/api/"):
            return response

        # Skip health check and schema endpoints
        if request.path in ("/api/v1/health/", "/api/v1/schema/"):
            return response

        phi_accessed = any(p.search(request.path) for p in PHI_URL_PATTERNS)

        # Only audit PHI-related access and write operations
        if phi_accessed or request.method not in ("GET", "HEAD", "OPTIONS"):
            action_map = {
                "GET": "read",
                "POST": "create",
                "PUT": "update",
                "PATCH": "update",
                "DELETE": "delete",
            }
            action = action_map.get(request.method, request.method.lower())

            logger.info(
                "api_access",
                extra={
                    "user_id": str(request.user.id),
                    "user_email": request.user.email,
                    "tenant_id": str(request.user.tenant_id) if request.user.tenant_id else None,
                    "action": action,
                    "path": request.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "ip_address": self._get_client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "phi_accessed": phi_accessed,
                    "timestamp": timezone.now().isoformat(),
                },
            )

            # Async audit log creation to avoid slowing down the response
            if phi_accessed:
                try:
                    from .tasks import create_audit_log_async
                    create_audit_log_async.delay(
                        user_id=str(request.user.id),
                        action=action,
                        resource_type=self._extract_resource_type(request.path),
                        ip_address=self._get_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                        phi_accessed=phi_accessed,
                        tenant_id=str(request.user.tenant_id) if request.user.tenant_id else None,
                    )
                except Exception:
                    pass  # Never block response for audit logging

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def _extract_resource_type(path: str) -> str:
        """Extract resource type from API path."""
        parts = [p for p in path.split("/") if p and p not in ("api", "v1")]
        return parts[0] if parts else "unknown"
