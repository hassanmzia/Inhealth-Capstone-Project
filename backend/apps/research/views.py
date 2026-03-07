"""Research and evidence views."""

import logging

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.permissions import CanAccessPHI

from .models import ClinicalTrial, MedicalEvidence, ResearchQuery
from .serializers import ClinicalTrialSerializer, MedicalEvidenceSerializer, ResearchQuerySerializer
from .tasks import process_research_query

logger = logging.getLogger("apps.research")


class ResearchSearchView(APIView):
    """
    POST /api/v1/research/search/
    Synchronous search across literature, trials, and guidelines.
    Returns results in the format the frontend expects.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query = request.data.get("query", "").strip()
        query_type = request.data.get("type", "literature")

        if not query:
            return Response(
                {"error": "query is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        answer = None

        if query_type == "literature":
            results = self._search_literature(query)
        elif query_type == "trials":
            results = self._search_trials(query)
        elif query_type == "guidelines":
            results = self._search_guidelines(query)
        elif query_type == "qa":
            results = self._search_literature(query)
            answer = self._generate_qa_answer(query, results)

        # Also log the query for history
        try:
            type_map = {
                "literature": ResearchQuery.QueryType.LITERATURE,
                "trials": ResearchQuery.QueryType.TRIAL_MATCHING,
                "guidelines": ResearchQuery.QueryType.GUIDELINE,
                "qa": ResearchQuery.QueryType.QA,
            }
            tenant = getattr(request, "tenant", None) or request.user.tenant
            ResearchQuery.objects.create(
                tenant=tenant,
                query_text=query,
                query_type=type_map.get(query_type, ResearchQuery.QueryType.QA),
                status=ResearchQuery.Status.COMPLETE,
                requested_by=request.user,
                result={
                    "summary": answer or f"Found {len(results)} results",
                    "result_count": len(results),
                },
                sources=[
                    {"title": r["title"], "url": r.get("url", "")}
                    for r in results[:5]
                ],
            )
        except Exception as exc:
            logger.debug("Failed to log research query: %s", exc)

        response_data = {"results": results}
        if answer is not None:
            response_data["answer"] = answer

        return Response(response_data)

    def _search_literature(self, query):
        """Search MedicalEvidence table."""
        from django.db.models import Q

        terms = query.lower().split()
        q_filter = Q()
        for term in terms:
            q_filter |= Q(title__icontains=term) | Q(abstract__icontains=term) | Q(journal__icontains=term)

        evidence = MedicalEvidence.objects.filter(q_filter).order_by("-year", "-citation_count")[:20]

        return [
            {
                "id": str(e.id),
                "title": e.title,
                "authors": e.authors if isinstance(e.authors, list) else [],
                "abstract": e.abstract,
                "source": e.journal or "PubMed",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{e.pubmed_id}/" if e.pubmed_id else None,
                "evidenceLevel": e.evidence_level,
                "publishedDate": str(e.year),
                "relevanceScore": e.relevance_score or 0.75,
                "type": "literature",
            }
            for e in evidence
        ]

    def _search_trials(self, query):
        """Search ClinicalTrial table."""
        from django.db.models import Q

        terms = query.lower().split()
        q_filter = Q()
        for term in terms:
            q_filter |= Q(title__icontains=term) | Q(brief_summary__icontains=term) | Q(condition__icontains=term)

        trials = ClinicalTrial.objects.filter(q_filter).order_by("-last_updated")[:20]

        return [
            {
                "id": str(t.id),
                "title": t.title,
                "abstract": t.brief_summary,
                "source": f"ClinicalTrials.gov ({t.nct_id})",
                "url": f"https://clinicaltrials.gov/study/{t.nct_id}" if t.nct_id else None,
                "publishedDate": t.start_date.isoformat() if t.start_date else None,
                "relevanceScore": 0.85,
                "type": "trials",
                "trialStatus": t.status,
                "phase": t.phase,
            }
            for t in trials
        ]

    def _search_guidelines(self, query):
        """Search for guideline-related evidence."""
        from django.db.models import Q

        terms = query.lower().split()
        q_filter = Q()
        for term in terms:
            q_filter |= Q(title__icontains=term) | Q(abstract__icontains=term)

        # Look for guideline-type evidence (high evidence level)
        evidence = (
            MedicalEvidence.objects.filter(q_filter)
            .filter(evidence_level="A")
            .order_by("-year", "-citation_count")[:20]
        )

        # If not enough A-level, broaden to all
        if evidence.count() < 3:
            evidence = MedicalEvidence.objects.filter(q_filter).order_by("-year", "-citation_count")[:20]

        return [
            {
                "id": str(e.id),
                "title": e.title,
                "authors": e.authors if isinstance(e.authors, list) else [],
                "abstract": e.abstract,
                "source": e.journal or "Clinical Guidelines",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{e.pubmed_id}/" if e.pubmed_id else None,
                "evidenceLevel": e.evidence_level,
                "publishedDate": str(e.year),
                "relevanceScore": e.relevance_score or 0.80,
                "type": "guidelines",
            }
            for e in evidence
        ]

    def _generate_qa_answer(self, query, results):
        """Generate a summary answer from search results."""
        if not results:
            return (
                "No relevant evidence was found for this query in the current literature database. "
                "Consider refining your search terms or searching with the Literature tab for broader results."
            )

        titles = [r["title"] for r in results[:3]]
        sources = ", ".join(titles)
        return (
            f"Based on {len(results)} relevant sources in our evidence database, including: {sources}. "
            f"Please review the individual results below for detailed findings. "
            f"Note: This is an AI-generated summary — always verify with primary literature before clinical application."
        )


class ResearchQueryViewSet(ModelViewSet):
    """Research query submission and result retrieval."""

    serializer_class = ResearchQuerySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["query_type", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return ResearchQuery.objects.filter(
            tenant=(getattr(self.request, 'tenant', None) or self.request.user.tenant)
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
            tenant=(getattr(request, 'tenant', None) or request.user.tenant),
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
