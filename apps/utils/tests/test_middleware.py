from django.test import TestCase
from django.urls import reverse
from parameterized import parameterized
from rest_framework import status


class MiddlewareTestCase(TestCase):
    @parameterized.expand([[{}], [{"HTTP_User-Agent": ""}]])
    def test_middleware(self, headers):
        response = self.client.post(reverse("check-app-version"), data={"app_version": "0"}, **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.content, b"Access denied.")
