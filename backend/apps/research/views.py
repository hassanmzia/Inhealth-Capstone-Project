"""Research and evidence views."""

import logging

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.permissions import CanAccessPHI

from .models import ClinicalTrial, MedicalEvidence, ResearchQuery
from .serializers import ClinicalTrialSerializer, MedicalEvidenceSerializer, ResearchQuerySerializer
from .tasks import process_research_query

logger = logging.getLogger("apps.research")


class ResearchQueryViewSet(ModelViewSet):
    """Research query submission and result retrieval."""

    serializer_class = ResearchQuerySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["query_type", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return ResearchQuery.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("requested_by", "patient")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.save()

        # Dispatch async processing
        process_research_query.delay(str(query.id))

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_202_ACCEPTED,
            headers=headers,
        )

    @action(detail=False, methods=["post"])
    def trial_matching(self, request):
        """Match a patient against active clinical trials."""
        patient_id = request.data.get("patient_id")
        if not patient_id:
            return Response({"error": "patient_id required"}, status=status.HTTP_400_BAD_REQUEST)

        query = ResearchQuery.objects.create(
            tenant=request.user.tenant,
            patient_id=patient_id,
            query_text=f"Find clinical trials for patient {patient_id}",
            query_type=ResearchQuery.QueryType.TRIAL_MATCHING,
            requested_by=request.user,
        )
        process_research_query.delay(str(query.id))
        return Response({"query_id": str(query.id), "message": "Trial matching queued."}, status=status.HTTP_202_ACCEPTED)


class ClinicalTrialViewSet(ReadOnlyModelViewSet):
    """Clinical trial search and retrieval."""

    serializer_class = ClinicalTrialSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "phase", "condition"]
    search_fields = ["title", "brief_summary", "condition"]
    ordering = ["-last_updated"]

    def get_queryset(self):
        qs = ClinicalTrial.objects.filter(status=ClinicalTrial.Status.RECRUITING)
        if self.request.query_params.get("condition"):
            qs = qs.filter(condition__icontains=self.request.query_params["condition"])
        return qs


class MedicalEvidenceViewSet(ReadOnlyModelViewSet):
    """Medical literature evidence search."""

    serializer_class = MedicalEvidenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["evidence_level", "year"]
    search_fields = ["title", "abstract", "journal"]
    ordering = ["-year", "-citation_count"]
    queryset = MedicalEvidence.objects.all()

    @action(detail=False, methods=["post"])
    def semantic_search(self, request):
        """Semantic search via vector embeddings (Qdrant)."""
        query = request.data.get("query")
        if not query:
            return Response({"error": "query required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from vector.rag import RAGPipeline
            pipeline = RAGPipeline()
            results = pipeline.retrieve(query, collection="medical_literature", top_k=10)
            return Response({"results": results})
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return Response({"error": "Search temporarily unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
