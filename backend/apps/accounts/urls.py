"""
URL configuration for the accounts app.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AuditLogView,
    ChangePasswordView,
    LoginView,
    LogoutView,
    MFASetupView,
    ProfileView,
    RegisterView,
    VerifyEmailView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("mfa/setup/", MFASetupView.as_view(), name="mfa-setup"),
    path("mfa/verify/", MFASetupView.as_view(), name="mfa-verify"),
    path("mfa/disable/", MFASetupView.as_view(), name="mfa-disable"),
    path("audit-logs/", AuditLogView.as_view(), name="audit-logs"),
]
