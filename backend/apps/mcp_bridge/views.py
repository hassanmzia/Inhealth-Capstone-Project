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
        tenant = (getattr(request, 'tenant', None) or request.user.tenant)
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
                tenant=(getattr(request, 'tenant', None) or request.user.tenant),
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


class AgentTriggerView(APIView):
    """
    POST /api/v1/agents/<agent_id>/trigger/
    Triggers a specific agent for a patient. Creates an AgentActionLog entry
    and returns the execution record. In production this would dispatch to
    the actual agent pipeline via Celery; for now it records the trigger.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, agent_id):
        patient_id = request.data.get("patient_id")
        priority = request.data.get("priority", "normal")
        input_data = request.data.get("input", {})

        try:
            from apps.fhir.models import AgentActionLog, FHIRPatient
            from django.utils import timezone as tz
            import uuid

            tenant = getattr(request, 'tenant', None) or request.user.tenant

            # Validate patient exists if provided
            patient = None
            patient_name = "Unknown"
            if patient_id:
                try:
                    patient = FHIRPatient.objects.get(id=patient_id, tenant=tenant)
                    patient_name = f"{patient.first_name} {patient.last_name}"
                except FHIRPatient.DoesNotExist:
                    return Response(
                        {"error": f"Patient {patient_id} not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            # Create execution log
            log = AgentActionLog.objects.create(
                tenant=tenant,
                patient=patient,
                agent_type=agent_id,
                action_type=AgentActionLog.ActionType.ANALYSIS,
                action_details=f"Manual trigger by {request.user.email} (priority: {priority})",
                input_context={
                    "trigger_source": "manual",
                    "triggered_by": str(request.user.id),
                    "priority": priority,
                    "input": input_data,
                },
                output={
                    "status": "queued",
                    "message": f"Agent {agent_id} triggered successfully",
                },
            )

            # TODO: In production, dispatch to Celery task here:
            # from apps.mcp_bridge.tasks import run_agent
            # run_agent.delay(agent_id=agent_id, patient_id=patient_id, ...)

            return Response({
                "id": str(log.id),
                "agentId": agent_id,
                "agentName": agent_id.replace("_", " ").title(),
                "tier": "tier1_monitoring",
                "status": "queued",
                "patientId": str(patient_id) if patient_id else None,
                "patientName": patient_name,
                "triggeredBy": request.user.email,
                "triggeredAt": log.created_at.isoformat(),
                "startedAt": log.created_at.isoformat(),
                "completedAt": None,
                "input": input_data,
                "output": {},
            })
        except Exception as exc:
            logger.error("Agent trigger failed: %s", exc)
            return Response(
                {"error": f"Failed to trigger agent: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AgentSingleStatusView(APIView):
    """
    GET /api/v1/agents/<agent_id>/status/
    Returns status for a single agent.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, agent_id):
        try:
            from apps.fhir.models import AgentActionLog
            from django.utils import timezone

            tenant = getattr(request, 'tenant', None) or request.user.tenant
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            qs = AgentActionLog.objects.filter(tenant=tenant, agent_type=agent_id)
            last_log = qs.order_by("-created_at").first()
            executions_today = qs.filter(created_at__gte=today_start).count()

            return Response({
                "agentId": agent_id,
                "agentName": agent_id.replace("_", " ").title(),
                "status": "idle",
                "tier": "tier1_monitoring",
                "lastRun": last_log.created_at.isoformat() if last_log else None,
                "nextScheduledRun": None,
                "executionsToday": executions_today,
                "averageRuntime": 0.0,
                "successRate": 100,
                "queueDepth": 0,
            })
        except Exception as exc:
            logger.debug("single agent status query failed: %s", exc)
            return Response({
                "agentId": agent_id,
                "agentName": agent_id.replace("_", " ").title(),
                "status": "unknown",
                "tier": "unknown",
            })


class AgentPauseView(APIView):
    """
    POST /api/v1/agents/<agent_id>/pause/
    Pauses a specific agent (stub — records the action).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, agent_id):
        logger.info("Agent %s paused by %s", agent_id, request.user.email)
        return Response({"agentId": agent_id, "status": "paused"})


class AgentResumeView(APIView):
    """
    POST /api/v1/agents/<agent_id>/resume/
    Resumes a specific agent (stub — records the action).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, agent_id):
        logger.info("Agent %s resumed by %s", agent_id, request.user.email)
        return Response({"agentId": agent_id, "status": "idle"})


