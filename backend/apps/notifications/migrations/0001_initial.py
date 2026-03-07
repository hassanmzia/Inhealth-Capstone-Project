"""Initial migration for the notifications app."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenants", "0001_initial"),
        ("fhir", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("notification_type", models.CharField(max_length=20)),
                ("health_literacy_level", models.IntegerField(
                    choices=[
                        (1, "Minimal (< 6th grade)"),
                        (2, "Limited (6th-8th grade)"),
                        (3, "Adequate (high school)"),
                        (4, "Proficient (college)"),
                        (5, "Expert (healthcare professional)"),
                    ],
                    default=3,
                )),
                ("language", models.CharField(default="en", max_length=10)),
                ("subject_template", models.CharField(max_length=255)),
                ("body_template", models.TextField()),
                ("channel", models.CharField(default="all", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "unique_together": {("name", "health_literacy_level", "language")},
            },
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("notification_type", models.CharField(
                    choices=[
                        ("CRITICAL", "Critical \u2014 Immediate Action Required"),
                        ("URGENT", "Urgent \u2014 Action Required Today"),
                        ("SOON", "Soon \u2014 Action Required This Week"),
                        ("ROUTINE", "Routine \u2014 General Information"),
                        ("EDUCATIONAL", "Educational Content"),
                        ("APPOINTMENT", "Appointment Reminder"),
                    ],
                    db_index=True,
                    default="ROUTINE",
                    max_length=20,
                )),
                ("channel", models.CharField(
                    choices=[
                        ("sms", "SMS Text Message"),
                        ("email", "Email"),
                        ("push", "Push Notification"),
                        ("ehr", "In-App EHR Alert"),
                        ("phone", "Phone Call"),
                        ("all", "All Channels"),
                    ],
                    default="email",
                    max_length=10,
                )),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("metadata", models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='{"loinc_code": "4548-4", "value": 9.2, "threshold": 7.0}',
                )),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("queued", "Queued"),
                        ("sent", "Sent"),
                        ("delivered", "Delivered"),
                        ("failed", "Failed"),
                        ("acknowledged", "Acknowledged by Patient"),
                        ("escalated", "Escalated"),
                    ],
                    db_index=True,
                    default="pending",
                    max_length=15,
                )),
                ("agent_source", models.CharField(blank=True, default="", max_length=50)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.CharField(blank=True, default="", max_length=500)),
                ("retry_count", models.PositiveSmallIntegerField(default=0)),
                ("external_message_id", models.CharField(blank=True, default="", max_length=100)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("escalation_level", models.PositiveSmallIntegerField(default=0)),
                ("escalated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("acknowledged_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="acknowledged_notifications",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to="fhir.fhirpatient",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant", "notification_type", "status"], name="notif_tenant_type_status_idx"),
                    models.Index(fields=["patient", "status", "created_at"], name="notif_patient_status_idx"),
                    models.Index(fields=["status", "created_at"], name="notif_status_created_idx"),
                ],
            },
        ),
    ]
