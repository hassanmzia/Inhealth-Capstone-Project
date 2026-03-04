"""URL configuration for the MCP bridge."""

from django.urls import path

from .views import MCPContextView, MCPToolsView

app_name = "mcp"

urlpatterns = [
    path("context/", MCPContextView.as_view(), name="mcp-context"),
    path("tools/", MCPToolsView.as_view(), name="mcp-tools"),
    path("tools/execute/", MCPToolsView.as_view(), name="mcp-tools-execute"),
]