class MonitoringPauseView(APIView):
    """POST /api/v1/agents/monitoring/pause/ — pauses monitoring for a patient."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        patient_id = request.data.get("patient_id")
        logger.info("Monitoring paused for patient %s by %s", patient_id, request.user.email)
        return Response({"patientId": patient_id, "status": "paused"})


class MonitoringResumeView(APIView):
    """POST /api/v1/agents/monitoring/resume/ — resumes monitoring for a patient."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        patient_id = request.data.get("patient_id")
        logger.info("Monitoring resumed for patient %s by %s", patient_id, request.user.email)
        return Response({"patientId": patient_id, "status": "active"})


class AgentStatusView(APIView):
    """
    GET /api/v1/agents/status/
    Returns current status of all known agent types.
    """

    permission_classes = [permissions.IsAuthenticated]

    # Static registry of all agent types in the system
    _AGENT_REGISTRY = [
        ("vitals_monitor",       "Vitals Monitor",       "tier1_ingestion"),
        ("lab_analyzer",         "Lab Analyzer",         "tier2_analysis"),
        ("risk_stratifier",      "Risk Stratifier",      "tier2_analysis"),
        ("care_gap_detector",    "Care Gap Detector",    "tier3_clinical"),
        ("medication_reviewer",  "Medication Reviewer",  "tier3_clinical"),
        ("care_plan_optimizer",  "Care Plan Optimizer",  "tier4_coordination"),
        ("patient_engagement",   "Patient Engagement",   "tier5_engagement"),
    ]

    def get(self, request):
        results = []
        try:
            from apps.fhir.models import AgentActionLog
            from django.utils import timezone
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

            for agent_id, agent_name, tier in self._AGENT_REGISTRY:
                last_log = None
                executions_today = 0
                avg_runtime = 0.0
                try:
                    qs = AgentActionLog.objects.filter(
                        tenant=(getattr(request, 'tenant', None) or request.user.tenant),
                        agent_type=agent_id,
                    )
                    last_log = qs.order_by("-created_at").first()
                    executions_today = qs.filter(created_at__gte=today_start).count()
                except Exception:
                    pass

                results.append({
                    "agentId": agent_id,
                    "agentName": agent_name,
                    "status": "idle",
                    "tier": tier,
                    "lastRun": last_log.created_at.isoformat() if last_log else None,
                    "nextScheduledRun": None,
                    "executionsToday": executions_today,
                    "averageRuntime": avg_runtime,
                    "successRate": 100,
                    "queueDepth": 0,
                })
        except Exception as exc:
            logger.debug("agent status query failed: %s", exc)

        return Response(results)


