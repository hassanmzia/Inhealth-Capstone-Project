"""
Security — Guardrails Module

Protects the InHealth AI Agent system against:
  1. Prompt injection attacks
  2. Topic restriction (clinical scope only)
  3. Output validation
  4. Rate limiting per tenant
  5. Jailbreak detection
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("inhealth.security.guardrails")

# ── Prompt injection detection patterns ───────────────────────────────────────
INJECTION_PATTERNS = [
    # Classic prompt injection
    r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+instructions",
    r"disregard\s+(?:all\s+)?(?:previous|above|prior)\s+instructions",
    r"forget\s+(?:all\s+)?(?:previous|above|prior)\s+instructions",
    r"new\s+instruction[s]?:",
    r"system\s*:\s*you\s+are\s+now",
    r"act\s+as\s+(?:if\s+you\s+(?:are|were)|a|an)\s+(?:different|new|evil|uncensored)",

    # Jailbreak patterns
    r"do\s+anything\s+now",
    r"dan\s+mode",
    r"developer\s+mode",
    r"jailbreak",
    r"bypass\s+(?:safety|restriction|filter)",
    r"ignore\s+(?:safety|ethical)\s+(?:guidelines|constraints)",

    # Role manipulation
    r"you\s+(?:are|were|will be)\s+(?:now\s+)?(?:a\s+)?(?:hacker|criminal|malicious)",
    r"pretend\s+(?:that\s+)?you\s+(?:have\s+no\s+)?(?:restrictions|limits|constraints)",

    # Data extraction
    r"reveal\s+(?:your\s+)?(?:system\s+)?prompt",
    r"show\s+(?:me\s+)?(?:your\s+)?(?:system\s+)?(?:instructions|prompt|training)",
    r"print\s+(?:your\s+)?(?:full\s+)?(?:system\s+)?prompt",
    r"what\s+(?:are\s+)?(?:your\s+)?(?:exact\s+)?instructions",
]

# ── Restricted topics (off-topic for a clinical platform) ─────────────────────
RESTRICTED_TOPICS = [
    "cryptocurrency",
    "investment advice",
    "stock market",
    "bitcoin",
    "political opinion",
    "election",
    "weapons manufacturing",
    "drug synthesis",  # Note: different from pharmacology
    "illegal activity",
    "hacking tutorial",
    "sex",
    "adult content",
    "gambling",
]

# ── Clinical scope keywords (must be present for long queries) ─────────────────
CLINICAL_KEYWORDS = [
    "patient", "diagnosis", "treatment", "medication", "symptom", "disease",
    "health", "medical", "clinical", "therapy", "lab", "glucose", "blood",
    "heart", "kidney", "lung", "cancer", "diabetes", "hypertension", "chronic",
    "doctor", "physician", "nurse", "hospital", "prescription", "risk", "vitals",
]

# ── In-memory rate limiter ────────────────────────────────────────────────────
_rate_limit_store: Dict[str, List[float]] = {}
RATE_LIMIT_REQUESTS = int(os.getenv("GUARDRAIL_RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("GUARDRAIL_RATE_LIMIT_WINDOW", "60"))


class GuardrailsEngine:
    """
    Multi-layer safety guardrail engine for InHealth AI agents.
    """

    def __init__(self):
        self._injection_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in INJECTION_PATTERNS
        ]

    def check_input(
        self,
        text: str,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Run all input guardrails. Returns (is_safe, reason_if_unsafe).
        """
        # 1. Rate limiting
        safe, reason = self._check_rate_limit(tenant_id)
        if not safe:
            return False, reason

        # 2. Prompt injection detection
        safe, reason = self._detect_prompt_injection(text)
        if not safe:
            return False, reason

        # 3. Restricted topic check
        safe, reason = self._check_restricted_topics(text)
        if not safe:
            return False, reason

        # 4. Input length validation
        if len(text) > 50_000:
            return False, "Input exceeds maximum allowed length (50,000 characters)"

        return True, None

    def check_output(
        self,
        output: str,
        original_input: str,
    ) -> Tuple[bool, str]:
        """
        Validate agent output. Returns (is_safe, sanitized_output).
        """
        sanitized = output

        # Remove any leaked system prompt artifacts
        sanitized = re.sub(
            r"(?:SYSTEM|INSTRUCTIONS|PROMPT)[:\s]*\[.*?\]",
            "[REDACTED]",
            sanitized,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove potential SQL injection in output
        dangerous_sql = re.compile(
            r"(?:DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE)\s+(?:TABLE|DATABASE|FROM|INTO)\s+\w+",
            re.IGNORECASE,
        )
        if dangerous_sql.search(sanitized):
            sanitized = dangerous_sql.sub("[BLOCKED SQL OPERATION]", sanitized)
            logger.warning("Potential SQL injection detected in agent output")

        return True, sanitized

    def validate_patient_scope(
        self,
        query_patient_id: str,
        authenticated_patient_ids: List[str],
        tenant_id: str,
    ) -> bool:
        """
        Ensure the agent only accesses data for authorized patients.
        Multi-tenant isolation check.
        """
        if query_patient_id not in authenticated_patient_ids:
            logger.critical(
                "SECURITY: Cross-patient data access attempt — query_patient=%s tenant=%s",
                query_patient_id,
                tenant_id,
            )
            return False
        return True

    def _check_rate_limit(self, tenant_id: str) -> Tuple[bool, Optional[str]]:
        """Sliding window rate limiter per tenant."""
        now = time.monotonic()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        if tenant_id not in _rate_limit_store:
            _rate_limit_store[tenant_id] = []

        # Clean old timestamps
        _rate_limit_store[tenant_id] = [
            ts for ts in _rate_limit_store[tenant_id] if ts > window_start
        ]

        if len(_rate_limit_store[tenant_id]) >= RATE_LIMIT_REQUESTS:
            return False, f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS}s"

        _rate_limit_store[tenant_id].append(now)
        return True, None

    def _detect_prompt_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        """Detect prompt injection attempts."""
        for pattern in self._injection_patterns:
            match = pattern.search(text)
            if match:
                logger.warning(
                    "Prompt injection detected: pattern='%s' match='%s'",
                    pattern.pattern[:50],
                    match.group(0)[:50],
                )
                return False, f"Prompt injection attempt detected: {match.group(0)[:50]}"
        return True, None

    def _check_restricted_topics(self, text: str) -> Tuple[bool, Optional[str]]:
        """Check if input is about a restricted (off-topic) subject."""
        text_lower = text.lower()

        for topic in RESTRICTED_TOPICS:
            if topic in text_lower:
                # Verify it's not clinically relevant (e.g., "drug synthesis" vs "drug for synthesis")
                clinical_context = any(kw in text_lower for kw in CLINICAL_KEYWORDS)
                if not clinical_context:
                    return False, f"Off-topic query detected: '{topic}'. InHealth AI supports clinical queries only."

        return True, None

    def sanitize_for_llm(self, text: str) -> str:
        """
        Sanitize user input before passing to LLM.
        Removes special characters that could confuse prompt parsing.
        """
        # Remove null bytes
        text = text.replace("\x00", "")
        # Limit consecutive special characters
        text = re.sub(r"[<>]{3,}", "...", text)
        # Remove HTML tags (potential XSS in prompts)
        text = re.sub(r"<[^>]{1,200}>", "", text)
        return text.strip()

    def hash_for_audit(self, text: str) -> str:
        """Return a SHA-256 hash of text for audit logging without storing raw content."""
        return hashlib.sha256(text.encode()).hexdigest()


# Module-level singleton instance
guardrails = GuardrailsEngine()
