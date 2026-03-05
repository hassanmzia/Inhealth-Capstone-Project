"""
Account views: registration, login, profile, MFA, audit log.
"""

import hashlib
import logging
import pyotp
import qrcode
import io
import base64

from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import AuditLog, RefreshTokenBlacklist, User
from .permissions import IsOrgAdmin, IsSuperAdmin
from .serializers import (
    AuditLogSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    MFASetupSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from .tasks import send_verification_email, send_welcome_email

logger = logging.getLogger("apps.accounts")


class AuthRateThrottle(AnonRateThrottle):
    rate = "10/minute"
    scope = "auth"


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Register a new user. Requires org admin or open registration based on tenant config.
    """

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def perform_create(self, serializer):
        user = serializer.save()
        send_verification_email.delay(str(user.id))
        logger.info(f"New user registered: {user.email} with role {user.role}")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"message": "Registration successful. Please check your email to verify your account.", "user": serializer.data},
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Returns access + refresh JWT tokens with user metadata.
    """

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Log successful login
            user_email = request.data.get("email", "")
            try:
                user = User.objects.get(email=user_email)
                user.reset_login_attempts()
                user.last_login_ip = self._get_client_ip(request)
                user.save(update_fields=["last_login_ip", "failed_login_attempts", "locked_until"])
                logger.info(f"Successful login: {user_email} from {user.last_login_ip}")
            except User.DoesNotExist:
                pass
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the refresh token.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/auth/profile/
    View and update the authenticated user's profile.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/
    Change the current user's password and blacklist all tokens.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Keep session alive after password change
        update_session_auth_hash(request, request.user)
        return Response(
            {"message": "Password changed successfully. All other sessions have been invalidated."},
            status=status.HTTP_200_OK,
        )


class MFASetupView(APIView):
    """
    GET /api/v1/auth/mfa/setup/ — Generate TOTP secret and QR code
    POST /api/v1/auth/mfa/verify/ — Verify and enable MFA
    DELETE /api/v1/auth/mfa/disable/ — Disable MFA
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Generate a new TOTP secret and return QR code."""
        user = request.user
        # Generate new secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="InHealth Chronic Care",
        )
        # Generate QR code as base64 PNG
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Store secret temporarily (not yet enabled)
        from cryptography.fernet import Fernet
        import base64 as b64
        key = request.session.get("mfa_setup_key")
        if not key:
            key = Fernet.generate_key().decode()
            request.session["mfa_setup_key"] = key
        request.session["mfa_pending_secret"] = secret

        return Response({
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "provisioning_uri": provisioning_uri,
            "message": "Scan the QR code with your authenticator app, then POST the 6-digit code to /mfa/verify/",
        })

    def post(self, request):
        """Verify TOTP code and enable MFA."""
        serializer = MFASetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        secret = request.session.get("mfa_pending_secret")
        if not secret:
            return Response(
                {"error": {"code": "MFA_SETUP_EXPIRED", "message": "MFA setup session expired. Please start again."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(secret)
        if not totp.verify(serializer.validated_data["totp_code"], valid_window=1):
            return Response(
                {"error": {"code": "INVALID_TOTP", "message": "Invalid TOTP code. Please try again."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Enable MFA
        user = request.user
        user.mfa_secret = secret  # In production, encrypt this field
        user.is_mfa_enabled = True
        user.save(update_fields=["mfa_secret", "is_mfa_enabled"])
        del request.session["mfa_pending_secret"]

        return Response({"message": "MFA has been enabled successfully."}, status=status.HTTP_200_OK)

    def delete(self, request):
        """Disable MFA after password verification."""
        password = request.data.get("password")
        if not password or not request.user.check_password(password):
            return Response(
                {"error": {"code": "INVALID_PASSWORD", "message": "Password is required to disable MFA."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.is_mfa_enabled = False
        request.user.mfa_secret = ""
        request.user.save(update_fields=["is_mfa_enabled", "mfa_secret"])
        return Response({"message": "MFA has been disabled."}, status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """
    POST /api/v1/auth/verify-email/
    Verifies the email address using the token sent during registration.
    Activates the account and sends a welcome email.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Verification token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email_verification_token=token)
        except (User.DoesNotExist, Exception):
            return Response({"error": "Invalid or expired verification token."}, status=status.HTTP_400_BAD_REQUEST)

        if user.email_verified:
            return Response({"message": "Email already verified. You can log in."}, status=status.HTTP_200_OK)

        user.email_verified = True
        user.is_active = True
        user.email_verification_token = None
        user.save(update_fields=["email_verified", "is_active", "email_verification_token"])

        send_welcome_email.delay(str(user.id))
        logger.info(f"Email verified for user: {user.email}")

        return Response({"message": "Email verified successfully. You can now log in."}, status=status.HTTP_200_OK)


class AuditLogView(generics.ListAPIView):
    """
    GET /api/v1/auth/audit-logs/
    Returns audit log for the current user (or all logs for org admins).
    """

    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["action", "resource_type", "phi_accessed"]
    search_fields = ["resource_type", "ip_address"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]

    def get_queryset(self):
        user = self.request.user
        qs = AuditLog.objects.select_related("user")
        if user.role in (User.Role.SUPER_ADMIN, User.Role.ORG_ADMIN):
            # Admins can see all logs for their tenant
            if user.role == User.Role.ORG_ADMIN and user.tenant_id:
                qs = qs.filter(tenant_id=user.tenant_id)
        else:
            # Regular users can only see their own logs
            qs = qs.filter(user=user)
        return qs