class AgentExecutionsView(APIView):
    """
    GET /api/v1/agents/executions/
    Returns paginated agent execution history from AgentActionLog.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.core.paginator import Paginator
        page_num = max(int(request.query_params.get("page", 1)), 1)
        page_size = min(int(request.query_params.get("page_size", 50)), 200)

        results = []
        total = 0
        try:
            from apps.fhir.models import AgentActionLog
            qs = AgentActionLog.objects.filter(tenant=(getattr(request, 'tenant', None) or request.user.tenant)).order_by("-created_at")

            # Optional filters
            agent_id_param = request.query_params.get("agent_id")
            patient_id_param = request.query_params.get("patient_id")
            status_param = request.query_params.get("status")
            if agent_id_param:
                qs = qs.filter(agent_type=agent_id_param)
            if patient_id_param:
                qs = qs.filter(patient_id=patient_id_param)

            total = qs.count()
            paginator = Paginator(qs, page_size)
            page_obj = paginator.get_page(page_num)

            for log in page_obj.object_list:
                patient_name = "Unknown"
                try:
                    if log.patient:
                        patient_name = f"{log.patient.first_name} {log.patient.last_name}"
                except Exception:
                    pass

                results.append({
                    "id": str(log.id),
                    "agentId": log.agent_type,
                    "agentName": log.agent_type.replace("_", " ").title(),
                    "tier": "tier2_analysis",
                    "status": "completed",
                    "patientId": str(log.patient_id) if log.patient_id else None,
                    "patientName": patient_name,
                    "triggeredBy": "system",
                    "triggeredAt": log.created_at.isoformat(),
                    "startedAt": log.created_at.isoformat(),
                    "completedAt": log.updated_at.isoformat() if hasattr(log, "updated_at") else log.created_at.isoformat(),
                    "input": log.input_context or {},
                    "output": log.output or {},
                })
        except Exception as exc:
            logger.debug("executions query failed: %s", exc)

        return Response({
            "count": total,
            "next": None,
            "previous": None,
            "results": results,
        })


class AgentHITLView(APIView):
    """
    GET  /api/v1/agents/hitl/?status=pending
    POST /api/v1/agents/hitl/<id>/decide/
    Human-in-the-loop request list and decision endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get("status", "pending")
        patient_id_param = request.query_params.get("patient_id")
        agent_id_param = request.query_params.get("agent_id")

        results = []
        try:
            from apps.fhir.models import AgentActionLog
            qs = AgentActionLog.objects.filter(
                tenant=(getattr(request, 'tenant', None) or request.user.tenant),
                action_type=AgentActionLog.ActionType.RECOMMENDATION,
            ).select_related("patient").order_by("-created_at")

            if status_filter == "pending":
                qs = qs.filter(reviewed_by_id__isnull=True)
            elif status_filter == "decided":
                qs = qs.filter(reviewed_by_id__isnull=False)
            if patient_id_param:
                qs = qs.filter(patient_id=patient_id_param)
            if agent_id_param:
                qs = qs.filter(agent_type=agent_id_param)

            for log in qs[:100]:
                output = log.output or {}
                patient_name = "Unknown"
                try:
                    if log.patient:
                        patient_name = f"{log.patient.first_name} {log.patient.last_name}"
                except Exception:
                    pass

                decision = None
                if log.reviewed_by_id:
                    decision = "approved" if log.was_accepted else "rejected"

                results.append({
                    "id": str(log.id),
                    "executionId": str(log.id),
                    "agentId": log.agent_type,
                    "agentName": log.agent_type.replace("_", " ").title(),
                    "patientId": str(log.patient_id) if log.patient_id else "",
                    "patientName": patient_name,
                    "requestType": "approve_recommendation",
                    "title": output.get("title", "Agent Recommendation"),
                    "description": output.get("description", ""),
                    "recommendation": output.get("recommendation", ""),
                    "evidenceLevel": output.get("evidence_level", "C"),
                    "confidence": output.get("confidence", 75),
                    "urgency": output.get("priority", "routine"),
                    "status": "decided" if decision else "pending",
                    "decision": decision,
                    "createdAt": log.created_at.isoformat(),
                    "expiresAt": output.get("expires_at"),
                })
        except Exception as exc:
            logger.debug("hitl query failed: %s", exc)

        return Response(results)


class AgentHITLDecideView(APIView):
    """POST /api/v1/agents/hitl/<id>/decide/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        decision = request.data.get("decision")
        if decision not in ("approved", "rejected", "modified", "escalated", "deferred"):
            return Response({"error": "invalid decision"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from apps.fhir.models import AgentActionLog
            from django.utils import timezone as tz
            log = AgentActionLog.objects.get(pk=pk, tenant=(getattr(request, 'tenant', None) or request.user.tenant))
            log.reviewed_by_id = request.user.id
            log.was_accepted = decision in ("approved", "modified")
            log.reviewed_at = tz.now()
            log.save(update_fields=["reviewed_by_id", "was_accepted", "reviewed_at"])
            return Response({"id": str(log.id), "decision": decision})
        except Exception as exc:
            logger.debug("hitl decide failed: %s", exc)
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class MCPContextView(APIView):
    """
    GET /api/v1/mcp/context/?patient_id=<id>
    Returns structured MCP context for a patient (used by AI agents).
    """

    permission_classes = [CanAccessPHI]

    def get(self, request):
        patient_id = request.query_params.get("patient_id")
        cohort_id = request.query_params.get("cohort_id")

        builder = MCPContextBuilder(tenant=(getattr(request, 'tenant', None) or request.user.tenant))

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
        builder = MCPContextBuilder(tenant=(getattr(request, 'tenant', None) or request.user.tenant))
        return Response({"tools": builder.build_tool_list()})

    def post(self, request):
        tool_name = request.data.get("tool")
        parameters = request.data.get("parameters", {})

        if not tool_name:
            return Response(
                {"error": "tool name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        executor = MCPToolExecutor(tenant=(getattr(request, 'tenant', None) or request.user.tenant), user=request.user)
        result = executor.execute(tool_name, parameters)

        if result.get("status") == "error":
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)
