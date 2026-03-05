"""
Serializers for the accounts app.
Handles registration, login, profile management, and MFA.
"""

import hashlib

from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AuditLog, RefreshTokenBlacklist, User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for new user registration."""

    password = serializers.CharField(write_only=True, min_length=12, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "password",
            "password_confirm",
            "preferred_language",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "role": {"default": User.Role.PATIENT},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        password_validation.validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        # Account is inactive until email is verified
        validated_data["is_active"] = False
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for reading and updating user profiles."""

    full_name = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "role",
            "specialty",
            "license_number",
            "npi_number",
            "preferred_language",
            "health_literacy_level",
            "is_mfa_enabled",
            "profile_picture",
            "tenant_name",
            "date_joined",
            "last_activity",
        ]
        read_only_fields = ["id", "email", "role", "date_joined", "is_mfa_enabled", "full_name", "tenant_name"]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_tenant_name(self, obj):
        if obj.tenant:
            return obj.tenant.name
        return None


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change endpoint."""

    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, min_length=12, style={"input_type": "password"})
    new_password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        password_validation.validate_password(attrs["new_password"], self.context["request"].user)
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        # Blacklist all existing refresh tokens
        token_hash = hashlib.sha256(str(user.id).encode()).hexdigest()
        RefreshTokenBlacklist.objects.create(
            token_hash=token_hash,
            user=user,
            reason=RefreshTokenBlacklist.BlacklistReason.PASSWORD_CHANGE,
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Enhanced JWT serializer with role claims and security metadata."""

    def validate(self, attrs):
        # Give a clearer error when the account exists but email is unverified.
        email = attrs.get(self.username_field, "")
        try:
            user = User.objects.get(email=email)
            if not user.email_verified and not user.is_active:
                raise serializers.ValidationError(
                    "Your email address has not been verified. "
                    "Please check your inbox for the verification link."
                )
        except User.DoesNotExist:
            pass

        data = super().validate(attrs)
        user = self.user

        # Add custom claims to response
        data["user"] = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.get_full_name(),
            "role": user.role,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "is_mfa_enabled": user.is_mfa_enabled,
        }
        data["token_type"] = "Bearer"
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token["role"] = user.role
        token["tenant_id"] = str(user.tenant_id) if user.tenant_id else None
        token["email"] = user.email
        token["full_name"] = user.get_full_name()
        return token


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout — blacklists the refresh token."""

    refresh_token = serializers.CharField()

    def validate_refresh_token(self, value):
        try:
            token = RefreshToken(value)
            self._token = token
        except Exception:
            raise serializers.ValidationError("Invalid or expired refresh token.")
        return value

    def save(self):
        user = self.context["request"].user
        token_hash = hashlib.sha256(self.validated_data["refresh_token"].encode()).hexdigest()
        # Blacklist via simplejwt's built-in mechanism
        self._token.blacklist()
        # Also store in our custom blacklist for fast lookup
        RefreshTokenBlacklist.objects.get_or_create(
            token_hash=token_hash,
            defaults={
                "user": user,
                "reason": RefreshTokenBlacklist.BlacklistReason.LOGOUT,
            },
        )


class MFASetupSerializer(serializers.Serializer):
    """Serializer for MFA setup verification."""

    totp_code = serializers.CharField(max_length=6, min_length=6)

    def validate_totp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("TOTP code must be 6 digits.")
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for audit log entries."""

    user_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_email",
            "action",
            "resource_type",
            "resource_id",
            "ip_address",
            "timestamp",
            "phi_accessed",
            "details",
        ]
        read_only_fields = fields

    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return None
