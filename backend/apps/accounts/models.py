"""
Accounts models for InHealth Chronic Care.
Custom User model with HIPAA-compliant audit logging.
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom manager for the User model."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.SUPER_ADMIN)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Extended user model supporting multi-tenant clinical roles.
    HIPAA: all PHI access tracked via AuditLog.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", _("Super Administrator")
        ORG_ADMIN = "org_admin", _("Organization Administrator")
        PHYSICIAN = "physician", _("Physician")
        NURSE = "nurse", _("Nurse / NP / PA")
        PATIENT = "patient", _("Patient")
        PHARMACIST = "pharmacist", _("Pharmacist")
        BILLING = "billing", _("Billing Specialist")
        RESEARCHER = "researcher", _("Clinical Researcher")

    class HealthLiteracyLevel(models.IntegerChoices):
        MINIMAL = 1, _("Minimal (< 6th grade)")
        LIMITED = 2, _("Limited (6th–8th grade)")
        ADEQUATE = 3, _("Adequate (high school)")
        PROFICIENT = 4, _("Proficient (college level)")
        EXPERT = 5, _("Expert (healthcare professional)")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant linkage (nullable for super_admin who spans all tenants)
    tenant = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
        db_index=True,
    )

    # Identity
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    phone_number = models.CharField(max_length=20, blank=True, default="")
    profile_picture = models.ImageField(upload_to="profiles/%Y/%m/", blank=True, null=True)
    preferred_language = models.CharField(max_length=10, default="en", blank=True)

    # Role & credentials
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT, db_index=True)
    specialty = models.CharField(max_length=100, blank=True, default="")  # e.g., "Endocrinology"
    license_number = models.CharField(max_length=50, blank=True, default="")
    npi_number = models.CharField(max_length=10, blank=True, default="")  # National Provider Identifier

    # MFA
    is_mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=255, blank=True, default="")  # Encrypted TOTP secret

    # Patient-specific
    health_literacy_level = models.IntegerField(
        choices=HealthLiteracyLevel.choices,
        null=True,
        blank=True,
        help_text="Health literacy level (1=minimal, 5=expert) — for patient users only",
    )

    # Security metadata
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["email", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_clinician(self):
        return self.role in (self.Role.PHYSICIAN, self.Role.NURSE, self.Role.PHARMACIST)

    @property
    def is_provider(self):
        return self.role in (self.Role.PHYSICIAN, self.Role.NURSE)

    @property
    def is_account_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def record_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=15)
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def reset_login_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_attempts", "locked_until"])


class AuditLog(models.Model):
    """
    HIPAA-compliant audit log for all PHI access and clinical actions.
    Immutable — no update/delete operations should be performed.
    """

    class Action(models.TextChoices):
        CREATE = "create", _("Create")
        READ = "read", _("Read")
        UPDATE = "update", _("Update")
        DELETE = "delete", _("Delete")
        LOGIN = "login", _("Login")
        LOGOUT = "logout", _("Logout")
        EXPORT = "export", _("Export")
        PRINT = "print", _("Print")
        SHARE = "share", _("Share")
        PRESCRIBE = "prescribe", _("Prescribe")
        ORDER = "order", _("Order")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
        db_index=True,
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.UUIDField(null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    phi_accessed = models.BooleanField(default=False, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["phi_accessed", "timestamp"]),
            models.Index(fields=["tenant_id", "timestamp"]),
        ]
        # Audit logs should never be modified
        default_permissions = ("add", "view")

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.user} {self.action} {self.resource_type}:{self.resource_id}"

    def save(self, *args, **kwargs):
        # Prevent updates to existing audit log entries
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError("Audit log entries are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit log entries cannot be deleted.")


class RefreshTokenBlacklist(models.Model):
    """
    Blacklist for invalidated JWT refresh tokens.
    Used to implement logout-everywhere and security revocation.
    """

    class BlacklistReason(models.TextChoices):
        LOGOUT = "logout", _("User Logout")
        LOGOUT_ALL = "logout_all", _("Logout All Devices")
        PASSWORD_CHANGE = "password_change", _("Password Changed")
        SECURITY_REVOKE = "security_revoke", _("Security Revocation")
        ACCOUNT_LOCKED = "account_locked", _("Account Locked")
        SUSPICIOUS_ACTIVITY = "suspicious_activity", _("Suspicious Activity Detected")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="blacklisted_tokens",
    )
    blacklisted_at = models.DateTimeField(default=timezone.now, db_index=True)
    reason = models.CharField(
        max_length=30,
        choices=BlacklistReason.choices,
        default=BlacklistReason.LOGOUT,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-blacklisted_at"]
        indexes = [
            models.Index(fields=["user", "blacklisted_at"]),
        ]

    def __str__(self):
        return f"Blacklisted token for {self.user} at {self.blacklisted_at:%Y-%m-%d %H:%M:%S}"
