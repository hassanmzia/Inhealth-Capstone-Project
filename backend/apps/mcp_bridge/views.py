"""MCP bridge views — context retrieval and tool execution."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanAccessPHI

from .context_builder import MCPContextBuilder
from .tool_executor import MCPToolExecutor

logger = logging.getLogger("apps.mcp_bridge")


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
