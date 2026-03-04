"""
Celery tasks for HL7 message processing.
"""

import logging

from celery import shared_task

logger = logging.getLogger("apps.hl7")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_hl7_message(self, message_id: str):
    """Process a stored HL7 message asynchronously."""
    try:
        from .models import HL7Message
        from .processor import HL7Processor

        hl7_record = HL7Message.objects.get(id=message_id)
        processor = HL7Processor(tenant=hl7_record.tenant)
        success, error = processor.process(hl7_record)

        if not success:
            logger.error(f"HL7 processing failed for {message_id}: {error}")
            raise self.retry(exc=ValueError(error))

        return {"status": "processed", "message_id": message_id}
    except HL7Message.DoesNotExist:  # type: ignore
        logger.error(f"HL7Message not found: {message_id}")
        raise
    except Exception as exc:
        logger.error(f"Unexpected error processing HL7 message {message_id}: {exc}")
        raise self.retry(exc=exc)
