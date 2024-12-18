from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from model_bakery.baker import make
from rest_framework import status

from apps.home.models import EmailTemplate, EmailTemplateTranslation, SiteConfiguration
from apps.translations.models import Language
from apps.users.models import User, PasswordKey, ActivationKey
from apps.utils.tasks import send_email_task
from apps.utils.tests_utils import BaseTestCase


@override_settings(DEFAULT_LANGUAGE="en")
class SendEmailTestCase(TestCase):
    def _add_email_template_and_translation(
        self,
        site_config: SiteConfiguration,
        template_name: str,
        language: Language,
        dynamic_content_fragment: str,
    ) -> None:
        template, _create = EmailTemplate.objects.get_or_create(name=template_name)
        setattr(site_config, template_name, template)
        subject = "Subject"
        content = f"Follow this link: {{{{ {dynamic_content_fragment} }}}}"
        make(
            EmailTemplateTranslation,
            language=language,
            template=template,
            subject=subject,
            content=content,
        )

    def setUp(self):
        site_config = SiteConfiguration.get_solo()
        language, _create = Language.objects.get_or_create(code="en", name="English")
        site_config.enabled_languages.add(language)

        self._add_email_template_and_translation(site_config, "password_renewal_template", language, "passwordUrl")
        self._add_email_template_and_translation(site_config, "verify_email_template", language, "activationUrl")

        self.email = "test@example.com"
        self.user = make(User, email=self.email, language=language)
        site_config.save()

    def test_send_email_task(self):
        password_url = "http://example.com/api/reset"  # noqa: S105
        send_email_task(
            email=self.email,
            template="password_renewal_template",
            context={"passwordUrl": password_url},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.email])
        self.assertEqual(mail.outbox[0].subject, "Subject")
        self.assertIn(password_url, mail.outbox[0].body)

    def test_send_email_task_with_cc_and_bcc(self):
        cc = ["test1@example.com", "test2@example.com"]
        bcc = ["test3@example.com"]

        password_url = "http://example.com/api/reset"  # noqa: S105
        send_email_task(
            email=self.email,
            cc=cc,
            bcc=bcc,
            template="password_renewal_template",
            context={"passwordUrl": password_url},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.email])
        self.assertEqual(mail.outbox[0].cc, cc)
        self.assertEqual(mail.outbox[0].bcc, bcc)
        self.assertEqual(mail.outbox[0].subject, "Subject")
        self.assertIn(password_url, mail.outbox[0].body)

    def test_resend_verification_email(self):
        data = {"email": self.email}
        url = reverse("resend-verification")

        response = self.client.post(url, data=data, format="json", **BaseTestCase.headers)
        activation_key = ActivationKey.objects.get(user=self.user).activation_key
        activation_url = settings.VERIFICATION_BASE_URL.format(settings.APP_HOST, activation_key)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.email])
        self.assertEqual(mail.outbox[0].subject, "Subject")
        self.assertIn(activation_url, mail.outbox[0].body)

    def test_send_password_renewal_email(self):
        data = {"email": self.email}
        url = reverse("forgot")

        response = self.client.post(url, data=data, format="json", **BaseTestCase.headers)
        password_key = PasswordKey.objects.get(user=self.user).password_key
        password_url = settings.RESET_PASSWORD_BASE_URL.format(settings.APP_HOST, password_key)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.email])
        self.assertEqual(mail.outbox[0].subject, "Subject")
        self.assertIn(password_url, mail.outbox[0].body)
