"""SDOH assessment views."""

import logging

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import CanAccessPHI

from .models import SDOHAssessment
from .serializers import SDOHAssessmentSerializer

logger = logging.getLogger("apps.sdoh")


class SDOHAssessmentViewSet(ModelViewSet):
    """SDOH assessment CRUD with risk scoring."""

    serializer_class = SDOHAssessmentSerializer
    permission_classes = [CanAccessPHI]
    filterset_fields = ["overall_sdoh_risk", "patient"]
    ordering = ["-assessment_date"]

    def get_queryset(self):
        qs = SDOHAssessment.objects.filter(
            tenant=(getattr(self.request, 'tenant', None) or self.request.user.tenant)
        ).select_related("patient", "assessed_by")
        # Accept patient_id as alias for patient filter param
        patient_id = self.request.query_params.get("patient_id")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs

    @action(detail=False, methods=["get"])
    def high_risk_patients(self, request):
        """Return patients with high SDOH risk."""
        from apps.fhir.serializers import FHIRPatientSerializer
        high_risk = SDOHAssessment.objects.filter(
            tenant=(getattr(request, 'tenant', None) or request.user.tenant),
            overall_sdoh_risk=SDOHAssessment.RiskLevel.HIGH,
        ).select_related("patient").order_by("-total_score")[:50]

        return Response({
            "count": high_risk.count(),
            "assessments": SDOHAssessmentSerializer(high_risk, many=True).data,
        })

    @action(detail=True, methods=["get"])
    def recommendations(self, request, pk=None):
        """Get intervention recommendations for an assessment."""
        assessment = self.get_object()
        return Response({
            "overall_risk": assessment.overall_sdoh_risk,
            "total_score": assessment.total_score,
            "recommendations": assessment.get_intervention_recommendations(),
        })

    @action(detail=True, methods=["post"])
    def update_intervention_status(self, request, pk=None):
        """Update the status of a specific intervention."""
        assessment = self.get_object()
        domain = request.data.get("domain")
        new_status = request.data.get("status")

        if not domain or not new_status:
            return Response({"error": "domain and status required"}, status=status.HTTP_400_BAD_REQUEST)

        interventions = assessment.interventions_recommended or []
        for intervention in interventions:
            if intervention.get("domain") == domain:
                intervention["status"] = new_status

        assessment.interventions_recommended = interventions
        assessment.save(update_fields=["interventions_recommended"])
        return Response({"message": "Intervention status updated."})
