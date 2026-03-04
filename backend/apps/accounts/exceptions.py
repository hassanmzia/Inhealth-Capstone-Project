"""
Custom exception handlers for InHealth API.
Returns consistent error response format across all endpoints.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.accounts")


def custom_exception_handler(exc, context):
    """
    Custom exception handler that wraps all errors in a consistent format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable message",
            "details": { ... }
        }
    }
    """
    # Let DRF handle the response first
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "error": {
                "code": _get_error_code(exc),
                "message": _get_error_message(response.data),
                "details": response.data if isinstance(response.data, dict) else {"detail": response.data},
            }
        }
        response.data = error_data
        return response

    # Handle unhandled exceptions
    if isinstance(exc, Exception):
        logger.exception(f"Unhandled exception in {context.get('view', 'unknown view')}: {exc}")
        return Response(
            {
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return None


def _get_error_code(exc) -> str:
    from rest_framework.exceptions import (
        AuthenticationFailed,
        NotAuthenticated,
        PermissionDenied,
        ValidationError,
        NotFound,
        Throttled,
    )
    code_map = {
        ValidationError: "VALIDATION_ERROR",
        NotAuthenticated: "AUTHENTICATION_REQUIRED",
        AuthenticationFailed: "AUTHENTICATION_FAILED",
        PermissionDenied: "PERMISSION_DENIED",
        NotFound: "NOT_FOUND",
        Throttled: "RATE_LIMITED",
    }
    for exc_class, code in code_map.items():
        if isinstance(exc, exc_class):
            return code
    return "API_ERROR"


def _get_error_message(data) -> str:
    if isinstance(data, dict):
        if "detail" in data:
            detail = data["detail"]
            if hasattr(detail, "string"):
                return str(detail)
            return str(detail)
        # Collect first validation error message
        for field, errors in data.items():
            if isinstance(errors, list) and errors:
                return f"{field}: {errors[0]}"
            if isinstance(errors, str):
                return f"{field}: {errors}"
    if isinstance(data, list) and data:
        return str(data[0])
    return "An error occurred."
