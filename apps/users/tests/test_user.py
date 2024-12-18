from collections import defaultdict
import datetime
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from model_bakery.baker import make
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from social_core.backends.apple import AppleIdAuth
from social_core.backends.facebook import FacebookOAuth2
from social_core.backends.google import GoogleOAuth2
from social_core.backends.oauth import BaseOAuth2
from social_django.models import UserSocialAuth

from apps.content import AboutAndNoticeSectionType
from apps.home.models import (
    EmailTemplate,
    EmailTemplateTranslation,
    SiteConfiguration,
    AboutAndNoticeSection,
)
from apps.orders.models import Order
from apps.questionnaire.models import UserQuestionnaire
from apps.routines.models import FaceScan
from apps.translations.models import Language
from apps.users import SocialClient
from apps.users.models import ActivationKey, PasswordKey, User, UserSettings
from apps.utils.error_codes import Errors
from apps.utils.tests_utils import BaseTestCase


class AuthenticationTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        site_config = SiteConfiguration.get_solo()

        template_name = "verify_email_template"
        template = EmailTemplate.objects.create(name=template_name)
        language = Language.objects.get(code="en", name="English")
        subject = "create account"
        content = "{{ activationUrl }}"
        make(
            EmailTemplateTranslation,
            language=language,
            template=template,
            subject=subject,
            content=content,
        )
        setattr(site_config, template_name, template)

        template_name = "password_renewal_template"
        template = EmailTemplate.objects.create(name=template_name)
        language = Language.objects.get(code="en", name="English")
        subject = "reset password"
        content = "{{ passwordUrl }}"
        make(
            EmailTemplateTranslation,
            language=language,
            template=template,
            subject=subject,
            content=content,
        )

        setattr(site_config, template_name, template)
        site_config.enabled_languages.add(language)
        site_config.save()

    def test_login_valid(self):
        response = self.client.post(reverse("login"), self.credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["token"])
        self.assertTrue(response.data["refresh"])

    def test_login_invalid(self):
        credentials = {"email": "test@test.lt", "password": "password"}
        response = self.client.post(reverse("login"), credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["non_field_errors"][0], "error_login_bad_credentials")

    def test_token_refresh(self):
        response = self.client.post(reverse("login"), self.credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        refresh = response.data["refresh"]
        response = self.post(reverse("token-refresh"), {"refresh": refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["access"])
        self.assertTrue(response.data["refresh"])

    def test_token_refresh_after_password_change(self):
        response = self.client.post(reverse("login"), self.credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        refresh = response.data["refresh"]
        self.user.password_last_change = timezone.now() + datetime.timedelta(minutes=1)
        self.user.save()
        response = self.client.post(reverse("token-refresh"), {"refresh": refresh})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()[0], "error_user_datetime_claim_changed")

    def test_token_verify(self):
        response = self.client.post(reverse("login"), self.credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        token = response.data["token"]
        response = self.post(reverse("token-verify"), {"token": token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_delete_with_active_token(self):
        response = self.client.post(reverse("login"), self.credentials, format="json")
        User.objects.all().delete()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {response.data["token"]}')
        response = self.client.post(reverse("token-refresh"), {"refresh": response.data["refresh"]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()[0], "error_user_does_not_exist")

    def test_invalid_password(self):
        response = self.client.post(
            reverse("login"),
            {"email": self.user.email, "password": "invalid"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["non_field_errors"][0], "error_login_bad_credentials")

    def test_invalid_email(self):
        response = self.client.post(
            reverse("login"),
            {"email": "invalid@email", "password": self.user.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["email"][0], "error_invalid_email")

    def test_missing_email(self):
        response = self.client.post(reverse("login"), {"password": self.user.password}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["email"][0], "error_field_is_required")

    def test_missing_password(self):
        response = self.client.post(reverse("login"), {"email": self.user.email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["password"][0], "error_field_is_required")

    def test_get_user(self):
        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in ["first_name", "email", "id"]:
            self.assertEqual(response.data.get(field), getattr(self.user, field))
        self.assertEqual(response.json()["avatar"], None)
        self.assertEqual(response.json()["gender"], None)
        self.assertEqual(response.json()["geolocation"], "")
        self.assertEqual(response.json()["device"], "")
        self.assertEqual(response.json()["operating_system"], "")
        self.assertEqual(response.json()["questionnaire_id"], None)
        self.assertEqual(response.json()["is_questionnaire_finished"], False)
        self.assertTrue(response.json()["date_joined"])

    def test_get_user_with_avatar(self):
        self.user.avatar.name = "users_avatar.jpg"
        self.user.save()
        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in ["first_name", "email", "id"]:
            self.assertEqual(response.data.get(field), getattr(self.user, field))
        self.assertIn(self.user.avatar.url, response.json()["avatar"])
        self.assertEqual(response.json()["questionnaire_id"], None)
        self.assertEqual(response.json()["gender"], None)
        self.assertEqual(response.json()["is_questionnaire_finished"], False)
        self.assertTrue(response.json()["date_joined"])

    def test_get_user_with_device_data(self):
        self.user.geolocation = "Seattle, Washington, USA"
        self.user.device = "NOKIA 3310"
        self.user.operating_system = "Android 10"
        self.user.save()

        boolean_fields = {
            None: ["avatar", "gender", "questionnaire_id"],
            False: ["is_questionnaire_finished"],
        }
        expected_boolean = {field: value for value, fields in boolean_fields.items() for field in fields}
        specific_fields = [
            "first_name",
            "email",
            "id",
            "geolocation",
            "device",
            "operating_system",
            "date_joined",
        ]

        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in specific_fields + list(expected_boolean.keys()):
            expected = defaultdict(lambda: getattr(self.user, field), **expected_boolean)
            self.assertEqual(
                response.data.get(field),
                expected[field].strftime("%Y-%m-%dT%H:%M:%S.%fZ") if field == "date_joined" else expected[field],
                field,
            )

    def test_get_user_with_mandatory_questionnaire_questions_answered(self):
        questionnaire = make(
            UserQuestionnaire,
            user=self.user,
            skin_goal="LESS_SCARS",
            feeling_today="MEHHH",
            age="12-16_YEARS",
            gender="MALE",
        )
        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in ["first_name", "email", "id"]:
            self.assertEqual(response.data.get(field), getattr(self.user, field))
        self.assertEqual(response.json()["gender"], "MALE")
        self.assertEqual(response.json()["questionnaire_id"], str(questionnaire.id))
        self.assertEqual(response.json()["is_questionnaire_finished"], True)
        self.assertTrue(response.json()["date_joined"])

    def test_get_user_with_all_questionnaire_questions_answered(self):
        questionnaire = make(
            UserQuestionnaire,
            user=self.user,
            skin_goal="LESS_SCARS",
            feeling_today="MEHHH",
            age="12-16_YEARS",
            gender="MALE",
            skin_type="NORMAL_SKIN",
            skin_feel="SENSITIVE",
            expectations="ASAP",
            diet_balance="BALANCED",
            diet="DIARY_FREE",
            guilty_pleasures=["COFFEE_JUNKIE"],
            easily_stressed="MODERATE",
            hours_of_sleep="7",
            exercise_days_a_week="1",
        )
        response = self.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in ["first_name", "email", "id"]:
            self.assertEqual(response.data.get(field), getattr(self.user, field))
        self.assertEqual(response.json()["gender"], "MALE")
        self.assertEqual(response.json()["questionnaire_id"], str(questionnaire.id))
        self.assertEqual(response.json()["is_questionnaire_finished"], True)
        self.assertTrue(response.json()["date_joined"])

    def test_get_user_not_authorized(self):
        response = self.client.get(reverse("user"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["detail"], "Authentication credentials were not provided.")

    @patch.object(PasswordKey, "send_password_key")
    def test_forgot_password(self, mock):
        response = self.client.post(reverse("forgot"), data={"email": self.user.email})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(self.user.password_keys.count(), 1)
        self.assertEqual(PasswordKey.objects.count(), 1)
        self.assertTrue(mock.called)

    @patch.object(PasswordKey, "send_password_key")
    def test_forgot_password_non_existing_email(self, mock):
        response = self.client.post(reverse("forgot"), data={"email": "some@email.com"})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(PasswordKey.objects.count(), 0)
        self.assertFalse(mock.called)

    @patch.object(PasswordKey, "send_password_key")
    def test_reset_password_after_forgot_password(self, mock):
        del mock
        self.user.create_new_password_token()
        previous_psw = self.user.password
        uuid = str(uuid4())
        reset_key = self.user.create_new_password_token()
        response = self.client.put(
            reverse("reset-password", args=[reset_key]),
            data={"password": uuid, "confirm_password": uuid},
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.user.refresh_from_db()
        self.assertNotEqual(previous_psw, self.user.password)
        self.assertFalse(self.user.password_keys.count())

    @patch.object(PasswordKey, "send_password_key")
    def test_expired_password_key(self, mock):
        del mock
        reset_key = self.user.create_new_password_token()
        self.user.password_keys.update(
            expires_at=timezone.now() - datetime.timedelta(hours=settings.PASSWORD_TOKEN_EXPIRATION_PERIOD + 1)
        )
        response = self.client.put(reverse("reset-password", args=[reset_key]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.password_keys.count())

    def test_resend_verification_email_required_data(self):
        response = self.client.post(reverse("resend-verification"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["email"][0], "error_email_is_a_required_field")

    @patch.object(ActivationKey, "send_verification")
    def test_resend_verification_email_to_verified_user(self, mock):
        response = self.client.post(reverse("resend-verification"), data={"email": self.user.email})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertFalse(mock.called)

    @patch.object(ActivationKey, "send_verification")
    def test_resend_verification_email_to_unverified_user(self, mock):
        self.user.is_verified = False
        self.user.save()
        response = self.client.post(reverse("resend-verification"), data={"email": self.user.email})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertTrue(mock.called)

    @patch.object(ActivationKey, "send_verification")
    def test_verify_user(self, mock):
        del mock
        self.user.is_verified = False
        self.user.save()
        verification_key = self.user.create_activation_key()
        self.assertFalse(self.user.is_verified)
        response = self.client.put(reverse("verify", args=[verification_key]))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.json()["token"])
        self.assertTrue(response.json()["refresh"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertFalse(self.user.activation_keys.count())

    @patch.object(ActivationKey, "send_verification")
    def test_verify_user_again(self, mock):
        del mock
        verification_key = self.user.create_activation_key()
        self.user.is_verified = True
        self.user.save()
        self.assertTrue(self.user.is_verified)
        response = self.client.put(reverse("verify", args=[verification_key]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()[0], "error_verify_already_verified")

    def test_change_language(self):
        lang = make(Language)
        response = self.post(reverse("change-language"), data={"language": lang.code})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, lang)

    def test_change_to_invalid_language(self):
        response = self.post(reverse("change-language"), data={"language": "abc"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["language"][0], "error_no_such_language")

    def test_change_password(self):
        uuid = str(uuid4())
        previous_psw = self.user.password
        previous_psw_datetime = self.user.password_last_change
        response = self.post(
            reverse("change-password"),
            data={
                "old_password": self.credentials["password"],
                "password": uuid,
                "confirm_password": uuid,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.user.refresh_from_db()
        self.assertNotEqual(previous_psw, self.user.password)
        self.assertFalse(self.user.password_keys.all().count())
        self.assertNotEqual(self.user.password_last_change, previous_psw_datetime)
        self.assertTrue(response.json()["access"])
        self.assertTrue(response.json()["refresh"])
        response = self.client.post(reverse("token-refresh"), {"refresh": response.json()["refresh"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_change_password_not_equal(self):
        previous_psw = self.user.password
        response = self.post(
            reverse("change-password"),
            data={
                "old_password": self.credentials["password"],
                "password": str(uuid4()),
                "confirm_password": str(uuid4()),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(previous_psw, self.user.password)
        self.assertEqual(response.json()["non_field_errors"][0], "error_passwords_not_equal")

    @patch("apps.users.models.send_email_task.delay")
    def test_signup_endpoint_creates_new_user(self, mock):
        self.query_limits["ANY POST REQUEST"] = 8

        terms_of_service = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.TERMS_OF_SERVICE.value)
        privacy_policy = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.PRIVACY_POLICY.value)

        terms_of_service_v2 = make(
            AboutAndNoticeSection,
            type=terms_of_service.type,
            version=terms_of_service.version + 1,
        )
        privacy_policy_v2 = make(
            AboutAndNoticeSection,
            type=privacy_policy.type,
            version=privacy_policy.version + 1,
        )

        signup_url = reverse("signup")
        data = {
            "email": "test@test.com",
            "password": "aZvD1234D",
            "first_name": "Tester",
            "terms_of_service": terms_of_service_v2.id,
            "privacy_policy": privacy_policy_v2.id,
        }

        signup_response = self.client.post(signup_url, data, format="json")
        self.assertEqual(signup_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock.called)
        self.assertEqual(mock.call_args.args[1], "get_verification_template")
        self.assertEqual(signup_response.json()["first_name"], "Tester")
        self.assertEqual(signup_response.json()["email"], "test@test.com")

        # check if user was created properly
        user = User.objects.filter(email=data["email"]).first()
        self.assertIsNotNone(user)
        self.assertTrue(user.activation_keys.exists())
        self.assertFalse(user.is_verified)
        self.assertTrue(user.has_accepted_latest_terms_of_service)
        self.assertTrue(user.has_accepted_latest_privacy_policy)

    @patch("apps.users.models.send_email_task.delay")
    def test_signup_endpoint_creates_new_user_lower_version(self, mock):
        terms_of_service = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.TERMS_OF_SERVICE.value)
        privacy_policy = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.PRIVACY_POLICY.value)

        make(
            AboutAndNoticeSection,
            type=terms_of_service.type,
            version=terms_of_service.version + 1,
        )
        make(
            AboutAndNoticeSection,
            type=privacy_policy.type,
            version=privacy_policy.version + 1,
        )

        signup_url = reverse("signup")
        data = {
            "email": "test@test.com",
            "password": "aZvD1234D",
            "first_name": "Tester",
            "terms_of_service": terms_of_service.id,
            "privacy_policy": privacy_policy.id,
        }

        signup_response = self.client.post(signup_url, data, format="json")
        self.assertEqual(signup_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(mock.called)
        self.assertEqual(
            signup_response.json()["terms_of_service"],
            [Errors.INCORRECT_TERMS_OF_SERVICE_VERSION.value],
        )
        self.assertEqual(
            signup_response.json()["privacy_policy"],
            [Errors.INCORRECT_PRIVACY_POLICY_VERSION.value],
        )
        self.assertFalse(self.user.has_accepted_latest_terms_of_service)
        self.assertFalse(self.user.has_accepted_latest_privacy_policy)

    @patch("apps.users.models.send_email_task")
    def test_signup_with_upper_case_email(self, mock):
        del mock
        self.query_limits["ANY POST REQUEST"] = 8

        terms_of_service = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.TERMS_OF_SERVICE.value)
        privacy_policy = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.PRIVACY_POLICY.value)

        signup_url = reverse("signup")
        data = {
            "email": "TEST@TEST.com",
            "password": "aZvD1234D",
            "first_name": "Tester",
            "terms_of_service": terms_of_service.id,
            "privacy_policy": privacy_policy.id,
        }

        signup_response = self.client.post(signup_url, data, format="json")
        self.assertEqual(
            signup_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(signup_response.json()["email"], "test@test.com")

    def test_user_already_exists_during_signup(self):
        terms_of_service = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.TERMS_OF_SERVICE.value)
        privacy_policy = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.PRIVACY_POLICY.value)

        signup_url = reverse("signup")
        data = {
            "terms_of_service": terms_of_service.id,
            "privacy_policy": privacy_policy.id,
            **self.user_data,
        }
        response = self.client.post(signup_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"], ["error_email_already_exists"])

    def test_signup_endpoint_invalid_email_returns_error_code(self):
        signup_url = reverse("signup")
        data = {
            "email": "testtest.com",
            "password": "aZvD1234D",
            "first_name": "Tester",
        }
        signup_response = self.client.post(signup_url, data, format="json")
        self.assertEqual(signup_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(signup_response.json()["email"][0], "error_invalid_email")

    def test_signup_endpoint_without_providing_email_returns_error_code(self):
        signup_url = reverse("signup")
        data = {"password": "aZvD1234D", "first_name": "Tester"}
        signup_response = self.client.post(signup_url, data, format="json")
        self.assertEqual(signup_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(signup_response.json()["email"][0], "error_email_is_a_required_field")

    def test_signup_password_too_short(self):
        response = self.post(
            reverse("signup"),
            data={
                "email": "test@test.com",
                "password": "123zxc56",
                "first_name": "Tester",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["password"][0], "error_password_too_short")

    def test_signup_password_entirely_numeric(self):
        response = self.post(
            reverse("signup"),
            data={
                "email": "test@test.com",
                "password": "1236549878",
                "first_name": "Tester",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["password"][0], "error_password_entirely_numeric")

    def test_signup_password_too_common(self):
        response = self.post(
            reverse("signup"),
            data={
                "email": "test@test.com",
                "password": "password123",
                "first_name": "Tester",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["password"][0], "error_password_too_common")

    def test_signup_password_too_similar_to_the_email(self):
        response = self.post(
            reverse("signup"),
            data={
                "email": "test@test.com",
                "password": "test@test.com",
                "first_name": "Tester",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["password"][0], "error_password_too_similar_to_email")

    def test_redirect_to_app_on_reset_password_get_action(self):
        reset_key = self.user.create_new_password_token()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "reset password")
        self.assertEqual(mail.outbox[0].to, ["test@test.lt"])
        self.assertIn(
            f"/api/users/redirect-to-app/reset-password/{reset_key}/",
            mail.outbox[0].body,
        )

        response = self.client.get(reverse("redirect-to-app-with-uuid", args=["reset-password", reset_key]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        app_url = f"systemakvile://reset-password/{reset_key}"
        self.assertIn(f'window.location.replace("{app_url}")', response.content.decode())

    def test_redirect_to_app_on_verify_user_get_action(self):
        self.user.is_verified = False
        self.user.unverified_email = self.user.email
        self.user.save()

        activation_key = self.user.create_activation_key()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "create account")
        self.assertEqual(mail.outbox[0].to, ["test@test.lt"])
        self.assertIn(
            f"/api/users/redirect-to-app/verify-email/{activation_key}/",
            mail.outbox[0].body,
        )

        response = self.client.get(reverse("redirect-to-app-with-uuid", args=["verify-email", activation_key]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        app_url = f"systemakvile://verify-email/{activation_key}"
        self.assertIn(f'window.location.replace("{app_url}")', response.content.decode())

    def test_update_user_endpoint(self):
        self.query_limits["ANY PUT REQUEST"] = 6
        data = {
            "first_name": "New",
            "geolocation": "Seattle, Washington, USA",
            "device": "NOKIA 3310",
            "operating_system": "Android 10",
        }
        response = self.put(reverse("user"), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["first_name"], data["first_name"])
        self.user.refresh_from_db()
        self.assertEqual(data["first_name"], self.user.first_name)
        self.assertEqual(data["geolocation"], self.user.geolocation)
        self.assertEqual(data["device"], self.user.device)
        self.assertEqual(data["operating_system"], self.user.operating_system)

    def test_partial_update_user_endpoint(self):
        self.query_limits["ANY PATCH REQUEST"] = 6
        data = {
            "first_name": "New",
            "geolocation": "Seattle, Washington, USA",
            "device": "NOKIA 3310",
            "operating_system": "Android 10",
        }
        response = self.patch(reverse("user"), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["first_name"], data["first_name"])
        self.user.refresh_from_db()
        self.assertEqual(data["first_name"], self.user.first_name)
        self.assertEqual(data["geolocation"], self.user.geolocation)
        self.assertEqual(data["device"], self.user.device)
        self.assertEqual(data["operating_system"], self.user.operating_system)

    def test_update_user_endpoint_does_not_change_email(self):
        self.query_limits["ANY PUT REQUEST"] = 6
        data = {"first_name": "New", "email": "new@new.com"}
        response = self.put(reverse("user"), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.json()["email"], data["email"])
        self.user.refresh_from_db()
        self.assertNotEqual(data["email"], self.user.email)

    def test_deactivate_user(self):
        patcher_get_subject = patch("apps.routines.signals.get_subject_id")
        mock_haut_ai_get_subject_id = patcher_get_subject.start()
        mock_haut_ai_get_subject_id.return_value = "12312"
        self.addCleanup(patcher_get_subject.stop)

        patcher_upload_picture = patch("apps.routines.signals.upload_picture")
        mock_haut_ai_get_subject_id_upload_picture = patcher_upload_picture.start()
        mock_haut_ai_get_subject_id_upload_picture.return_value = ("123", "123")
        self.addCleanup(patcher_upload_picture.stop)

        patcher_get_auth_info = patch("apps.routines.signals.get_auth_info")
        mock_haut_ai_get_auth_info = patcher_get_auth_info.start()
        mock_haut_ai_get_auth_info.return_value = ("1234", "4321")
        self.addCleanup(patcher_get_auth_info.stop)

        self.query_limits["ANY DELETE REQUEST"] = 9
        self.user.avatar = "random.jpg"
        self.user.save()
        make(UserSocialAuth, user=self.user, _quantity=3)
        make(ActivationKey, user=self.user, _quantity=3)
        make(Order, user=self.user, _quantity=3)
        make(
            FaceScan,
            user=self.user,
            image=SimpleUploadedFile("icon.png", b"file_content"),
            _quantity=3,
        )

        url = reverse("deactivate")
        response = self.delete(url)
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.user.avatar, "")
        self.assertEqual(self.user.first_name, settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD)
        self.assertEqual(self.user.last_name, settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD)
        self.assertIn(settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD, self.user.email)
        self.assertEqual(self.user.is_active, False)
        self.assertEqual(self.user.is_verified, False)
        for order in self.user.orders.all():
            self.assertEqual(order.shopify_order_id, settings.DEACTIVATED_USER_SENSITIVE_DATA_FIELD)
        for face_scan in self.user.face_scans.all():
            self.assertEqual(face_scan.image, "")
        self.assertEqual(ActivationKey.objects.filter(user=self.user).first(), None)
        self.assertEqual(UserSocialAuth.objects.filter(user=self.user).first(), None)


class AuthenticationIntegrationTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # create verification template, language and translation
        site_config = SiteConfiguration.get_solo()

        template_name = "verify_email_template"
        template = EmailTemplate.objects.create(name=template_name)
        language = Language.objects.get(code="en", name="English")
        subject = "Subject"
        content = "{{ link_verify_email }}"
        make(
            EmailTemplateTranslation,
            language=language,
            template=template,
            subject=subject,
            content=content,
        )

        setattr(site_config, template_name, template)
        site_config.enabled_languages.add(language)
        site_config.save()

    def test_user_signup_flow(self):
        self.query_limits["ANY POST REQUEST"] = 11

        terms_of_service = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.TERMS_OF_SERVICE.value)
        privacy_policy = make(AboutAndNoticeSection, type=AboutAndNoticeSectionType.PRIVACY_POLICY.value)

        signup_url = reverse("signup")
        login_url = reverse("login")
        data = {
            "email": "test@test.com",
            "password": "321pSs1234",
            "first_name": "Tester",
            "terms_of_service": terms_of_service.id,
            "privacy_policy": privacy_policy.id,
        }

        # signup the new user and check if verification email is sent
        signup_response = self.client.post(signup_url, data, format="json")
        self.assertEqual(signup_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(signup_response.json()["first_name"], "Tester")
        self.assertEqual(signup_response.json()["email"], "test@test.com")
        self.assertEqual(len(mail.outbox), 1)

        # this first try to login should fail because the user is not verified
        login_response = self.client.post(login_url, data, format="json")
        self.assertEqual(login_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            login_response.data["non_field_errors"][0],
            "error_login_user_email_not_verified",
        )

        # verify user
        user = User.objects.filter(email=data["email"]).first()
        activation_key = ActivationKey.objects.get(user=user).activation_key
        self.client.put(reverse("verify", args=[activation_key]))

        # second try to login should work because user is now verified
        login_response2 = self.client.post(login_url, data, format="json")
        self.assertEqual(login_response2.status_code, status.HTTP_201_CREATED, login_response2.json())
        self.assertTrue(login_response2.json()["token"])


class SocialLoginTestCase(BaseTestCase):
    def setUp(self):
        session = self.client.session
        session["facebook_state"] = "1"
        session["google-oauth2_state"] = "1"
        session["apple-id_state"] = "1"
        session.save()
        self.email = "test@yahoo.com"

    def _assert_response(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        # check token valid
        jwt_auth = JWTAuthentication()
        token_instance = jwt_auth.get_validated_token(response.data["token"])
        self.assertEqual(token_instance["token_type"], "access")
        self.assertIn("datetime_claim", token_instance)

    def _assert_user_and_user_social_auth(self, user):
        self.assertTrue(user)
        user_social_auth = UserSocialAuth.objects.filter(user=user)
        self.assertEqual(len(user_social_auth), 1)

    @patch("django.contrib.sessions.backends.base.SessionBase.set_expiry")
    @patch("social_core.backends.base.BaseAuth.request")
    def test_facebook_login(self, mock_request, mock_session_expiry):
        data = {"access_token": "123", "email": self.email, "fullname": "Brown John"}
        mock_request.return_value.json.return_value = data
        mock_session_expiry.side_effect = [OverflowError, None]
        response = self.client.post(
            reverse("login_social_jwt_pair"),
            {"provider": FacebookOAuth2.name, "code": "okDwqxMmF3cQ8ybRz7JlAaf4"},
            **self.headers,
        )
        self._assert_response(response)
        user = User.objects.filter(email=self.email).first()
        self._assert_user_and_user_social_auth(user)

    @patch("django.contrib.sessions.backends.base.SessionBase.set_expiry")
    @patch("social_core.backends.base.BaseAuth.request")
    def test_facebook_login_error_missing_permission_to_retrieve_email(self, mock_request, mock_session_expiry):
        data = {"access_token": "123", "fullname": "Brown John"}
        mock_request.return_value.json.return_value = data
        mock_session_expiry.side_effect = [OverflowError, None]
        creation_timestamp = timezone.now()
        response = self.client.post(
            reverse("login_social_jwt_pair"),
            {"provider": FacebookOAuth2.name, "code": "okDwqxMmF3cQ8ybRz7JlAaf4"},
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), ["error_missing_permission_to_retrieve_email"])
        self.assertFalse(User.objects.filter(date_joined__gte=creation_timestamp).exists())

    @patch("django.contrib.sessions.backends.base.SessionBase.set_expiry")
    @patch("social_core.backends.base.BaseAuth.request")
    def test_google_login(self, mock_request, mock_session_expiry):
        data = {
            "access_token": "123",
            "email": self.email,
            "first_name": "John",
            "last_name": "Brown",
        }
        mock_request.return_value.json.return_value = data
        mock_session_expiry.side_effect = [OverflowError, None]
        response = self.client.post(
            reverse("login_social_jwt_pair"),
            {"provider": GoogleOAuth2.name, "code": "okDwqxMmF3cQ8ybRz7JlAaf4"},
            **self.headers,
        )
        self._assert_response(response)
        user = User.objects.filter(email=self.email).first()
        self._assert_user_and_user_social_auth(user)

    @patch.object(AppleIdAuth, "decode_id_token")
    @patch.object(BaseOAuth2, "request_access_token")
    @patch.object(BaseOAuth2, "auth_complete_params")
    def test_apple_web_login(self, mock_auth_complete_params, mock_request_access_token, mock_decode_id_token):
        data = {
            "access_token": "gCu5T2DhnGXViQErTuMtrhlX_CD-5jh7GPPgcwZIG6Zq5FhuXqIwg",
            AppleIdAuth.ID_KEY: "dflindslf",
            "email": self.email,
        }
        mock_auth_complete_params.return_value.json.return_value = data
        mock_request_access_token.return_value = data
        mock_decode_id_token.return_value = data
        response = self.client.post(
            reverse("login_social_jwt_pair"),
            {
                "provider": AppleIdAuth.name,
                "code": "3D52VoM1uiw94a1ETnGvYlCw",
                "client_type": SocialClient.WEB.value,
            },
            **self.headers,
        )
        self._assert_response(response)

        user = User.objects.filter(email=self.email).first()
        self._assert_user_and_user_social_auth(user)


class UserQuestionnaireTestCase(BaseTestCase):
    def test_user_does_not_have_questionnaire(self):
        self.assertFalse(self.user.is_questionnaire_finished)

    def test_user_has_not_finished_filling_the_questionnaire(self):
        make(UserQuestionnaire, user=self.user)
        self.assertTrue(self.user.is_questionnaire_finished)


class UserSettingsTest(BaseTestCase):
    def test_default_user_settings(self):
        user_settings = make(UserSettings, user=self.user)
        self.assertFalse(user_settings.is_face_scan_reminder_active)
        self.assertFalse(user_settings.is_daily_questionnaire_reminder_active)

    def test_creating_duplicate_user_settings(self):
        make(UserSettings, user=self.user)
        with self.assertRaises(IntegrityError):
            make(UserSettings, user=self.user)

    def test_create_user_settings(self):
        url = reverse("user-settings-user-settings")
        data = {
            "is_face_scan_reminder_active": True,
            "is_daily_questionnaire_reminder_active": True,
        }
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_settings = response.json()
        self.assertTrue(user_settings["is_face_scan_reminder_active"])
        self.assertTrue(user_settings["is_daily_questionnaire_reminder_active"])

    def test_get_non_existing_user_settings(self):
        url = reverse("user-settings-user-settings")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_user_settings(self):
        user_settings = make(
            UserSettings,
            user=self.user,
            is_face_scan_reminder_active=True,
            is_daily_questionnaire_reminder_active=True,
        )
        url = reverse("user-settings-user-settings")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fetched_user_settings = response.json()
        self.assertEqual(
            fetched_user_settings["is_face_scan_reminder_active"],
            user_settings.is_face_scan_reminder_active,
        )
        self.assertEqual(
            fetched_user_settings["is_daily_questionnaire_reminder_active"],
            user_settings.is_daily_questionnaire_reminder_active,
        )

    def test_update_user_settings(self):
        user_settings = make(
            UserSettings,
            user=self.user,
            is_face_scan_reminder_active=False,
            is_daily_questionnaire_reminder_active=True,
        )
        self.assertFalse(user_settings.is_face_scan_reminder_active)
        self.assertTrue(user_settings.is_daily_questionnaire_reminder_active)

        url = reverse("user-settings-user-settings")
        data = {
            "is_face_scan_reminder_active": True,
            "is_daily_questionnaire_reminder_active": True,
        }
        response = self.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fetched_user_settings = response.json()
        user_settings.refresh_from_db()
        self.assertEqual(
            fetched_user_settings["is_face_scan_reminder_active"],
            user_settings.is_face_scan_reminder_active,
        )
        self.assertEqual(
            fetched_user_settings["is_daily_questionnaire_reminder_active"],
            user_settings.is_daily_questionnaire_reminder_active,
        )

    def test_partial_update_user_settings(self):
        user_settings = make(
            UserSettings,
            user=self.user,
            is_face_scan_reminder_active=True,
            is_daily_questionnaire_reminder_active=True,
        )
        self.assertTrue(user_settings.is_face_scan_reminder_active)
        self.assertTrue(user_settings.is_daily_questionnaire_reminder_active)

        url = reverse("user-settings-user-settings")
        data = {"is_face_scan_reminder_active": False}
        response = self.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fetched_user_settings = response.json()
        user_settings.refresh_from_db()
        self.assertEqual(
            fetched_user_settings["is_face_scan_reminder_active"],
            user_settings.is_face_scan_reminder_active,
        )
        self.assertEqual(
            fetched_user_settings["is_daily_questionnaire_reminder_active"],
            user_settings.is_daily_questionnaire_reminder_active,
        )

    def test_delete_user_settings(self):
        make(
            UserSettings,
            user=self.user,
            is_face_scan_reminder_active=True,
            is_daily_questionnaire_reminder_active=True,
        )
        url = reverse("user-settings-user-settings")
        response = self.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_non_existing_user_settings(self):
        url = reverse("user-settings-user-settings")
        response = self.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
