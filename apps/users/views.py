import logging
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_social_auth.views import SocialJWTPairOnlyAuthView, SocialJWTPairUserAuthView
from social_django.models import UserSocialAuth

from apps.home.models import AboutAndNoticeSection
from apps.orders.models import Order
from apps.routines.models import FaceScan
from apps.translations.models import Translation
from apps.users.models import ActivationKey, PasswordKey, User
from apps.users.serializers import (
    BasePasswordSerializer,
    ChangeLanguageSerializer,
    ChangePasswordSerializer,
    ForgottenPasswordSerializer,
    JWTWithClaimPairSerializer,
    LoginSerializer,
    MultiClientOAuth2InputSerializer,
    SignUpSerializer,
    UserJWTWithClaimPairSerializer,
    UserSerializer,
    VerificationEmailResendSerializer,
    UserSettingsSerializer,
)
from apps.utils.error_codes import Errors
from apps.utils.token import get_token

LOGGER = logging.getLogger("app")


class RedirectGetActionToAppView(TemplateResponseMixin, ContextMixin, APIView):
    template_name = "redirect-template.html"
    permission_classes = (permissions.AllowAny,)

    def _get_path_and_key(self, request):
        path = request.path[len("/api/users/redirect-to-app/") :]  # noqa: E203
        path = path.strip("/")

        key = None
        if "/" in path:
            path, key = path.split("/")

        return path, key

    def get(self, request, *args, **kwargs):
        language = settings.DEFAULT_LANGUAGE

        path, key = self._get_path_and_key(request)

        if path == "reset-password":
            password_reset = PasswordKey.objects.filter(password_key=key).first()
            if password_reset:
                language = password_reset.user.language

        if path == "verify-email":
            activation_key = ActivationKey.objects.filter(activation_key=key).first()
            if activation_key:
                language = activation_key.user.language

        messages = [
            "msg_redirect_title",
            "msg_redirect_subtitle",
            "msg_redirect_button",
        ]
        translations = Translation.objects.filter(
            language=language,
            message__message_id__in=messages,
        ).values("message__message_id", "text")

        translations = {translation["message__message_id"]: translation["text"] for translation in translations}

        app_url = f"{settings.MOBILE_LINK_PROTOCOL}{path}"
        if key:
            app_url += f"/{key}"
        context = {"url": app_url}

        for message in messages:
            context[message] = translations.get(message, message)

        return self.render_to_response(context)


class SignUpView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = SignUpSerializer


class LoginView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer


class UserView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(instance=request.user).data)

    @extend_schema(responses=UserSerializer)
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(responses=UserSerializer)
    def patch(self, request: Request) -> Response:
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class VerifyUserView(APIView):
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def put(request, activation_key):
        del request
        activation_key = get_object_or_404(ActivationKey, activation_key=str(activation_key))
        activated = activation_key.activate()
        if not activated:
            raise ValidationError(Errors.USER_ALREADY_VERIFIED.value)

        refresh = get_token(activation_key.user)
        token = refresh.access_token

        activation_key.delete()
        return Response(
            status=status.HTTP_200_OK,
            data={"refresh": str(refresh), "token": str(token)},
        )


class ChangeLanguageView(APIView):
    def post(self, request):
        serializer = ChangeLanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lang = serializer.validated_data["language"]
        request.user.change_language(lang)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(generics.CreateAPIView):
    serializer_class = ChangePasswordSerializer


class ForgottenPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = ForgottenPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResendVerificationView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = VerificationEmailResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def put(request, password_key):
        password_key = get_object_or_404(PasswordKey, password_key=str(password_key))
        if not password_key.validate_expiration():
            password_key.delete()
            return Response(
                {"detail": Errors.RESET_PASSWORD_KEY_EXPIRED},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BasePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password_key.user.set_password(serializer.validated_data["password"])
        password_key.user.save()

        # On success - deleting all the remaining password keys and authentication keys
        password_key.user.password_keys.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TokenRefreshViewWithActiveChecks(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        access_token = response.data.get("access")
        if access_token:
            self._validate_user_state(access_token)
        return response

    @staticmethod
    def _validate_user_state(access_token: str) -> None:
        token = AccessToken(token=access_token)
        user_id = token.get("user_id")
        user = User.objects.filter(id=user_id).first() if user_id else None
        if not user:
            raise ValidationError(Errors.USER_DOES_NOT_EXIST.value)
        if user.password_last_change and int(user.password_last_change.timestamp()) != token["datetime_claim"]:
            raise ValidationError(Errors.USER_DATETIME_CLAIM_CHANGED.value)
        if not user.is_active:
            raise ValidationError(Errors.USER_IS_NOT_ACTIVE.value)


class SocialJWTErrorHandlingAuthViewMixin(object):
    def respond_error(self, error):
        """Override due a bug in a lib - unable to parse error responses properly."""
        if hasattr(error, "response"):
            if response := getattr(error, "response", None):
                response_json = response.json()
                error = response_json.get("error_description", response_json.get("error", error))
            elif custom_error_msg := getattr(error, "error", None):
                error = custom_error_msg
        return super().respond_error(error)


class SocialJWTWithClaimPairOnlyAuthView(SocialJWTErrorHandlingAuthViewMixin, SocialJWTPairOnlyAuthView):
    oauth2_serializer_class_in = MultiClientOAuth2InputSerializer
    serializer_class = JWTWithClaimPairSerializer


class SocialJWTWithClaimPairUserAuthView(SocialJWTErrorHandlingAuthViewMixin, SocialJWTPairUserAuthView):
    serializer_class = UserJWTWithClaimPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return response

    def get_object(self) -> User:
        user = super().get_object()
        if user.is_new:
            about_and_notice_sections = AboutAndNoticeSection.get_latest_versions()
            for about_and_notice_section in about_and_notice_sections:
                user.user_accepted_about_and_notice_section.get_or_create(
                    about_and_notice_section=about_and_notice_section
                )
            user.verify()
        return user


class DeactivateUserView(APIView):
    def delete(self, request):
        """
        Removes/depersonalises sensitive user's data
        """
        user = request.user

        try:
            ActivationKey.objects.filter(user=user).delete()
        except ActivationKey.DoesNotExist:
            pass

        try:
            UserSocialAuth.objects.filter(user=user).delete()
        except UserSocialAuth.DoesNotExist:
            pass

        Order.objects.filter(user=user).update(shopify_order_id=settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD)

        user_face_scans = FaceScan.objects.filter(user=user)
        for face_scan in user_face_scans:
            face_scan.image.delete()

        user.avatar.delete(save=False)
        user.is_active = False
        user.is_verified = False
        user.first_name = settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD
        user.last_name = settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD
        user.email = f"{settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD}_{uuid.uuid4()}"
        user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserSettingsViewSet(viewsets.GenericViewSet):
    serializer_class = UserSettingsSerializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.filter(user=self.request.user)

    @action(
        methods=["get", "post", "put", "patch", "delete"],
        detail=False,
        url_path="settings",
    )
    def user_settings(self, request):
        partial = False
        instance = self.get_queryset().first()
        method = self.request.method.lower()

        if method == "delete" and instance:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif method in ["get", "delete"] and not instance:
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            if method == "patch":
                partial = True
            serializer = self.serializer_class(instance=instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            if method != "get":
                serializer.save(user=self.request.user)
        return Response(serializer.data)
