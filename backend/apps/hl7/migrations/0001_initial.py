"""Initial migration for the hl7 app."""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
        ("fhir", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HL7Message",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("message_type", models.CharField(
                    choices=[
                        ("ADT_A01", "ADT^A01 \u2014 Admit/Visit Notification"),
                        ("ADT_A02", "ADT^A02 \u2014 Transfer a Patient"),
                        ("ADT_A03", "ADT^A03 \u2014 Discharge Patient"),
                        ("ADT_A04", "ADT^A04 \u2014 Register a Patient"),
                        ("ADT_A08", "ADT^A08 \u2014 Update Patient Information"),
                        ("ADT_A11", "ADT^A11 \u2014 Cancel Admit"),
                        ("ORU_R01", "ORU^R01 \u2014 Unsolicited Observation Message"),
                        ("ORM_O01", "ORM^O01 \u2014 Order Message"),
                        ("MDM_T02", "MDM^T02 \u2014 Original Document Notification"),
                        ("SIU_S12", "SIU^S12 \u2014 Appointment Notification"),
                        ("BAR_P01", "BAR^P01 \u2014 Add Patient Account"),
                    ],
                    db_index=True,
                    max_length=20,
                )),
                ("raw_message", models.TextField()),
                ("parsed_data", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(
                    choices=[
                        ("received", "Received"),
                        ("processing", "Processing"),
                        ("processed", "Processed"),
                        ("error", "Error"),
                        ("rejected", "Rejected"),
                    ],
                    db_index=True,
                    default="received",
                    max_length=15,
                )),
                ("error_message", models.TextField(blank=True, default="")),
                ("sending_application", models.CharField(blank=True, default="", max_length=100)),
                ("sending_facility", models.CharField(blank=True, default="", max_length=100)),
                ("message_control_id", models.CharField(blank=True, db_index=True, default="", max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("patient", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="hl7_messages",
                    to="fhir.fhirpatient",
                )),
                ("tenant", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["status", "created_at"], name="hl7_msg_status_created_idx"),
                    models.Index(fields=["tenant", "message_type", "created_at"], name="hl7_msg_tenant_type_idx"),
                ],
            },
        ),
    ]
