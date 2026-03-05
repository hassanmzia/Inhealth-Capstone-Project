"""MCP bridge views — context retrieval and tool execution."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanAccessPHI

from .context_builder import MCPContextBuilder
from .tool_executor import MCPToolExecutor

logger = logging.getLogger("apps.mcp_bridge")


class AgentRecommendationsView(APIView):
    """
    GET /api/v1/agents/recommendations/
    Returns AI agent recommendations (HITL review queue).
    Params: patient_id, status (pending|approved|rejected), limit

    POST /api/v1/agents/recommendations/<id>/approve/
    POST /api/v1/agents/recommendations/<id>/reject/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = request.user.tenant
        patient_id = request.query_params.get("patient_id")
        status_filter = request.query_params.get("status", "pending")
        try:
            limit = min(int(request.query_params.get("limit", 20)), 100)
        except (ValueError, TypeError):
            limit = 20

        results = []
        try:
            from apps.fhir.models import AgentActionLog
            qs = AgentActionLog.objects.filter(
                tenant=tenant,
                action_type=AgentActionLog.ActionType.RECOMMENDATION,
            )
            if patient_id:
                qs = qs.filter(patient_id=patient_id)
            if status_filter == "pending":
                qs = qs.filter(reviewed_by_id__isnull=True)
            elif status_filter == "approved":
                qs = qs.filter(reviewed_by_id__isnull=False, was_accepted=True)
            elif status_filter == "rejected":
                qs = qs.filter(reviewed_by_id__isnull=False, was_accepted=False)

            for log in qs.select_related("patient").order_by("-created_at")[:limit]:
                output = log.output or {}
                try:
                    patient_name = (
                        f"{log.patient.first_name} {log.patient.last_name}"
                        if log.patient else "Unknown"
                    )
                except Exception:
                    patient_name = "Unknown"

                rec_status = "pending"
                if log.reviewed_by_id:
                    rec_status = "approved" if log.was_accepted else "rejected"

                results.append({
                    "id": str(log.id),
                    "agentId": log.agent_type,
                    "agentName": log.agent_type.replace("_", " ").title(),
                    "patientId": str(log.patient_id) if log.patient_id else "",
                    "patientName": patient_name,
                    "title": output.get("title", "Agent Recommendation"),
                    "recommendation": output.get("recommendation", output.get("detail", "")),
                    "evidenceLevel": output.get("evidence_level", "C"),
                    "confidence": output.get("confidence", 0.75),
                    "sourceGuideline": output.get("source_guideline", ""),
                    "sourceUrl": output.get("source_url", ""),
                    "category": output.get("category", log.agent_type),
                    "priority": output.get("priority", "routine"),
                    "status": rec_status,
                    "createdAt": log.created_at.isoformat(),
                    "expiresAt": output.get("expires_at"),
                    "featureImportance": output.get("feature_importance", []),
                })
        except Exception as e:
            logger.debug("recommendations query failed: %s", e)

        return Response(results)


class AgentRecommendationActionView(APIView):
    """
    POST /api/v1/agents/recommendations/<id>/approve/
    POST /api/v1/agents/recommendations/<id>/reject/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, action):
        if action not in ("approve", "reject"):
            return Response({"error": "invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from apps.fhir.models import AgentActionLog
            from django.utils import timezone as tz
            log = AgentActionLog.objects.get(
                pk=pk,
                tenant=request.user.tenant,
                action_type=AgentActionLog.ActionType.RECOMMENDATION,
            )
            log.reviewed_by_id = request.user.id
            log.was_accepted = (action == "approve")
            log.reviewed_at = tz.now()
            log.save(update_fields=["reviewed_by_id", "was_accepted", "reviewed_at"])
            return Response({
                "id": str(log.id),
                "status": "approved" if log.was_accepted else "rejected",
            })
        except Exception as e:
            logger.debug("recommendation action failed: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MCPContextView(APIView):
    """
    GET /api/v1/mcp/context/?patient_id=<id>
    Returns structured MCP context for a patient (used by AI agents).
    """

    permission_classes = [CanAccessPHI]

    def get(self, request):
        patient_id = request.query_params.get("patient_id")
        cohort_id = request.query_params.get("cohort_id")

        builder = MCPContextBuilder(tenant=request.user.tenant)

        if patient_id:
            context = builder.build_patient_context(patient_id)
        elif cohort_id:
            context = builder.build_population_context(cohort_id)
        else:
            context = {"tools": builder.build_tool_list(), "mcp_version": "1.0"}

        return Response(context)


class MCPToolsView(APIView):
    """
    GET /api/v1/mcp/tools/
    List available MCP tools.

    POST /api/v1/mcp/tools/execute
    Execute a specific MCP tool.
    """

    permission_classes = [CanAccessPHI]

    def get(self, request):
        builder = MCPContextBuilder(tenant=request.user.tenant)
        return Response({"tools": builder.build_tool_list()})

    def post(self, request):
        tool_name = request.data.get("tool")
        parameters = request.data.get("parameters", {})

        if not tool_name:
            return Response(
                {"error": "tool name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        executor = MCPToolExecutor(tenant=request.user.tenant, user=request.user)
        result = executor.execute(tool_name, parameters)

        if result.get("status") == "error":
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)
