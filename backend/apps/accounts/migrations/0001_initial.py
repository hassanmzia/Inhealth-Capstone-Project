import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0001_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        db_index=True,
                        max_length=254,
                        unique=True,
                        verbose_name="email address",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(max_length=150, verbose_name="first name"),
                ),
                (
                    "last_name",
                    models.CharField(max_length=150, verbose_name="last name"),
                ),
                ("phone_number", models.CharField(blank=True, default="", max_length=20)),
                (
                    "profile_picture",
                    models.ImageField(
                        blank=True, null=True, upload_to="profiles/%Y/%m/"
                    ),
                ),
                (
                    "preferred_language",
                    models.CharField(blank=True, default="en", max_length=10),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("super_admin", "Super Administrator"),
                            ("org_admin", "Organization Administrator"),
                            ("physician", "Physician"),
                            ("nurse", "Nurse / NP / PA"),
                            ("patient", "Patient"),
                            ("pharmacist", "Pharmacist"),
                            ("billing", "Billing Specialist"),
                            ("researcher", "Clinical Researcher"),
                        ],
                        db_index=True,
                        default="patient",
                        max_length=20,
                    ),
                ),
                ("specialty", models.CharField(blank=True, default="", max_length=100)),
                (
                    "license_number",
                    models.CharField(blank=True, default="", max_length=50),
                ),
                ("npi_number", models.CharField(blank=True, default="", max_length=10)),
                ("is_mfa_enabled", models.BooleanField(default=False)),
                ("mfa_secret", models.CharField(blank=True, default="", max_length=255)),
                (
                    "health_literacy_level",
                    models.IntegerField(
                        blank=True,
                        choices=[
                            (1, "Minimal (< 6th grade)"),
                            (2, "Limited (6th\u20138th grade)"),
                            (3, "Adequate (high school)"),
                            (4, "Proficient (college level)"),
                            (5, "Expert (healthcare professional)"),
                        ],
                        help_text="Health literacy level (1=minimal, 5=expert) \u2014 for patient users only",
                        null=True,
                    ),
                ),
                (
                    "last_login_ip",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                (
                    "failed_login_attempts",
                    models.PositiveSmallIntegerField(default=0),
                ),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                (
                    "date_joined",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("last_activity", models.DateTimeField(blank=True, null=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="users",
                        to="tenants.organization",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "Create"),
                            ("read", "Read"),
                            ("update", "Update"),
                            ("delete", "Delete"),
                            ("login", "Login"),
                            ("logout", "Logout"),
                            ("export", "Export"),
                            ("print", "Print"),
                            ("share", "Share"),
                            ("prescribe", "Prescribe"),
                            ("order", "Order"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(db_index=True, max_length=100),
                ),
                (
                    "resource_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                ("user_agent", models.TextField(blank=True, default="")),
                (
                    "timestamp",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
                ("phi_accessed", models.BooleanField(db_index=True, default=False)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("tenant_id", models.UUIDField(blank=True, db_index=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
                "default_permissions": ("add", "view"),
            },
        ),
        migrations.CreateModel(
            name="RefreshTokenBlacklist",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "token_hash",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                (
                    "blacklisted_at",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("logout", "User Logout"),
                            ("logout_all", "Logout All Devices"),
                            ("password_change", "Password Changed"),
                            ("security_revoke", "Security Revocation"),
                            ("account_locked", "Account Locked"),
                            ("suspicious_activity", "Suspicious Activity Detected"),
                        ],
                        default="logout",
                        max_length=30,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blacklisted_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-blacklisted_at"],
            },
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(
                fields=["tenant", "role"],
                name="accounts_user_tenant_id_role_2f62a0_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(
                fields=["email", "is_active"],
                name="accounts_user_email_is_active_186ac1_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["user", "timestamp"]),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["resource_type", "resource_id"]),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["phi_accessed", "timestamp"]),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["tenant_id", "timestamp"]),
        ),
        migrations.AddIndex(
            model_name="refreshtokenblacklist",
            index=models.Index(
                fields=["user", "blacklisted_at"],
                name="accounts_refresht_user_id_blacklisted_at_bf2d2f_idx",
            ),
        ),
    ]
