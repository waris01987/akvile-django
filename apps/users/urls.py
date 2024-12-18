from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenVerifyView

from apps.users.views import (
    ChangeLanguageView,
    ChangePasswordView,
    DeactivateUserView,
    ForgottenPasswordView,
    UserView,
    LoginView,
    RedirectGetActionToAppView,
    ResendVerificationView,
    ResetPasswordView,
    SignUpView,
    SocialJWTWithClaimPairOnlyAuthView,
    SocialJWTWithClaimPairUserAuthView,
    TokenRefreshViewWithActiveChecks,
    VerifyUserView,
    UserSettingsViewSet,
)

router = DefaultRouter()
router.register("", UserSettingsViewSet, basename="user-settings")

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path(
        "token/refresh/",
        TokenRefreshViewWithActiveChecks.as_view(),
        name="token-refresh",
    ),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("user/", UserView.as_view(), name="user"),
    path("verify/<uuid:activation_key>/", VerifyUserView.as_view(), name="verify"),
    path("change-language/", ChangeLanguageView.as_view(), name="change-language"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("forgot/", ForgottenPasswordView.as_view(), name="forgot"),
    path("deactivate/", DeactivateUserView.as_view(), name="deactivate"),
    path(
        "reset-password/<uuid:password_key>/",
        ResetPasswordView.as_view(),
        name="reset-password",
    ),
    path(
        "resend-verification/",
        ResendVerificationView.as_view(),
        name="resend-verification",
    ),
    path(
        "social/jwt-pair/",
        SocialJWTWithClaimPairOnlyAuthView.as_view(),
        name="login_social_jwt_pair",
    ),
    path(
        "social/jwt-pair-user/",
        SocialJWTWithClaimPairUserAuthView.as_view(),
        name="login_social_jwt_pair_user",
    ),
    path(
        "redirect-to-app/<slug:app_path>/<uuid:uuid>/",
        RedirectGetActionToAppView.as_view(),
        name="redirect-to-app-with-uuid",
    ),
    path("", include(router.urls)),
]
