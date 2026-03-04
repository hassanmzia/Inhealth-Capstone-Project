"""Celery tasks for research and clinical evidence processing."""

import logging
from datetime import timezone as py_tz

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.research")


@shared_task(bind=True, max_retries=2, time_limit=300, queue="research")
def process_research_query(self, query_id: str):
    """
    Process a research query using RAG + LLM.
    Updates the ResearchQuery model with results.
    """
    import time
    from .models import ResearchQuery

    try:
        query = ResearchQuery.objects.get(id=query_id)
        query.status = ResearchQuery.Status.PROCESSING
        query.save(update_fields=["status"])

        start_time = time.time()

        # Dispatch to appropriate handler based on query type
        handlers = {
            ResearchQuery.QueryType.LITERATURE: _handle_literature_query,
            ResearchQuery.QueryType.TRIAL_MATCHING: _handle_trial_matching,
            ResearchQuery.QueryType.GUIDELINE: _handle_guideline_query,
            ResearchQuery.QueryType.QA: _handle_clinical_qa,
            ResearchQuery.QueryType.DRUG_INTERACTION: _handle_drug_interaction,
        }
        handler = handlers.get(query.query_type, _handle_clinical_qa)
        result, sources, evidence_level = handler(query)

        elapsed_ms = int((time.time() - start_time) * 1000)

        query.status = ResearchQuery.Status.COMPLETE
        query.result = result
        query.sources = sources
        query.evidence_level = evidence_level
        query.processing_time_ms = elapsed_ms
        query.completed_at = timezone.now()
        query.save(update_fields=["status", "result", "sources", "evidence_level", "processing_time_ms", "completed_at"])

        return {"query_id": query_id, "status": "complete"}

    except ResearchQuery.DoesNotExist:
        logger.error(f"ResearchQuery {query_id} not found")
    except Exception as exc:
        logger.error(f"Research query processing failed: {exc}")
        try:
            query.status = ResearchQuery.Status.ERROR
            query.error_message = str(exc)
            query.save(update_fields=["status", "error_message"])
        except Exception:
            pass
        raise self.retry(exc=exc)


def _handle_literature_query(query):
    """Search PubMed and vector DB for relevant literature."""
    try:
        from vector.rag import RAGPipeline
        pipeline = RAGPipeline()
        results = pipeline.retrieve_and_augment(
            query=query.query_text,
            collection="medical_literature",
            top_k=5,
        )
        return (
            {"summary": results.get("answer", ""), "key_findings": results.get("findings", [])},
            results.get("sources", []),
            "B",
        )
    except Exception as e:
        logger.warning(f"RAG pipeline unavailable: {e}")
        return {"summary": "Literature search unavailable.", "note": str(e)}, [], ""


def _handle_trial_matching(query):
    """Match patient eligibility against clinical trials."""
    from .models import ClinicalTrial

    if not query.patient:
        return {"error": "No patient context provided"}, [], ""

    patient = query.patient
    # Simple matching by condition
    conditions = list(patient.conditions.filter(clinical_status="active").values_list("code", flat=True))

    matching_trials = []
    for condition_code in conditions[:5]:
        trials = ClinicalTrial.objects.filter(
            status=ClinicalTrial.Status.RECRUITING,
            condition__icontains=condition_code[:3],  # ICD10 prefix match
        )[:3]
        for trial in trials:
            matching_trials.append({
                "nct_id": trial.nct_id,
                "title": trial.title,
                "phase": trial.phase,
                "locations": trial.locations[:2],
            })

    return (
        {"matched_trials": matching_trials, "total_matched": len(matching_trials)},
        [{"title": t["title"], "url": f"https://clinicaltrials.gov/ct2/show/{t['nct_id']}"} for t in matching_trials],
        "A",
    )


def _handle_guideline_query(query):
    """Look up clinical guidelines."""
    try:
        from vector.rag import RAGPipeline
        pipeline = RAGPipeline()
        results = pipeline.retrieve_and_augment(
            query=query.query_text,
            collection="clinical_guidelines",
            top_k=3,
        )
        return (
            {"guideline_summary": results.get("answer", ""), "recommendations": results.get("recommendations", [])},
            results.get("sources", []),
            "A",
        )
    except Exception as e:
        return {"error": str(e)}, [], ""


def _handle_clinical_qa(query):
    """General clinical Q&A using LLM with RAG."""
    try:
        from vector.rag import RAGPipeline
        pipeline = RAGPipeline()
        results = pipeline.retrieve_and_augment(
            query=query.query_text,
            collection="disease_knowledge",
            top_k=5,
        )
        return (
            {"answer": results.get("answer", ""), "confidence": results.get("confidence", 0.0)},
            results.get("sources", []),
            results.get("evidence_level", "C"),
        )
    except Exception as e:
        return {"answer": f"Unable to process query: {e}"}, [], "C"


def _handle_drug_interaction(query):
    """Check drug-drug interactions using graph DB."""
    try:
        from graph.queries.drug import check_drug_interactions
        # Extract drug names from query text
        drug_names = query.query_text.split(" vs ")
        if len(drug_names) >= 2:
            interactions = check_drug_interactions(drug_names[0].strip(), drug_names[1].strip())
        else:
            interactions = []
        return (
            {"interactions": interactions, "query": query.query_text},
            [],
            "B",
        )
    except Exception as e:
        return {"interactions": [], "error": str(e)}, [], ""


@shared_task(queue="research")
def sync_clinical_guidelines():
    """
    Weekly sync of clinical guidelines from NLM/AHA/ADA/etc.
    Indexes new guidelines into Qdrant vector DB.
    """
    logger.info("Starting clinical guidelines sync...")
    # In production: fetch from USPSTF, ADA, AHA guidelines APIs
    # Then index into Qdrant using vector/collections.py
    return {"status": "sync_complete", "guidelines_updated": 0}
