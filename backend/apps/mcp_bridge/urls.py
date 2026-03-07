"""URL configuration for the MCP bridge."""

from django.urls import path

from .views import (
    AgentExecutionsView,
    AgentHITLDecideView,
    AgentHITLView,
    AgentPauseView,
    AgentRecommendationActionView,
    AgentRecommendationsView,
    AgentResumeView,
    AgentSingleStatusView,
    AgentStatusView,
    AgentTriggerView,
    MCPContextView,
    MCPToolsView,
    MonitoringPauseView,
    MonitoringResumeView,
)

app_name = "mcp"

urlpatterns = [
    path("context/", MCPContextView.as_view(), name="mcp-context"),
    path("tools/", MCPToolsView.as_view(), name="mcp-tools"),
    path("tools/execute/", MCPToolsView.as_view(), name="mcp-tools-execute"),
    # Agent status & execution history
    path("status/", AgentStatusView.as_view(), name="agent-status"),
    path("executions/", AgentExecutionsView.as_view(), name="agent-executions"),
    # HITL
    path("hitl/", AgentHITLView.as_view(), name="agent-hitl"),
    path("hitl/<uuid:pk>/decide/", AgentHITLDecideView.as_view(), name="agent-hitl-decide"),
    # Recommendations (legacy alias — same data, different shape)
    path("recommendations/", AgentRecommendationsView.as_view(), name="agent-recommendations"),
    path("recommendations/<uuid:pk>/approve/", AgentRecommendationActionView.as_view(), {"action": "approve"}, name="recommendation-approve"),
    path("recommendations/<uuid:pk>/reject/", AgentRecommendationActionView.as_view(), {"action": "reject"}, name="recommendation-reject"),
    # Monitoring controls (patient-level) — must come before <str:agent_id> wildcard
    path("monitoring/pause/", MonitoringPauseView.as_view(), name="monitoring-pause"),
    path("monitoring/resume/", MonitoringResumeView.as_view(), name="monitoring-resume"),
    # Per-agent actions (trigger, status, pause, resume)
    path("<str:agent_id>/trigger/", AgentTriggerView.as_view(), name="agent-trigger"),
    path("<str:agent_id>/status/", AgentSingleStatusView.as_view(), name="agent-single-status"),
    path("<str:agent_id>/pause/", AgentPauseView.as_view(), name="agent-pause"),
    path("<str:agent_id>/resume/", AgentResumeView.as_view(), name="agent-resume"),
]
