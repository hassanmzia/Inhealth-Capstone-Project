"""
HL7 message processor — converts HL7 v2 messages to FHIR resources.
"""

import logging
from typing import Optional, Tuple

from django.db import transaction
from django.utils import timezone

from apps.fhir.models import FHIRObservation, FHIRPatient

from .parser import HL7Message, HL7Parser
from .models import HL7Message as HL7MessageModel

logger = logging.getLogger("apps.hl7")


class HL7Processor:
    """
    Processes inbound HL7 v2 messages:
    1. Parse the raw message
    2. Identify the message type
    3. Dispatch to the appropriate handler
    4. Create/update FHIR resources
    """

    def __init__(self, tenant=None):
        self.parser = HL7Parser()
        self.tenant = tenant

    @transaction.atomic
    def process(self, hl7_msg_model: HL7MessageModel) -> Tuple[bool, str]:
        """
        Process a stored HL7 message record.
        Returns (success, error_message).
        """
        hl7_msg_model.status = "processing"
        hl7_msg_model.save(update_fields=["status"])

        try:
            parsed = self.parser.parse(hl7_msg_model.raw_message)
            hl7_msg_model.parsed_data = self._to_dict(parsed)

            msg_type = parsed.message_type
            event = parsed.message_event

            handler_map = {
                "ADT": self._handle_adt,
                "ORU": self._handle_oru,
                "ORM": self._handle_orm,
            }

            handler = handler_map.get(msg_type)
            if handler is None:
                raise ValueError(f"Unsupported HL7 message type: {msg_type}^{event}")

            handler(parsed, hl7_msg_model)

            hl7_msg_model.status = "processed"
            hl7_msg_model.processed_at = timezone.now()
            hl7_msg_model.save(update_fields=["status", "processed_at", "parsed_data"])
            return True, ""

        except Exception as e:
            logger.error(f"HL7 processing error for message {hl7_msg_model.id}: {e}", exc_info=True)
            hl7_msg_model.status = "error"
            hl7_msg_model.error_message = str(e)
            hl7_msg_model.save(update_fields=["status", "error_message"])
            return False, str(e)

    def _handle_adt(self, parsed: HL7Message, hl7_msg_model: HL7MessageModel):
        """Handle ADT (Admission/Discharge/Transfer) messages."""
        patient_data = self.parser.extract_patient_data(parsed)
        if not patient_data.get("mrn"):
            raise ValueError("ADT message missing patient MRN (PID-3)")

        tenant = hl7_msg_model.tenant or self.tenant
        if not tenant:
            raise ValueError("No tenant context for HL7 message")

        # Find or create FHIR patient
        patient, created = FHIRPatient.objects.get_or_create(
            mrn=patient_data["mrn"],
            tenant=tenant,
            defaults={
                "fhir_id": str(__import__("uuid").uuid4()),
                "first_name": patient_data.get("first_name", ""),
                "last_name": patient_data.get("last_name", ""),
                "middle_name": patient_data.get("middle_name", ""),
                "birth_date": patient_data.get("birth_date") or "1900-01-01",
                "gender": patient_data.get("gender", "unknown"),
                "phone": patient_data.get("phone", ""),
                "address_line1": patient_data.get("address_line1", ""),
                "city": patient_data.get("city", ""),
                "state": patient_data.get("state", ""),
                "postal_code": patient_data.get("postal_code", ""),
                "country": patient_data.get("country", "US"),
                "ssn_last4": patient_data.get("ssn_last4", ""),
            },
        )

        if not created:
            # Update existing patient
            for field_name in ("first_name", "last_name", "middle_name", "gender", "phone"):
                if patient_data.get(field_name):
                    setattr(patient, field_name, patient_data[field_name])
            patient.save()

        hl7_msg_model.patient = patient
        logger.info(f"ADT processed: patient {patient.mrn} ({'created' if created else 'updated'})")

    def _handle_oru(self, parsed: HL7Message, hl7_msg_model: HL7MessageModel):
        """Handle ORU^R01 (Observation Results) messages — lab results."""
        # First, identify the patient
        patient_data = self.parser.extract_patient_data(parsed)
        tenant = hl7_msg_model.tenant or self.tenant

        try:
            patient = FHIRPatient.objects.get(mrn=patient_data.get("mrn", ""), tenant=tenant)
            hl7_msg_model.patient = patient
        except FHIRPatient.DoesNotExist:
            raise ValueError(f"Patient MRN {patient_data.get('mrn')} not found. Process ADT first.")

        # Extract observations
        observations = self.parser.extract_observations(parsed)
        for obs_data in observations:
            if not obs_data.get("code"):
                continue
            FHIRObservation.objects.create(
                tenant=tenant,
                fhir_id=str(__import__("uuid").uuid4()),
                patient=patient,
                status=obs_data.get("status", "final"),
                code=obs_data.get("code", ""),
                display=obs_data.get("display", ""),
                code_system=obs_data.get("code_system", "http://loinc.org"),
                value_quantity=obs_data.get("value_quantity"),
                value_unit=obs_data.get("value_unit", ""),
                value_string=obs_data.get("value_string", ""),
                reference_range_low=obs_data.get("reference_range_low"),
                reference_range_high=obs_data.get("reference_range_high"),
                interpretation=obs_data.get("interpretation", ""),
                effective_datetime=obs_data.get("effective_datetime") or timezone.now(),
            )

        logger.info(f"ORU processed: {len(observations)} observations created for patient {patient.mrn}")

    def _handle_orm(self, parsed: HL7Message, hl7_msg_model: HL7MessageModel):
        """Handle ORM^O01 (Order) messages."""
        patient_data = self.parser.extract_patient_data(parsed)
        orders = self.parser.extract_orders(parsed)
        logger.info(f"ORM processed: {len(orders)} orders for MRN {patient_data.get('mrn')}")

    @staticmethod
    def _to_dict(parsed: HL7Message) -> dict:
        return {
            "message_type": parsed.message_type,
            "message_event": parsed.message_event,
            "message_control_id": parsed.message_control_id,
            "sending_application": parsed.sending_application,
            "sending_facility": parsed.sending_facility,
            "segment_count": len(parsed.segments),
            "segments": [s.segment_id for s in parsed.segments],
        }
