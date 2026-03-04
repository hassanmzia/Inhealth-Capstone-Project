"""
Notification channel adapters for SMS (Twilio), Email (SendGrid), Push.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from django.conf import settings

logger = logging.getLogger("apps.notifications")


class NotificationChannelBase(ABC):
    """Base class for all notification channel adapters."""

    @abstractmethod
    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> tuple[bool, str]:
        """
        Send a notification.
        Returns (success: bool, external_message_id: str).
        """
        ...


class SMSAdapter(NotificationChannelBase):
    """Twilio SMS adapter."""

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            from twilio.rest import Client
            sid = settings.TWILIO_ACCOUNT_SID
            token = settings.TWILIO_AUTH_TOKEN
            if sid and token:
                self.client = Client(sid, token)
        except ImportError:
            logger.warning("Twilio not installed. SMS will be logged only.")
        except Exception as e:
            logger.error(f"Twilio client init failed: {e}")

    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> tuple[bool, str]:
        if not self.client:
            logger.info(f"[SMS MOCK] To: {recipient} | Body: {body[:100]}")
            return True, "mock_sid_" + recipient[-4:]

        try:
            message = self.client.messages.create(
                body=body[:1600],  # SMS limit
                from_=settings.TWILIO_FROM_NUMBER,
                to=recipient,
            )
            logger.info(f"SMS sent to {recipient}: SID={message.sid}")
            return True, message.sid
        except Exception as e:
            logger.error(f"SMS send failed to {recipient}: {e}")
            return False, str(e)


class EmailAdapter(NotificationChannelBase):
    """SendGrid email adapter."""

    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> tuple[bool, str]:
        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
            message = Mail(
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_emails=To(recipient),
                subject=subject,
                html_content=Content("text/html", f"<p>{body}</p>"),
            )
            response = sg.send(message)
            message_id = response.headers.get("X-Message-Id", "")
            logger.info(f"Email sent to {recipient}: {message_id}")
            return True, message_id
        except ImportError:
            # Fallback to Django's email backend
            from django.core.mail import send_mail
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])
                return True, "django_email"
            except Exception as e:
                logger.error(f"Email send failed: {e}")
                return False, str(e)
        except Exception as e:
            logger.error(f"SendGrid send failed to {recipient}: {e}")
            return False, str(e)


class PushNotificationAdapter(NotificationChannelBase):
    """Firebase Cloud Messaging push notification adapter."""

    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> tuple[bool, str]:
        """
        recipient here is the FCM device token.
        """
        try:
            import firebase_admin
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(title=subject, body=body[:200]),
                token=recipient,
                data={k: str(v) for k, v in (metadata or {}).items()},
            )
            response = messaging.send(message)
            logger.info(f"Push sent: {response}")
            return True, response
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return False, str(e)


class EHRAlertAdapter(NotificationChannelBase):
    """In-app EHR alert — stored in the database and surfaced via WebSocket."""

    def send(self, recipient: str, subject: str, body: str, metadata: dict = None) -> tuple[bool, str]:
        """
        recipient here is the patient's FHIR ID.
        Publishes to Redis channel for real-time WebSocket delivery.
        """
        try:
            import json
            import redis
            from django.conf import settings

            r = redis.from_url(settings.REDIS_URL)
            channel = f"ehr_alerts:{recipient}"
            payload = json.dumps({
                "type": "alert",
                "subject": subject,
                "body": body,
                "metadata": metadata or {},
            })
            r.publish(channel, payload)
            return True, f"ehr_pubsub_{recipient}"
        except Exception as e:
            logger.error(f"EHR alert publish failed: {e}")
            return False, str(e)


def get_channel_adapter(channel: str) -> NotificationChannelBase:
    """Factory function returning the appropriate channel adapter."""
    adapters = {
        "sms": SMSAdapter,
        "email": EmailAdapter,
        "push": PushNotificationAdapter,
        "ehr": EHRAlertAdapter,
    }
    cls = adapters.get(channel)
    if cls is None:
        raise ValueError(f"Unknown notification channel: {channel}")
    return cls()
