import itertools
from urllib.parse import urlencode

from django.urls import reverse
from model_bakery.baker import make
from rest_framework import status

from apps.routines.models import UserTag
from apps.utils.error_codes import Errors
from apps.utils.tests_utils import BaseTestCase


class UserTagTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.predefined_tags = make(UserTag, user=None, _quantity=3, category="NUTRITION")

    def test_predefined_tag_list_only(self):
        url = reverse("tags-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tags = response.json()["results"]
        self.assertEqual(len(tags), 3)
        for pre_tag, tag in zip(self.predefined_tags[::-1], tags):
            self.assertEqual(pre_tag.id, tag["id"])
            self.assertEqual(pre_tag.name, tag["name"])
            self.assertEqual(pre_tag.slug, tag["slug"])
            self.assertEqual(pre_tag.category, tag["category"])
            self.assertIsNone(pre_tag.user)
            self.assertTrue(tag["is_predefined"])

    def test_delete_predefined_tags_by_any_user(self):
        url = reverse("tags-detail", args=[self.predefined_tags[0].id])
        response = self.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_predefined_tags_by_any_user(self):
        url = reverse("tags-detail", args=[self.predefined_tags[0].id])
        data = {"name": "Updated UserTag", "category": "NUTRITION"}
        response = self.put(url, data=data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_predefined_tag_for_any_user(self):
        url = reverse("tags-detail", args=[self.predefined_tags[0].id])
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag = response.json()
        self.assertEqual(self.predefined_tags[0].id, tag["id"])
        self.assertEqual(self.predefined_tags[0].name, tag["name"])
        self.assertEqual(self.predefined_tags[0].slug, tag["slug"])
        self.assertEqual(self.predefined_tags[0].category, tag["category"])
        self.assertTrue(tag["is_predefined"])
        self.assertIsNone(self.predefined_tags[0].user)

    def test_tag_list_for_any_user(self):
        user_defined_tags = make(UserTag, user=self.user, _quantity=3)
        all_tags = list(itertools.chain(self.predefined_tags, user_defined_tags))
        all_tags.reverse()
        url = reverse("tags-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tags = response.json()["results"]
        self.assertEqual(len(tags), 6)
        for pre_tag, tag in zip(all_tags, tags):
            self.assertEqual(pre_tag.id, tag["id"])
            self.assertEqual(pre_tag.name, tag["name"])
            self.assertEqual(pre_tag.slug, tag["slug"])
            self.assertEqual(pre_tag.category, tag["category"])
            if pre_tag.user is None:
                self.assertTrue(tag["is_predefined"])
            else:
                self.assertFalse(tag["is_predefined"])

    def test_create_user_defined_tag(self):
        url = reverse("tags-list")
        data = {"name": "User Defined UserTag1", "category": "NUTRITION"}
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tag = UserTag.objects.filter(user=self.user).first()
        res_tag = response.json()
        self.assertEqual(tag.id, res_tag["id"])
        self.assertEqual(tag.name, res_tag["name"])
        self.assertEqual(tag.slug, res_tag["slug"])
        self.assertEqual(tag.category, res_tag["category"])
        self.assertFalse(res_tag["is_predefined"])

    def test_update_user_defined_tag(self):
        tag = make(UserTag, user=self.user)
        url = reverse("tags-detail", args=[tag.id])
        data = {"name": "User Defined UserTag1", "category": "NUTRITION"}
        response = self.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        res_tag = response.json()
        self.assertEqual(tag.id, res_tag["id"])
        self.assertEqual(tag.name, res_tag["name"])
        self.assertEqual(tag.slug, res_tag["slug"])
        self.assertEqual(tag.category, res_tag["category"])
        self.assertIsNotNone(tag.user)
        self.assertFalse(res_tag["is_predefined"])

    def test_partial_update_user_defined_tag(self):
        tag = make(UserTag, user=self.user, category="WELL_BEING")
        url = reverse("tags-detail", args=[tag.id])
        data = {"category": "NUTRITION"}
        response = self.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        res_tag = response.json()
        self.assertEqual(tag.id, res_tag["id"])
        self.assertEqual(tag.name, res_tag["name"])
        self.assertEqual(tag.slug, res_tag["slug"])
        self.assertEqual(tag.category, res_tag["category"])
        self.assertIsNotNone(tag.user)
        self.assertFalse(res_tag["is_predefined"])

    def test_detail_user_defined_tag_by_any_user(self):
        tag = make(UserTag, user=self.user)
        url = reverse("tags-detail", args=[tag.id])
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_tag = response.json()
        self.assertEqual(tag.id, res_tag["id"])
        self.assertEqual(tag.name, res_tag["name"])
        self.assertEqual(tag.slug, res_tag["slug"])
        self.assertEqual(tag.category, res_tag["category"])
        self.assertIsNotNone(tag.user)
        self.assertFalse(res_tag["is_predefined"])

    def test_delete_user_defined_tag_by_any_user(self):
        self.query_limits["ANY DELETE REQUEST"] = 7
        tag = make(UserTag, user=self.user)
        url = reverse("tags-detail", args=[tag.id])
        response = self.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(UserTag.objects.filter(user=self.user).first())

    def test_create_duplicate_tags_for_same_category(self):
        name = "Sample UserTag1"
        make(UserTag, user=self.user, name=name, category="NUTRITION")
        data = {"name": name, "category": "NUTRITION"}
        url = reverse("tags-list")
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["name"][0], Errors.TAG_NAME_ALREADY_EXISTS_FOR_SAME_CATEGORY)

    def test_create_same_tag_name_for_different_category(self):
        name = "Sample UserTag1"
        url = reverse("tags-list")
        first_tag = make(UserTag, user=self.user, name=name, category="NUTRITION")
        data = {"name": "User Defined UserTag1", "category": "WELL_BEING"}
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tag = UserTag.objects.filter(user=self.user, category=data["category"]).first()
        res_tag = response.json()
        self.assertEqual(tag.id, res_tag["id"])
        self.assertEqual(tag.name, res_tag["name"])
        self.assertEqual(tag.slug, res_tag["slug"])
        self.assertEqual(tag.category, res_tag["category"])
        self.assertEqual(tag.user, self.user)
        self.assertFalse(res_tag["is_predefined"])
        self.assertNotEqual(first_tag.category, res_tag["category"])
        self.assertNotEqual(first_tag.name, res_tag["name"])
        self.assertNotEqual(first_tag.slug, res_tag["slug"])

    def test_filtering_tags_with_category(self):
        nutrition_tags = make(UserTag, user=self.user, category="NUTRITION", _quantity=3)
        url = reverse("tags-list")
        query_params = {"category": "NUTRITION"}
        response = self.get(f"{url}?{urlencode(query_params)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tags = response.json()["results"]
        self.assertEqual(len(tags), 6)
        all_tags = list(itertools.chain(self.predefined_tags, nutrition_tags))
        all_tags.reverse()
        for pre_tag, tag in zip(all_tags, tags):
            self.assertEqual(pre_tag.id, tag["id"])
            self.assertEqual(pre_tag.name, tag["name"])
            self.assertEqual(pre_tag.slug, tag["slug"])
            self.assertEqual(pre_tag.category, tag["category"])
            self.assertEqual(pre_tag.category, "NUTRITION")

        query_params1 = {"category": "WELL_BEING"}
        response1 = self.get(f"{url}?{urlencode(query_params1)}")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        tags_from_response1 = response1.json()["results"]
        self.assertEqual(len(tags_from_response1), 0)

    def test_create_tags_with_invalid_category(self):
        name = "Sample UserTag1"
        data = {"name": name, "category": "INVALID_CATEGORY"}
        url = reverse("tags-list")
        response = self.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["category"][0], '"INVALID_CATEGORY" is not a valid choice.')
