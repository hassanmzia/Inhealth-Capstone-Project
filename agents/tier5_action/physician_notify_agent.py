"""
Agent 20 — Physician Notification Agent

Responsibilities:
  - Priority-based physician notification
  - Generate CRITICAL/URGENT/SOON/ROUTINE alerts
  - Multi-channel: in-app, push notification, SMS, email, EHR inbox
  - Include patient summary, findings, recommended action
  - Track acknowledgment and escalate if unacknowledged
    (CRITICAL: 5min, URGENT: 30min)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from base.agent import MCPAgent
from base.tools import query_fhir_database, send_notification, vector_search

logger = logging.getLogger("inhealth.agent.physician_notify")

# Escalation timeouts (seconds)
ESCALATION_TIMEOUTS = {
    "CRITICAL": 300,    # 5 minutes
    "URGENT": 1800,     # 30 minutes
    "SOON": 14400,      # 4 hours
    "ROUTINE": 86400,   # 24 hours
}

NOTIFICATION_PRIORITY_MAP = {
    "EMERGENCY": "CRITICAL",
    "HIGH": "URGENT",
    "NORMAL": "SOON",
    "LOW": "ROUTINE",
}


class PhysicianNotifyAgent(MCPAgent):
    """Agent 20: Priority-based physician notification and escalation."""

    agent_id = 20
    agent_name = "physician_notify_agent"
    agent_tier = "tier5_action"
    system_prompt = (
        "You are the Physician Notification AI Agent for InHealth Chronic Care. "
        "You generate concise, actionable physician notifications based on clinical findings. "
        "Prioritize alerts (CRITICAL/URGENT/SOON/ROUTINE), select appropriate communication channels, "
        "and track acknowledgment. Use clinical language appropriate for a physician. "
        "Include patient context, key findings, and specific recommended actions."
    )

    def _default_tools(self):
        return [query_fhir_database, send_notification, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        alerts = state.get("alerts", [])
        interventions = state.get("interventions", [])
        risk_scores = state.get("risk_scores", {})
        monitoring = state.get("monitoring_results", {})
        diagnostics = state.get("diagnostic_results", {})

        if not alerts and not interventions:
            return self._build_result(
                status="no_notifications_needed",
                findings={"message": "No actionable alerts requiring physician notification"},
            )

        # Determine highest priority
        priority = "ROUTINE"
        for alert in alerts:
            alert_severity = alert.get("severity", "LOW")
            mapped = NOTIFICATION_PRIORITY_MAP.get(alert_severity, "ROUTINE")
            if list(NOTIFICATION_PRIORITY_MAP.values()).index(mapped) < \
               list(NOTIFICATION_PRIORITY_MAP.values()).index(priority):
                priority = mapped

        # Get responsible physician
        physician_data = await self._get_responsible_physician(patient_id)
        physician_id = physician_data.get("physician_id", "on_call")

        # Generate physician notification content via LLM
        alerts_summary = "\n".join([
            f"  [{a.get('severity', 'UNKNOWN')}] {a.get('message', '')[:150]}"
            for a in sorted(alerts, key=lambda x: {"EMERGENCY": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}.get(x.get("severity", "LOW"), 4))[:10]
        ])

        ensemble_risk = risk_scores.get("ml_ensemble_agent", {}).get("findings", {})
        risk_str = f"{ensemble_risk.get('risk_level', 'UNKNOWN')} ({ensemble_risk.get('unified_score', 0):.0%})" if ensemble_risk else "Not calculated"

        llm_input = (
            f"Generate a physician notification for patient {patient_id}:\n\n"
            f"Priority: {priority}\n"
            f"Overall risk level: {risk_str}\n\n"
            f"Active alerts:\n{alerts_summary}\n\n"
            f"Pending interventions requiring approval: {len([i for i in interventions if i.get('requires_hitl')])}\n\n"
            f"Create a physician notification with:\n"
            f"1. Subject line (brief, priority-tagged)\n"
            f"2. Patient summary (2-3 sentences: age, gender, key conditions)\n"
            f"3. Key findings (bullet list, most critical first)\n"
            f"4. Recommended actions (numbered, specific, with urgency)\n"
            f"5. Required physician decisions (HITL items)\n"
            f"6. Contact information for follow-up\n\n"
            f"Format for EHR inbox message. Professional, concise, action-oriented."
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            notification_content = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Physician notify LLM failed: %s", exc)
            notification_content = self._fallback_notification(patient_id, priority, alerts[:3])

        # Send notifications across channels
        channels_used = []
        channels = self._select_channels(priority)

        for channel in channels:
            try:
                success = send_notification.invoke({
                    "patient_id": patient_id,
                    "notification_type": priority,
                    "message": notification_content[:1000],
                    "channel": channel,
                })
                if success:
                    channels_used.append(channel)
            except Exception as exc:
                logger.warning("Failed to send on channel %s: %s", channel, exc)

        # Track notification for acknowledgment monitoring
        notification_record = {
            "notification_id": f"phys-{patient_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "patient_id": patient_id,
            "physician_id": physician_id,
            "priority": priority,
            "channels_sent": channels_used,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "acknowledged": False,
            "escalation_timeout_seconds": ESCALATION_TIMEOUTS.get(priority, 86400),
            "content_preview": notification_content[:200],
        }

        await self._track_notification(notification_record)

        # Schedule escalation if CRITICAL or URGENT (background task)
        if priority in ("CRITICAL", "URGENT"):
            await self._schedule_escalation(notification_record)

        return self._build_result(
            status="completed",
            findings={
                "priority": priority,
                "notification_content": notification_content,
                "channels_sent": channels_used,
                "notification_id": notification_record["notification_id"],
                "physician_notified": physician_id,
                "escalation_in_seconds": ESCALATION_TIMEOUTS.get(priority),
            },
            recommendations=[f"Physician notification sent ({priority}). Awaiting acknowledgment within {ESCALATION_TIMEOUTS.get(priority, 86400) // 60} minutes."],
        )

    async def _get_responsible_physician(self, patient_id: str) -> Dict[str, Any]:
        """Look up the patient's primary care physician or on-call provider."""
        try:
            import httpx

            api_url = os.getenv("DJANGO_API_URL", "http://backend:8000")
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{api_url}/api/patients/{patient_id}/physician/",
                    headers={"X-Internal-Token": os.getenv("INTERNAL_API_TOKEN", "")},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.debug("Physician lookup failed: %s", exc)
        return {"physician_id": "on_call", "name": "On-Call Physician"}

    def _select_channels(self, priority: str) -> List[str]:
        """Select notification channels based on priority."""
        channel_map = {
            "CRITICAL": ["sms", "push", "in_app", "ehr_inbox"],
            "URGENT": ["push", "in_app", "ehr_inbox"],
            "SOON": ["in_app", "ehr_inbox", "email"],
            "ROUTINE": ["ehr_inbox", "email"],
        }
        return channel_map.get(priority, ["ehr_inbox"])

    async def _track_notification(self, record: Dict[str, Any]) -> None:
        """Store notification tracking record in Redis."""
        try:
            url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            redis = await aioredis.from_url(url, decode_responses=True)
            key = f"notification:physician:{record['notification_id']}"
            await redis.setex(key, 86400 * 7, json.dumps(record))
            await redis.aclose()
        except Exception as exc:
            logger.debug("Notification tracking failed: %s", exc)

    async def _schedule_escalation(self, record: Dict[str, Any]) -> None:
        """Schedule an escalation check via Celery."""
        try:
            from celery import Celery

            celery_app = Celery(broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"))
            celery_app.send_task(
                "tasks.escalate_unacknowledged_notification",
                args=[record["notification_id"]],
                countdown=record["escalation_timeout_seconds"],
            )
            logger.info(
                "Escalation scheduled for notification %s in %ds",
                record["notification_id"],
                record["escalation_timeout_seconds"],
            )
        except Exception as exc:
            logger.warning("Celery escalation scheduling failed: %s", exc)

    def _fallback_notification(
        self,
        patient_id: str,
        priority: str,
        alerts: List[Dict[str, Any]],
    ) -> str:
        alert_lines = "\n".join([f"- {a.get('message', '')[:100]}" for a in alerts])
        return (
            f"[{priority}] Patient {patient_id}\n"
            f"Active alerts:\n{alert_lines}\n"
            f"Please review patient chart and take appropriate action."
        )
