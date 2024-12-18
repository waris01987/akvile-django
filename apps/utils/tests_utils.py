import logging
from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse
from model_bakery import generators

from apps.translations.models import Language
from apps.users.models import User
from apps.utils.tests_query_counter import APIClientWithQueryCounter
from apps.utils.token import get_token


class BaseTestCase(TestCase):
    email = "test@test.lt"
    password = "aZvD1234D"
    credentials = {"email": email, "password": password}
    user_data = {
        "email": email,
        "password": password,
        "first_name": "First",
        "last_name": "Last",
    }
    auth_url = reverse("login")
    headers = {"HTTP_User-Agent": "Python"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        generators.add("ckeditor.fields.RichTextField", generators.random_gen.gen_text)

    def setUp(self):
        self.query_limits = {}
        logging.disable(logging.INFO)
        self.language = Language.objects.get_or_create(code="en", defaults={"name": "English"})[0]
        self.user = User.objects.create_user(**self.user_data)
        self.user.is_verified = True
        self.user.language = self.language
        self.user.save()
        self.client = APIClientWithQueryCounter(test_case=self, headers=self.headers)

        # Default query_limits for all project:
        self.query_limits["ANY GET REQUEST"] = 5
        self.query_limits["ANY POST REQUEST"] = 5
        self.query_limits["ANY PUT REQUEST"] = 5
        self.query_limits["ANY PATCH REQUEST"] = 5
        self.query_limits["ANY DELETE REQUEST"] = 5

    def tearDown(self):
        logging.disable(logging.NOTSET)
        super(BaseTestCase, self).tearDown()

    def authorize(self, user: User = None) -> APIClientWithQueryCounter:
        if not user:
            user = self.user
        refresh = get_token(user)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + str(refresh.access_token))  # type: ignore
        return self.client  # type: ignore

    def get(self, path: str, query_params: dict = None, *args, **kwargs):
        if query_params:
            path += f"?{urlencode(query_params)}"
        return self.authorize().get(path=path, *args, **kwargs)

    def post(self, path: str, data: dict = None, format: str = "json", *args, **kwargs):
        return self.authorize().post(path=path, data=data, format=format, *args, **kwargs)

    def put(self, path: str, data: dict = None, format: str = "json", *args, **kwargs):
        return self.authorize().put(path=path, data=data, format=format, *args, **kwargs)

    def patch(self, path: str, data: dict = None, format: str = "json", *args, **kwargs):
        return self.authorize().patch(path=path, data=data, format=format, *args, **kwargs)

    def delete(self, path: str, data: dict = None, format: str = "json", *args, **kwargs):
        return self.authorize().delete(path=path, data=data, format=format, *args, **kwargs)
