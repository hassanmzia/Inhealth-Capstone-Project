from django.contrib import admin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import AuditLog, RefreshTokenBlacklist, User


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Raw passwords are not stored. Use the Django shell or "
            '<a href="../password/">this form</a> to change it.'
        ),
    )

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserChangeForm

    list_display = ("email", "first_name", "last_name", "role", "is_active", "email_verified", "date_joined")
    list_filter = ("role", "is_active", "email_verified", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("id", "date_joined", "last_activity", "last_login", "last_login_ip")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone_number", "profile_picture", "preferred_language")}),
        (_("Role & tenant"), {"fields": ("role", "tenant", "specialty", "license_number", "npi_number")}),
        (
            _("Account status"),
            {"fields": ("is_active", "email_verified", "email_verification_token", "health_literacy_level")},
        ),
        (_("Security"), {"fields": ("is_mfa_enabled", "failed_login_attempts", "locked_until", "last_login_ip")}),
        (_("Permissions"), {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("date_joined", "last_login", "last_activity")}),
    )

    actions = ["activate_users", "deactivate_users", "mark_email_verified"]

    @admin.action(description="Activate selected users (set is_active=True)")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.")

    @admin.action(description="Deactivate selected users (set is_active=False)")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.")

    @admin.action(description="Mark email as verified and activate account")
    def mark_email_verified(self, request, queryset):
        updated = queryset.update(email_verified=True, is_active=True, email_verification_token=None)
        self.message_user(request, f"{updated} user(s) verified and activated.")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "resource_type", "timestamp", "phi_accessed", "ip_address")
    list_filter = ("action", "phi_accessed")
    search_fields = ("user__email", "resource_type", "ip_address")
    ordering = ("-timestamp",)
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RefreshTokenBlacklist)
class RefreshTokenBlacklistAdmin(admin.ModelAdmin):
    list_display = ("user", "reason", "blacklisted_at")
    list_filter = ("reason",)
    search_fields = ("user__email",)
    ordering = ("-blacklisted_at",)
    readonly_fields = [f.name for f in RefreshTokenBlacklist._meta.fields]

    def has_add_permission(self, request):
        return False
