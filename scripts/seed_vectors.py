#!/usr/bin/env python3
"""
InHealth Chronic Care - Qdrant Vector Store Initializer

Creates Qdrant collections and optionally loads initial embeddings
for clinical knowledge retrieval.
"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import Optional

# Third-party imports
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        CreateCollection,
        OptimizersConfigDiff,
        HnswConfigDiff,
        QuantizationConfig,
        ScalarQuantization,
        ScalarQuantizationConfig,
        ScalarType,
        PayloadSchemaType,
        TextIndexParams,
        TokenizerType,
    )
    from qdrant_client.http.exceptions import UnexpectedResponse
except ImportError:
    print("ERROR: qdrant-client not installed. Run: pip install 'qdrant-client[fastembed]'")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None):
        pass

# ============================================================
# Configuration
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", None)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)

# Embedding dimensions
# OpenAI text-embedding-3-small: 1536 dimensions
# OpenAI text-embedding-3-large: 3072 dimensions
EMBEDDING_DIM = 1536
EMBEDDING_MODEL = "text-embedding-3-small"

# ============================================================
# Collections configuration
# ============================================================
COLLECTIONS = [
    {
        "name": "clinical_guidelines",
        "description": "Clinical practice guidelines - ADA, ACC/AHA, KDIGO, GOLD, etc.",
        "dimension": EMBEDDING_DIM,
        "distance": Distance.COSINE,
        "on_disk_payload": True,
        "hnsw_m": 16,
        "hnsw_ef_construct": 100,
        "quantize": False,
        "payload_schema": {
            "guideline_id": PayloadSchemaType.KEYWORD,
            "title": PayloadSchemaType.TEXT,
            "organization": PayloadSchemaType.KEYWORD,
            "disease_codes": PayloadSchemaType.KEYWORD,
            "section": PayloadSchemaType.KEYWORD,
            "year": PayloadSchemaType.INTEGER,
            "evidence_level": PayloadSchemaType.KEYWORD,
        },
    },
    {
        "name": "medical_literature",
        "description": "PubMed abstracts, RCT summaries, systematic reviews",
        "dimension": EMBEDDING_DIM,
        "distance": Distance.COSINE,
        "on_disk_payload": True,
        "hnsw_m": 16,
        "hnsw_ef_construct": 100,
        "quantize": True,  # Use scalar quantization for large collections
        "payload_schema": {
            "pmid": PayloadSchemaType.KEYWORD,
            "title": PayloadSchemaType.TEXT,
            "journal": PayloadSchemaType.KEYWORD,
            "year": PayloadSchemaType.INTEGER,
            "disease_codes": PayloadSchemaType.KEYWORD,
            "study_type": PayloadSchemaType.KEYWORD,
            "evidence_level": PayloadSchemaType.KEYWORD,
        },
    },
    {
        "name": "patient_notes",
        "description": "De-identified clinical notes for RAG-based patient context",
        "dimension": EMBEDDING_DIM,
        "distance": Distance.COSINE,
        "on_disk_payload": True,
        "hnsw_m": 16,
        "hnsw_ef_construct": 100,
        "quantize": False,
        "payload_schema": {
            "patient_id": PayloadSchemaType.KEYWORD,
            "tenant_id": PayloadSchemaType.KEYWORD,
            "note_type": PayloadSchemaType.KEYWORD,
            "encounter_date": PayloadSchemaType.KEYWORD,
            "author_role": PayloadSchemaType.KEYWORD,
            "fhir_resource_id": PayloadSchemaType.KEYWORD,
        },
    },
    {
        "name": "drug_information",
        "description": "Drug monographs, FDA drug labels, pharmacology information",
        "dimension": EMBEDDING_DIM,
        "distance": Distance.COSINE,
        "on_disk_payload": True,
        "hnsw_m": 16,
        "hnsw_ef_construct": 100,
        "quantize": False,
        "payload_schema": {
            "rxnorm": PayloadSchemaType.KEYWORD,
            "drug_name": PayloadSchemaType.TEXT,
            "drug_class": PayloadSchemaType.KEYWORD,
            "section": PayloadSchemaType.KEYWORD,
            "ndc": PayloadSchemaType.KEYWORD,
        },
    },
    {
        "name": "disease_knowledge",
        "description": "Disease pathophysiology, epidemiology, and management summaries",
        "dimension": EMBEDDING_DIM,
        "distance": Distance.COSINE,
        "on_disk_payload": True,
        "hnsw_m": 16,
        "hnsw_ef_construct": 100,
        "quantize": False,
        "payload_schema": {
            "icd10": PayloadSchemaType.KEYWORD,
            "disease_name": PayloadSchemaType.TEXT,
            "category": PayloadSchemaType.KEYWORD,
            "section": PayloadSchemaType.KEYWORD,
            "source": PayloadSchemaType.KEYWORD,
        },
    },
]


# ============================================================
# Qdrant Client
# ============================================================
def create_client(url: str, api_key: Optional[str] = None) -> QdrantClient:
    """Create and verify Qdrant client connection."""
    max_retries = 10
    retry_delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            client = QdrantClient(
                url=url,
                api_key=api_key,
                timeout=60,
            )
            # Verify connectivity
            client.get_collections()
            logger.info(f"Connected to Qdrant at {url}")
            return client
        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    f"Qdrant not available (attempt {attempt}/{max_retries}): {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Qdrant after {max_retries} attempts")
                raise


def create_collection(client: QdrantClient, config: dict) -> bool:
    """
    Create a Qdrant collection with the specified configuration.
    Returns True if created, False if already exists.
    """
    name = config["name"]

    # Check if collection already exists
    existing = client.get_collections()
    existing_names = [c.name for c in existing.collections]

    if name in existing_names:
        logger.info(f"  Collection '{name}' already exists - skipping")
        return False

    # Build vectors config
    vectors_config = VectorParams(
        size=config["dimension"],
        distance=config["distance"],
        on_disk=False,  # Keep vectors in RAM for speed
    )

    # Build HNSW config
    hnsw_config = HnswConfigDiff(
        m=config.get("hnsw_m", 16),
        ef_construct=config.get("hnsw_ef_construct", 100),
        full_scan_threshold=10000,
        on_disk=False,
    )

    # Optimizer config
    optimizer_config = OptimizersConfigDiff(
        indexing_threshold=20000,
        memmap_threshold=50000,
    )

    # Quantization (optional - reduces memory at some accuracy cost)
    quantization_config = None
    if config.get("quantize", False):
        quantization_config = QuantizationConfig(
            scalar=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,
                )
            )
        )

    try:
        client.create_collection(
            collection_name=name,
            vectors_config=vectors_config,
            hnsw_config=hnsw_config,
            optimizers_config=optimizer_config,
            quantization_config=quantization_config,
            on_disk_payload=config.get("on_disk_payload", True),
        )
        logger.info(f"  Created collection '{name}' (dim={config['dimension']}, distance={config['distance']})")

        # Create payload indexes for fast filtering
        for field_name, field_type in config.get("payload_schema", {}).items():
            try:
                if field_type == PayloadSchemaType.TEXT:
                    # Text index with tokenizer for full-text search
                    client.create_payload_index(
                        collection_name=name,
                        field_name=field_name,
                        field_schema=TextIndexParams(
                            type="text",
                            tokenizer=TokenizerType.WORD,
                            min_token_len=2,
                            max_token_len=20,
                            lowercase=True,
                        ),
                    )
                else:
                    client.create_payload_index(
                        collection_name=name,
                        field_name=field_name,
                        field_schema=field_type,
                    )
                logger.debug(f"    Created index on field: {field_name}")
            except Exception as e:
                logger.warning(f"    Could not create index on {field_name}: {e}")

        return True

    except UnexpectedResponse as e:
        if "already exists" in str(e):
            logger.info(f"  Collection '{name}' already exists (race condition)")
            return False
        raise


def get_embedding(text: str, model: str = EMBEDDING_MODEL) -> Optional[list]:
    """
    Generate an embedding using OpenAI.
    Returns None if OpenAI is not configured.
    """
    if not OPENAI_API_KEY:
        return None

    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            input=text,
            model=model,
            dimensions=EMBEDDING_DIM,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Failed to generate embedding: {e}")
        return None


def seed_sample_clinical_guidelines(client: QdrantClient) -> int:
    """
    Load a small set of sample clinical guideline chunks into the
    clinical_guidelines collection to bootstrap the RAG pipeline.

    Returns the number of vectors inserted.
    """
    sample_guidelines = [
        {
            "id": "ada-2024-hba1c-target",
            "text": (
                "ADA 2024 Standards of Care - Glycemic Targets: "
                "For many nonpregnant adults with type 2 diabetes, the American Diabetes Association "
                "recommends an HbA1c target of less than 7% (53 mmol/mol). "
                "More or less stringent glycemic goals may be appropriate for individual patients. "
                "A lower HbA1c goal, such as less than 6.5%, may be considered in patients with "
                "short duration of diabetes, long life expectancy, no significant CVD, treated with "
                "lifestyle or metformin only, and without significant hypoglycemia. "
                "Higher HbA1c targets (less than 8%) are appropriate for patients with history of "
                "severe hypoglycemia, limited life expectancy, advanced complications, or poor self-management."
            ),
            "payload": {
                "guideline_id": "ada-2024-soc",
                "title": "ADA 2024 Standards of Care in Diabetes",
                "organization": "American Diabetes Association",
                "disease_codes": ["E11.9", "E11.65"],
                "section": "Glycemic Targets",
                "year": 2024,
                "evidence_level": "A",
            }
        },
        {
            "id": "ada-2024-metformin",
            "text": (
                "ADA 2024 - Pharmacologic Therapy for T2DM: "
                "Metformin remains the preferred first-line pharmacologic agent for the treatment "
                "of type 2 diabetes mellitus. Metformin is effective, safe, inexpensive, and may "
                "reduce the risk of cardiovascular events. It should be initiated unless contraindicated "
                "(eGFR <30 mL/min/1.73m2). "
                "For patients with established ASCVD or at high cardiovascular risk, "
                "an SGLT2 inhibitor with proven CV benefit (empagliflozin, canagliflozin, dapagliflozin) "
                "or a GLP-1 receptor agonist with proven CV benefit (semaglutide, liraglutide) "
                "is recommended regardless of HbA1c level as part of the glucose-lowering regimen."
            ),
            "payload": {
                "guideline_id": "ada-2024-soc",
                "title": "ADA 2024 Standards of Care in Diabetes",
                "organization": "American Diabetes Association",
                "disease_codes": ["E11.9"],
                "section": "Pharmacologic Therapy",
                "year": 2024,
                "evidence_level": "A",
            }
        },
        {
            "id": "acc-aha-hf-2022-quadruple",
            "text": (
                "ACC/AHA 2022 Heart Failure Guidelines - Guideline-Directed Medical Therapy for HFrEF: "
                "For patients with HFrEF (EF <=40%), four evidence-based therapies improve mortality: "
                "1) ACE inhibitor or ARB or ARNI (sacubitril/valsartan preferred over ACEi/ARB), "
                "2) Beta-blocker (carvedilol, metoprolol succinate, or bisoprolol), "
                "3) Mineralocorticoid receptor antagonist (spironolactone or eplerenone), "
                "4) SGLT2 inhibitor (dapagliflozin or empagliflozin). "
                "All four agents should be initiated and uptitrated to maximally tolerated doses. "
                "Loop diuretics are used for volume management but do not affect mortality."
            ),
            "payload": {
                "guideline_id": "acc-aha-hf-2022",
                "title": "ACC/AHA/HFSA Guideline for the Management of Heart Failure 2022",
                "organization": "American College of Cardiology",
                "disease_codes": ["I50.9", "I50.22"],
                "section": "Pharmacologic Treatment of HFrEF",
                "year": 2022,
                "evidence_level": "A",
            }
        },
        {
            "id": "kdigo-2024-sglt2i-ckd",
            "text": (
                "KDIGO 2024 CKD Guidelines - SGLT2 Inhibitors in CKD: "
                "We recommend an SGLT2 inhibitor be used in adults with CKD and type 2 diabetes "
                "with an eGFR >=20 mL/min/1.73m2 to slow CKD progression (Grade 1A). "
                "In adults with CKD and heart failure with reduced ejection fraction (HFrEF), "
                "we recommend an SGLT2 inhibitor to slow CKD progression regardless of diabetes status (Grade 1A). "
                "We suggest considering an SGLT2 inhibitor in other CKD patients with eGFR >=20 "
                "to slow CKD progression (Grade 2B). "
                "SGLT2 inhibitors should be continued even if eGFR falls below 20 mL/min/1.73m2 "
                "unless they need to be stopped for clinical reasons."
            ),
            "payload": {
                "guideline_id": "kdigo-2024-ckd",
                "title": "KDIGO 2024 Clinical Practice Guideline for Chronic Kidney Disease",
                "organization": "Kidney Disease: Improving Global Outcomes",
                "disease_codes": ["N18.3", "N18.4"],
                "section": "Pharmacologic Treatment",
                "year": 2024,
                "evidence_level": "1A",
            }
        },
        {
            "id": "gold-copd-2024-initial",
            "text": (
                "GOLD 2024 COPD Guidelines - Initial Pharmacologic Treatment: "
                "For newly diagnosed COPD patients, the choice of initial maintenance therapy depends on "
                "symptom burden (mMRC dyspnea scale or CAT score) and exacerbation history. "
                "Group A patients (low symptoms, low exacerbation risk): SABA or SAMA as needed. "
                "Group B patients (high symptoms, low exacerbation risk): Long-acting bronchodilator "
                "(LAMA or LABA); LAMA preferred for most patients. "
                "Group E patients (high exacerbation risk): LAMA or LAMA+LABA; "
                "consider ICS/LABA if blood eosinophils >=300 cells/mcL. "
                "Avoid ICS monotherapy. Smoking cessation is the most important intervention."
            ),
            "payload": {
                "guideline_id": "gold-copd-2024",
                "title": "GOLD 2024 Global Strategy for Prevention, Diagnosis and Management of COPD",
                "organization": "Global Initiative for Chronic Obstructive Lung Disease",
                "disease_codes": ["J44.1", "J44.0"],
                "section": "Initial Pharmacologic Treatment",
                "year": 2024,
                "evidence_level": "A",
            }
        },
        {
            "id": "acc-aha-afib-anticoag",
            "text": (
                "ACC/AHA 2023 Atrial Fibrillation Guidelines - Stroke Prevention: "
                "Oral anticoagulation is recommended for patients with AF and CHA2DS2-VASc score "
                ">=2 in men or >=3 in women to prevent thromboembolic stroke. "
                "Direct oral anticoagulants (DOACs: apixaban, rivaroxaban, dabigatran, or edoxaban) "
                "are preferred over vitamin K antagonists (warfarin) for patients with nonvalvular AF. "
                "Apixaban is associated with lowest bleeding risk. "
                "Anticoagulation is NOT recommended for patients with AF and CHA2DS2-VASc score of 0 in men "
                "or 1 in women as net clinical benefit has not been demonstrated."
            ),
            "payload": {
                "guideline_id": "acc-aha-afib-2023",
                "title": "ACC/AHA Atrial Fibrillation Guideline 2023",
                "organization": "American College of Cardiology",
                "disease_codes": ["I48.91"],
                "section": "Stroke Prevention",
                "year": 2023,
                "evidence_level": "I",
            }
        },
        {
            "id": "acc-aha-htn-2017-bp-target",
            "text": (
                "ACC/AHA 2017 Hypertension Guidelines - Blood Pressure Targets: "
                "The blood pressure target for most adults with hypertension is <130/80 mmHg. "
                "This target applies to adults with clinical CVD (coronary artery disease, stroke, "
                "heart failure, peripheral artery disease), CKD, diabetes, and 10-year ASCVD risk >=10%. "
                "For adults with hypertension without additional clinical conditions, "
                "a BP target of <130/80 mmHg is also recommended. "
                "Lifestyle modification (weight loss, DASH diet, sodium reduction, physical activity, "
                "limiting alcohol) is recommended for all hypertensive patients. "
                "Antihypertensive medication should be initiated for Stage 1 hypertension "
                "(BP 130-139/80-89) in patients with clinical CVD or 10-year ASCVD risk >=10%."
            ),
            "payload": {
                "guideline_id": "acc-aha-htn-2017",
                "title": "ACC/AHA 2017 High Blood Pressure Guideline",
                "organization": "American College of Cardiology",
                "disease_codes": ["I10"],
                "section": "Blood Pressure Targets",
                "year": 2017,
                "evidence_level": "I",
            }
        },
        {
            "id": "ada-2024-ckd-monitoring",
            "text": (
                "ADA 2024 - Diabetic Kidney Disease Monitoring: "
                "Annual measurement of urinary albumin-to-creatinine ratio (UACR) and estimated "
                "GFR (eGFR) is recommended for all patients with type 2 diabetes, starting at diagnosis. "
                "Patients with UACR >=30 mg/g creatinine or eGFR <60 mL/min/1.73m2 should be treated "
                "with an ACE inhibitor or ARB to reduce albuminuria and slow CKD progression. "
                "An SGLT2 inhibitor with proven benefit in CKD should be added for patients with "
                "T2DM and CKD with eGFR >=20 mL/min/1.73m2. "
                "Finerenone (nonsteroidal MRA) should be added in T2DM with CKD and UACR >=30 mg/g "
                "despite optimized ACEi/ARB therapy and eGFR 25-75 mL/min/1.73m2."
            ),
            "payload": {
                "guideline_id": "ada-2024-soc",
                "title": "ADA 2024 Standards of Care in Diabetes",
                "organization": "American Diabetes Association",
                "disease_codes": ["E11.9", "N18.3", "E11.21"],
                "section": "Diabetic Kidney Disease",
                "year": 2024,
                "evidence_level": "A",
            }
        },
    ]

    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set - skipping embedding generation")
        logger.info(f"Would insert {len(sample_guidelines)} guideline chunks when API key is available")
        return 0

    logger.info(f"Generating embeddings for {len(sample_guidelines)} clinical guideline chunks...")

    from qdrant_client.models import PointStruct
    import hashlib

    points = []
    for i, item in enumerate(sample_guidelines):
        logger.debug(f"  Embedding {i+1}/{len(sample_guidelines)}: {item['id']}")

        embedding = get_embedding(item["text"])
        if embedding is None:
            logger.warning(f"  Skipping {item['id']} - embedding failed")
            continue

        # Generate deterministic UUID from ID
        point_id = int(hashlib.md5(item["id"].encode()).hexdigest()[:16], 16) % (2**63)

        points.append(PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "chunk_id": item["id"],
                "text": item["text"],
                **item["payload"],
            }
        ))

        # Small delay to respect rate limits
        time.sleep(0.1)

    if points:
        client.upsert(
            collection_name="clinical_guidelines",
            points=points,
        )
        logger.info(f"Inserted {len(points)} guideline chunks into 'clinical_guidelines' collection")

    return len(points)


def seed_collections(
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
    seed_data: bool = True,
) -> bool:
    """
    Create all Qdrant collections and optionally seed with sample data.
    Returns True if successful.
    """
    url = qdrant_url or QDRANT_URL
    api_key = qdrant_api_key or QDRANT_API_KEY

    logger.info("=" * 60)
    logger.info("InHealth Chronic Care - Qdrant Initializer")
    logger.info("=" * 60)
    logger.info(f"Qdrant URL: {url}")
    logger.info(f"Collections to create: {len(COLLECTIONS)}")
    logger.info(f"Seed with data: {seed_data}")
    logger.info("")

    # Connect
    client = create_client(url, api_key)

    # Get current collections
    existing = client.get_collections()
    logger.info(f"Existing collections: {[c.name for c in existing.collections]}")
    logger.info("")

    # Create collections
    created = 0
    skipped = 0
    logger.info("Creating collections:")
    for config in COLLECTIONS:
        if create_collection(client, config):
            created += 1
        else:
            skipped += 1

    logger.info("")
    logger.info(f"Collections: {created} created, {skipped} already existed")

    # Seed with sample data
    vectors_inserted = 0
    if seed_data:
        logger.info("")
        logger.info("Seeding sample clinical guidelines...")
        vectors_inserted = seed_sample_clinical_guidelines(client)

    # Final stats
    logger.info("")
    final_collections = client.get_collections()
    logger.info("=" * 60)
    logger.info("Qdrant Initialization Complete")
    logger.info("=" * 60)
    for collection in final_collections.collections:
        info = client.get_collection(collection.name)
        logger.info(
            f"  {collection.name}: "
            f"vectors={info.vectors_count or 0}, "
            f"dim={info.config.params.vectors.size}"
        )

    logger.info(f"Total vectors inserted: {vectors_inserted}")
    return True


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize InHealth Qdrant vector store collections"
    )
    parser.add_argument(
        "--url",
        default=QDRANT_URL,
        help=f"Qdrant URL (default: {QDRANT_URL})"
    )
    parser.add_argument(
        "--api-key",
        default=QDRANT_API_KEY,
        help="Qdrant API key (if required)"
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Only create collections, do not seed with sample data"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing collections and exit"
    )

    args = parser.parse_args()

    if args.list:
        client = create_client(args.url, args.api_key)
        collections = client.get_collections()
        print(f"\nExisting Qdrant collections at {args.url}:")
        for c in collections.collections:
            info = client.get_collection(c.name)
            print(
                f"  {c.name}: "
                f"vectors={info.vectors_count or 0}, "
                f"dim={info.config.params.vectors.size}"
            )
        sys.exit(0)

    success = seed_collections(
        qdrant_url=args.url,
        qdrant_api_key=args.api_key,
        seed_data=not args.no_seed,
    )
    sys.exit(0 if success else 1)
