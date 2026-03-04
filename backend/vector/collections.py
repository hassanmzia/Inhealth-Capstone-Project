"""
Qdrant collection initialization and management.
Creates the 5 required collections for InHealth RAG system.
"""

import logging
from typing import Dict, List

logger = logging.getLogger("vector")

# Collection configurations
COLLECTIONS = {
    "clinical_guidelines": {
        "description": "Clinical practice guidelines from ADA, AHA, USPSTF, etc.",
        "vector_size": 768,  # sentence-transformers/all-mpnet-base-v2
        "payload_schema": {
            "title": "string",
            "source": "string",  # e.g., "ADA 2024 Standards of Care"
            "icd10_codes": "list[string]",
            "recommendation_level": "string",  # A/B/C/D
            "year": "integer",
            "url": "string",
            "content": "string",
        },
    },
    "medical_literature": {
        "description": "PubMed abstracts and full-text articles",
        "vector_size": 768,
        "payload_schema": {
            "pubmed_id": "string",
            "title": "string",
            "abstract": "string",
            "authors": "list[string]",
            "journal": "string",
            "year": "integer",
            "doi": "string",
            "evidence_level": "string",
            "mesh_terms": "list[string]",
        },
    },
    "patient_notes": {
        "description": "De-identified clinical notes and encounter documentation",
        "vector_size": 768,
        "payload_schema": {
            "patient_id": "string",
            "tenant_id": "string",
            "note_type": "string",
            "encounter_date": "string",
            "provider_specialty": "string",
            "content": "string",  # De-identified
        },
    },
    "drug_information": {
        "description": "Drug monographs, interactions, and prescribing information",
        "vector_size": 768,
        "payload_schema": {
            "rxnorm": "string",
            "drug_name": "string",
            "generic_name": "string",
            "drug_class": "string",
            "indications": "list[string]",
            "contraindications": "list[string]",
            "warnings": "list[string]",
            "dosing": "string",
        },
    },
    "disease_knowledge": {
        "description": "Disease descriptions, pathophysiology, and management",
        "vector_size": 768,
        "payload_schema": {
            "icd10": "string",
            "disease_name": "string",
            "category": "string",
            "description": "string",
            "symptoms": "list[string]",
            "diagnostic_criteria": "string",
            "management": "string",
        },
    },
}


def initialize_collections() -> Dict[str, bool]:
    """
    Initialize all required Qdrant collections.
    Creates collections if they don't exist.
    Returns {collection_name: created} dict.
    """
    from qdrant_client.http import models as rest
    from vector.client import get_client

    client = get_client()
    results = {}

    for collection_name, config in COLLECTIONS.items():
        try:
            # Check if collection already exists
            try:
                client.get_collection(collection_name)
                logger.info(f"Collection {collection_name} already exists")
                results[collection_name] = False
                continue
            except Exception:
                pass  # Collection doesn't exist, create it

            client.create_collection(
                collection_name=collection_name,
                vectors_config=rest.VectorParams(
                    size=config["vector_size"],
                    distance=rest.Distance.COSINE,
                    on_disk=True,  # Store vectors on disk for large collections
                ),
                optimizers_config=rest.OptimizersConfigDiff(
                    indexing_threshold=1000,
                    memmap_threshold=10000,
                ),
                hnsw_config=rest.HnswConfigDiff(
                    m=16,
                    ef_construct=100,
                    full_scan_threshold=10000,
                ),
            )
            logger.info(f"Created Qdrant collection: {collection_name} (vector_size={config['vector_size']})")
            results[collection_name] = True

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            results[collection_name] = False

    return results


def add_clinical_guideline(
    title: str,
    content: str,
    source: str,
    icd10_codes: List[str],
    year: int,
    recommendation_level: str = "B",
    url: str = "",
) -> Optional[str]:
    """Add a clinical guideline to the vector store."""
    from vector.embeddings import generate_embedding
    from vector.client import upsert_vectors
    import uuid

    embedding = generate_embedding(f"{title}\n{content[:500]}")
    if not embedding:
        return None

    doc_id = str(uuid.uuid4())
    upsert_vectors(
        collection_name="clinical_guidelines",
        points=[{
            "id": doc_id,
            "vector": embedding,
            "payload": {
                "title": title,
                "content": content,
                "source": source,
                "icd10_codes": icd10_codes,
                "year": year,
                "recommendation_level": recommendation_level,
                "url": url,
            },
        }],
    )
    return doc_id


def add_medical_literature(
    pubmed_id: str,
    title: str,
    abstract: str,
    authors: List[str],
    journal: str,
    year: int,
    evidence_level: str = "B",
    mesh_terms: List[str] = None,
) -> Optional[str]:
    """Add a medical literature entry to the vector store."""
    from vector.embeddings import generate_embedding
    from vector.client import upsert_vectors

    text_to_embed = f"{title}\n\n{abstract}"
    embedding = generate_embedding(text_to_embed)
    if not embedding:
        return None

    upsert_vectors(
        collection_name="medical_literature",
        points=[{
            "id": pubmed_id,
            "vector": embedding,
            "payload": {
                "pubmed_id": pubmed_id,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "year": year,
                "evidence_level": evidence_level,
                "mesh_terms": mesh_terms or [],
            },
        }],
    )
    return pubmed_id


try:
    from typing import Optional
except ImportError:
    pass
