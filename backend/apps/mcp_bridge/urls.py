"""URL configuration for the MCP bridge."""

from django.urls import path

from .views import AgentRecommendationActionView, AgentRecommendationsView, MCPContextView, MCPToolsView

app_name = "mcp"

urlpatterns = [
    path("context/", MCPContextView.as_view(), name="mcp-context"),
    path("tools/", MCPToolsView.as_view(), name="mcp-tools"),
    path("tools/execute/", MCPToolsView.as_view(), name="mcp-tools-execute"),
    # HITL recommendation queue
    path("recommendations/", AgentRecommendationsView.as_view(), name="agent-recommendations"),
    path("recommendations/<uuid:pk>/approve/", AgentRecommendationActionView.as_view(), {"action": "approve"}, name="recommendation-approve"),
    path("recommendations/<uuid:pk>/reject/", AgentRecommendationActionView.as_view(), {"action": "reject"}, name="recommendation-reject"),
]
