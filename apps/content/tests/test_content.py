import datetime

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.urls import reverse
from model_bakery.baker import make
from parameterized import parameterized
from rest_framework import status

from apps.content import CategoryName, LifeStyleCategories, SubCategoryName
from apps.content.models import (
    Article,
    ArticleTranslation,
    Category,
    CategoryTranslation,
    Period,
    PeriodTranslation,
    SubCategory,
    SubCategoryTranslation,
    UserArticle,
)
from apps.utils.tests_utils import BaseTestCase


class ContentTests(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.period_1 = make(Period, unlocks_after_week=0, ordering=1)
        self.period_1.image.name = "random_period_img_1.jpg"
        self.period_1.period_number_image.name = "random_period_number_img_1.jpg"
        self.period_1.save()

        self.period_2 = make(Period, unlocks_after_week=1, ordering=2)
        self.period_2.image.name = "random_period_img_2.jpg"
        self.period_2.period_number_image.name = "random_period_number_img_2.jpg"
        self.period_2.save()

        self.category = make(Category, name=CategoryName.CORE_PROGRAM.value)
        self.category.image.name = "random_category_img_1.jpg"
        self.category.save()
        self.category_translation = make(
            CategoryTranslation,
            language=self.language,
            title="category_translation_1",
            category=self.category,
        )
        self.article_1 = make(
            Article,
            name="article_1",
            category=self.category,
            period=self.period_2,
            is_published=True,
        )
        self.article_1.thumbnail.name = "random_article_thumbnail_1.jpg"
        self.article_1.video.name = "random_video_img_1.jpg"
        self.article_1.article_image.name = "random_article_img_1.jpg"
        self.article_1.save()
        self.article_translation_1 = make(ArticleTranslation, article=self.article_1)

        self.article_2 = make(
            Article,
            name="article_2",
            category=self.category,
            period=self.period_1,
            is_published=True,
        )
        self.article_2.thumbnail.name = "random_article_thumbnail_2.jpg"
        self.article_2.video.name = "random_video_img_2.jpg"
        self.article_2.article_image.name = "random_article_img_2.jpg"
        self.article_2.save()
        self.article_translation_2 = make(ArticleTranslation, article=self.article_2)

        self.period_translation_1 = make(
            PeriodTranslation,
            language=self.language,
            title="period_translation_1",
            period=self.period_1,
        )
        self.period_translation_2 = make(
            PeriodTranslation,
            language=self.language,
            title="period_translation_2",
            period=self.period_2,
        )

        self.initial_category = make(Category, name=CategoryName.INITIAL.value)
        self.intro_article = make(
            Article,
            name="intro_article",
            category=self.initial_category,
            is_published=True,
        )

        self.query_limits["ANY GET REQUEST"] = 11
        self.query_limits["ANY POST REQUEST"] = 8

    def test_articles_list(self):
        url = reverse("articles-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.article_1.id)
        self.assertEqual(response.json()["results"][0]["title"], self.article_translation_1.title)
        self.assertEqual(
            response.json()["results"][0]["subtitle"],
            self.article_translation_1.subtitle,
        )
        self.assertEqual(
            response.json()["results"][0]["headline"],
            self.article_translation_1.headline,
        )
        self.assertEqual(
            response.json()["results"][0]["sub_headline"],
            self.article_translation_1.sub_headline,
        )
        self.assertEqual(
            response.json()["results"][0]["description"],
            self.article_translation_1.description,
        )
        self.assertEqual(
            response.json()["results"][0]["main_text"],
            self.article_translation_1.main_text,
        )
        self.assertEqual(
            response.json()["results"][0]["created_at"],
            self.article_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][0]["name"], self.article_1.name)
        self.assertEqual(response.json()["results"][0]["content_type"], self.article_1.content_type)
        self.assertIn(self.article_1.thumbnail.url, response.json()["results"][0]["thumbnail"])
        self.assertIn(self.article_1.video.url, response.json()["results"][0]["video"])
        self.assertIn(
            self.article_1.article_image.url,
            response.json()["results"][0]["article_image"],
        )
        self.assertEqual(response.json()["results"][0]["category"], self.article_1.category.id)

        self.assertEqual(response.json()["results"][1]["id"], self.article_2.id)
        self.assertEqual(response.json()["results"][1]["title"], self.article_translation_2.title)
        self.assertEqual(
            response.json()["results"][1]["subtitle"],
            self.article_translation_2.subtitle,
        )
        self.assertEqual(
            response.json()["results"][1]["headline"],
            self.article_translation_2.headline,
        )
        self.assertEqual(
            response.json()["results"][1]["sub_headline"],
            self.article_translation_2.sub_headline,
        )
        self.assertEqual(
            response.json()["results"][1]["description"],
            self.article_translation_2.description,
        )
        self.assertEqual(
            response.json()["results"][1]["main_text"],
            self.article_translation_2.main_text,
        )
        self.assertEqual(
            response.json()["results"][1]["created_at"],
            self.article_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][1]["name"], self.article_2.name)
        self.assertEqual(response.json()["results"][1]["content_type"], self.article_2.content_type)
        self.assertIn(self.article_2.thumbnail.url, response.json()["results"][1]["thumbnail"])
        self.assertIn(
            self.article_2.video.url,
            response.json()["results"][1]["video"],
        )
        self.assertIn(
            self.article_2.article_image.url,
            response.json()["results"][1]["article_image"],
        )
        self.assertEqual(response.json()["results"][1]["category"], self.article_2.category.id)

    def test_articles_detail(self):
        url = reverse("articles-detail", kwargs={"pk": str(self.article_1.id)})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.article_1.id)
        self.assertEqual(response.json()["title"], self.article_translation_1.title)
        self.assertEqual(response.json()["subtitle"], self.article_translation_1.subtitle)
        self.assertEqual(response.json()["headline"], self.article_translation_1.headline)
        self.assertEqual(response.json()["sub_headline"], self.article_translation_1.sub_headline)
        self.assertEqual(response.json()["description"], self.article_translation_1.description)
        self.assertEqual(response.json()["main_text"], self.article_translation_1.main_text)
        self.assertEqual(
            response.json()["created_at"],
            self.article_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["name"], self.article_1.name)
        self.assertEqual(response.json()["content_type"], self.article_1.content_type)
        self.assertIn(self.article_1.thumbnail.url, response.json()["thumbnail"])
        self.assertIn(self.article_1.video.url, response.json()["video"])
        self.assertIn(self.article_1.article_image.url, response.json()["article_image"])
        self.assertEqual(response.json()["category"], self.article_1.category.id)

    def test_categories_list(self):
        Article.objects.all().delete()
        Category.objects.exclude(id__in=[self.category.id, self.initial_category.id]).delete()

        additional_category = make(Category, name=CategoryName.SKIN_SCHOOL.value)
        additional_category_translation = make(
            CategoryTranslation, language=self.language, category=additional_category
        )
        additional_category.image.name = "random_category_img_1.jpg"
        additional_category.save()

        url = reverse("categories-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.category.id)
        self.assertEqual(response.json()["results"][0]["title"], self.category_translation.title)
        self.assertEqual(
            response.json()["results"][0]["description"],
            self.category_translation.description,
        )
        self.assertEqual(
            response.json()["results"][0]["created_at"],
            self.category.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][0]["name"], self.category.name)
        self.assertIn(self.category.image.url, response.json()["results"][0]["image"])

        self.assertEqual(response.json()["results"][1]["id"], self.initial_category.id)
        self.assertEqual(response.json()["results"][1]["title"], self.initial_category.name)
        self.assertEqual(response.json()["results"][1]["description"], "")
        self.assertEqual(
            response.json()["results"][1]["created_at"],
            self.initial_category.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][1]["name"], self.initial_category.name)
        self.assertIsNone(response.json()["results"][1]["image"])

        self.assertEqual(response.json()["results"][2]["id"], additional_category.id)
        self.assertEqual(
            response.json()["results"][2]["title"],
            additional_category_translation.title,
        )
        self.assertEqual(
            response.json()["results"][2]["description"],
            additional_category_translation.description,
        )
        self.assertEqual(
            response.json()["results"][2]["created_at"],
            additional_category.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][2]["name"], additional_category.name)
        self.assertIn(additional_category.image.url, response.json()["results"][2]["image"])

    def test_categories_detail(self):
        url = reverse("categories-detail", kwargs={"pk": str(self.category.id)})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.category.id)
        self.assertEqual(response.json()["title"], self.category_translation.title)
        self.assertEqual(response.json()["description"], self.category_translation.description)
        self.assertEqual(
            response.json()["created_at"],
            self.category.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["name"], self.category.name)
        self.assertIn(self.category.image.url, response.json()["image"])

    def test_articles_list_filter_by_category(self):
        url = reverse("articles-list")
        query = f"?category={self.category.pk}"
        resp = self.get(url + query)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()["results"]), 2)
        self.assertEqual(resp.json()["results"][0]["id"], self.article_1.id)
        self.assertEqual(resp.json()["results"][1]["id"], self.article_2.id)

    def test_subcategories_list(self):
        SubCategory.objects.all().delete()

        nutrition_subcategory = make(SubCategory, name=SubCategoryName.RECIPE_NUTRITION.value)
        nutrition_subcategory_translation = make(
            SubCategoryTranslation,
            language=self.language,
            subcategory=nutrition_subcategory,
        )
        nutrition_subcategory.image.name = "nutrition_subcategory_img_1.jpg"
        nutrition_subcategory.save()

        snacks_subcategory = make(SubCategory, name=SubCategoryName.SNACKS.value)
        snacks_subcategory_translation = make(
            SubCategoryTranslation,
            language=self.language,
            subcategory=snacks_subcategory,
        )
        snacks_subcategory.image.name = "snacks_subcategory_img_1.jpg"
        snacks_subcategory.save()

        url = reverse("subcategories-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)
        self.assertEqual(response.json()["results"][0]["id"], nutrition_subcategory.id)
        self.assertEqual(
            response.json()["results"][0]["title"],
            nutrition_subcategory_translation.title,
        )
        self.assertEqual(
            response.json()["results"][0]["description"],
            nutrition_subcategory_translation.description,
        )
        self.assertEqual(
            response.json()["results"][0]["created_at"],
            nutrition_subcategory.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][0]["name"], nutrition_subcategory.name)
        self.assertIn(nutrition_subcategory.image.url, response.json()["results"][0]["image"])

        self.assertEqual(response.json()["results"][1]["id"], snacks_subcategory.id)
        self.assertEqual(response.json()["results"][1]["title"], snacks_subcategory_translation.title)
        self.assertEqual(
            response.json()["results"][1]["description"],
            snacks_subcategory_translation.description,
        )
        self.assertEqual(
            response.json()["results"][1]["created_at"],
            snacks_subcategory.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][1]["name"], snacks_subcategory.name)
        self.assertIn(snacks_subcategory.image.url, response.json()["results"][1]["image"])

    def test_subcategories_detail(self):
        nutrition_subcategory = make(SubCategory, name=SubCategoryName.RECIPE_NUTRITION.value)
        nutrition_subcategory_translation = make(
            SubCategoryTranslation,
            language=self.language,
            subcategory=nutrition_subcategory,
        )
        nutrition_subcategory.image.name = "nutrition_subcategory_img_1.jpg"
        nutrition_subcategory.save()
        url = reverse("subcategories-detail", kwargs={"pk": str(nutrition_subcategory.id)})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], nutrition_subcategory.id)
        self.assertEqual(response.json()["title"], nutrition_subcategory_translation.title)
        self.assertEqual(
            response.json()["description"],
            nutrition_subcategory_translation.description,
        )
        self.assertEqual(
            response.json()["created_at"],
            nutrition_subcategory.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["name"], nutrition_subcategory.name)
        self.assertIn(nutrition_subcategory.image.url, response.json()["image"])

    def test_articles_list_filter_by_subcategory(self):
        category = make(Category, name=CategoryName.RECIPES.value)
        subcategory_1 = make(SubCategory, name=SubCategoryName.RECIPE_NUTRITION.value)
        subcategory_2 = make(SubCategory, name=SubCategoryName.BREAKFAST.value)
        article1 = make(Article, category=category, subcategory=subcategory_1, is_published=True)
        make(Article, category=category, subcategory=subcategory_2, is_published=True)
        url = reverse("articles-list")
        query = f"?subcategory={subcategory_1.pk}"
        resp = self.get(url + query)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()["results"]), 1)
        self.assertEqual(resp.json()["results"][0]["id"], article1.id)
        self.assertEqual(resp.json()["results"][0]["category"], category.id)
        self.assertEqual(resp.json()["results"][0]["subcategory"], subcategory_1.id)

    def test_article_is_read(self):
        user_article_1 = UserArticle.objects.get(article=self.article_1, user=self.user)
        user_article_1.is_read = True
        user_article_1.save()
        user_article_2 = UserArticle.objects.get(article=self.article_2, user=self.user)
        user_article_2.is_read = False
        user_article_2.save()

        url = reverse("articles-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.json()["results"][0]["id"], self.article_1.id)
        self.assertEqual(response.json()["results"][0]["is_read"], True)

        self.assertEqual(response.json()["results"][1]["id"], self.article_2.id)
        self.assertEqual(response.json()["results"][1]["is_read"], False)

    def test_mark_article_is_read(self):
        user_article_1 = UserArticle.objects.get(article=self.article_1, user=self.user)
        self.assertEqual(user_article_1.is_read, False)
        url = reverse("articles-mark-as-read", kwargs={"pk": self.article_1.id})
        response = self.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        user_article_1.refresh_from_db()
        self.assertEqual(user_article_1.is_read, True)
        self.assertIsNotNone(user_article_1.read_at)

    def test_mark_article_is_read_when_there_is_no_intermediary_model_istance(self):
        new_article = make(Article, name="new_article", is_published=True)

        url = reverse("articles-mark-as-read", kwargs={"pk": new_article.id})
        response = self.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        new_user_article = UserArticle.objects.get(article=new_article, user=self.user)
        self.assertEqual(new_user_article.is_read, True)
        self.assertIsNotNone(new_user_article.read_at)

    def test_article_is_not_read_when_there_is_no_intermediary_model_istance(self):
        new_article = make(Article, name="new_article", is_published=True)

        url = reverse("articles-detail", kwargs={"pk": new_article.id})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], new_article.id)
        self.assertEqual(response.json()["is_read"], False)

    def test_periods_list_old(self):
        url = reverse("periods-old-list")
        response = self.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.period_1.id)
        self.assertEqual(response.json()["results"][0]["title"], self.period_translation_1.title)
        self.assertEqual(
            response.json()["results"][0]["description"],
            self.period_translation_1.description,
        )
        self.assertEqual(
            response.json()["results"][0]["created_at"],
            self.period_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][0]["name"], self.period_1.name)
        self.assertEqual(response.json()["results"][0]["ordering"], self.period_1.ordering)
        self.assertEqual(response.json()["results"][0]["is_locked"], True)
        self.assertIn(self.period_1.image.url, response.json()["results"][0]["image"])
        self.assertIn(
            self.period_1.period_number_image.url,
            response.json()["results"][0]["period_number_image"],
        )

    def test_periods_list(self):
        self.query_limits["ANY GET REQUEST"] = 9
        make(
            Article,
            name="article_3",
            category=self.category,
            period=self.period_1,
            is_published=False,
        )
        make(
            Article,
            name="article_4",
            category=self.category,
            period=self.period_2,
            is_published=False,
        )
        url = reverse("periods-list")
        response = self.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.period_1.id)
        self.assertEqual(response.json()["results"][0]["title"], self.period_translation_1.title)
        self.assertEqual(
            response.json()["results"][0]["description"],
            self.period_translation_1.description,
        )
        self.assertEqual(
            response.json()["results"][0]["created_at"],
            self.period_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][0]["name"], self.period_1.name)
        self.assertEqual(response.json()["results"][0]["ordering"], self.period_1.ordering)
        self.assertEqual(response.json()["results"][0]["is_locked"], True)
        self.assertIn(self.period_1.image.url, response.json()["results"][0]["image"])
        self.assertIn(
            self.period_1.period_number_image.url,
            response.json()["results"][0]["period_number_image"],
        )

        result_1_articles = response.json()["results"][0]["articles"]
        self.assertEqual(len(result_1_articles), 1)
        self.assertEqual(result_1_articles[0]["id"], self.article_2.id)
        self.assertEqual(result_1_articles[0]["title"], self.article_translation_2.title)
        self.assertEqual(result_1_articles[0]["headline"], self.article_translation_2.headline)
        self.assertEqual(result_1_articles[0]["description"], self.article_translation_2.description)
        self.assertEqual(result_1_articles[0]["main_text"], self.article_translation_2.main_text)
        self.assertEqual(
            result_1_articles[0]["created_at"],
            self.article_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(result_1_articles[0]["name"], self.article_2.name)
        self.assertEqual(result_1_articles[0]["content_type"], self.article_2.content_type)
        self.assertIn(self.article_2.thumbnail.url, result_1_articles[0]["thumbnail"])
        self.assertIn(self.article_2.video.url, result_1_articles[0]["video"])
        self.assertEqual(result_1_articles[0]["category"], self.article_2.category.id)

        self.assertEqual(response.json()["results"][1]["id"], self.period_2.id)
        self.assertEqual(response.json()["results"][1]["title"], self.period_translation_2.title)
        self.assertEqual(
            response.json()["results"][1]["description"],
            self.period_translation_2.description,
        )
        self.assertEqual(
            response.json()["results"][1]["created_at"],
            self.period_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["results"][1]["name"], self.period_2.name)
        self.assertEqual(response.json()["results"][1]["ordering"], self.period_2.ordering)
        self.assertEqual(response.json()["results"][1]["is_locked"], True)
        self.assertIn(self.period_2.image.url, response.json()["results"][1]["image"])
        self.assertIn(
            self.period_2.period_number_image.url,
            response.json()["results"][1]["period_number_image"],
        )

        result_2_articles = response.json()["results"][1]["articles"]
        self.assertEqual(len(result_2_articles), 1)
        self.assertEqual(result_2_articles[0]["id"], self.article_1.id)
        self.assertEqual(result_2_articles[0]["title"], self.article_translation_1.title)
        self.assertEqual(result_2_articles[0]["headline"], self.article_translation_1.headline)
        self.assertEqual(result_2_articles[0]["description"], self.article_translation_1.description)
        self.assertEqual(result_2_articles[0]["main_text"], self.article_translation_1.main_text)
        self.assertEqual(
            result_2_articles[0]["created_at"],
            self.article_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(result_2_articles[0]["name"], self.article_1.name)
        self.assertEqual(result_2_articles[0]["content_type"], self.article_1.content_type)
        self.assertIn(self.article_1.thumbnail.url, result_2_articles[0]["thumbnail"])
        self.assertIn(self.article_1.video.url, result_2_articles[0]["video"])
        self.assertEqual(result_2_articles[0]["category"], self.article_1.category.id)

    def test_periods_detail(self):
        self.query_limits["ANY GET REQUEST"] = 9
        url = reverse("periods-detail", kwargs={"pk": str(self.period_2.id)})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.period_2.id)
        self.assertEqual(response.json()["title"], self.period_translation_2.title)
        self.assertEqual(response.json()["description"], self.period_translation_2.description)
        self.assertEqual(
            response.json()["created_at"],
            self.period_2.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["name"], self.period_2.name)
        self.assertEqual(response.json()["ordering"], self.period_2.ordering)
        self.assertEqual(response.json()["is_locked"], True)
        self.assertIn(self.period_2.image.url, response.json()["image"])
        self.assertIn(
            self.period_2.period_number_image.url,
            response.json()["period_number_image"],
        )

        self.assertEqual(response.json()["articles"][0]["id"], self.article_1.id)
        self.assertEqual(response.json()["articles"][0]["title"], self.article_translation_1.title)
        self.assertEqual(
            response.json()["articles"][0]["headline"],
            self.article_translation_1.headline,
        )
        self.assertEqual(
            response.json()["articles"][0]["description"],
            self.article_translation_1.description,
        )
        self.assertEqual(
            response.json()["articles"][0]["main_text"],
            self.article_translation_1.main_text,
        )
        self.assertEqual(
            response.json()["articles"][0]["created_at"],
            self.article_1.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(response.json()["articles"][0]["name"], self.article_1.name)
        self.assertEqual(response.json()["articles"][0]["content_type"], self.article_1.content_type)
        self.assertIn(self.article_1.thumbnail.url, response.json()["articles"][0]["thumbnail"])
        self.assertIn(self.article_1.video.url, response.json()["articles"][0]["video"])
        self.assertEqual(response.json()["articles"][0]["category"], self.article_1.category.id)

    def test_period_1_is_unlocked(self):
        self.query_limits["ANY GET REQUEST"] = 9
        intro_user_article = UserArticle.objects.filter(user=self.user, article=self.intro_article).first()
        intro_user_article.is_read = True
        intro_user_article.read_at = datetime.datetime.now(datetime.timezone.utc)
        intro_user_article.save()

        url = reverse("periods-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.json()["results"][0]["id"], self.period_1.id)
        self.assertEqual(response.json()["results"][0]["is_locked"], False)

        self.assertEqual(response.json()["results"][1]["id"], self.period_2.id)
        self.assertEqual(response.json()["results"][1]["is_locked"], True)

    def test_both_period_1_and_period_2_are_unlocked(self):
        self.query_limits["ANY GET REQUEST"] = 9
        intro_user_article = UserArticle.objects.filter(user=self.user, article=self.intro_article).first()
        intro_user_article.is_read = True
        intro_user_article.read_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(weeks=1)
        intro_user_article.save()

        url = reverse("periods-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.json()["results"][0]["id"], self.period_1.id)
        self.assertEqual(response.json()["results"][0]["is_locked"], False)

        self.assertEqual(response.json()["results"][1]["id"], self.period_2.id)
        self.assertEqual(response.json()["results"][1]["is_locked"], False)

    def test_article_ordering(self):
        self.article_1.ordering = 2
        self.article_1.save()
        self.article_2.ordering = 1
        self.article_2.save()

        url = reverse("articles-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.article_2.id)
        self.assertEqual(response.json()["results"][1]["id"], self.article_1.id)

    def test_percentage_of_articles_read(self):
        user_article_1 = UserArticle.objects.get(article=self.article_1, user=self.user)
        user_article_1.is_read = True
        user_article_1.save()

        make(Article, category=self.category, period=self.period_2, is_published=True)
        make(Article, category=self.category, period=self.period_2, is_published=True)
        make(Article, category=self.category, period=self.period_2, is_published=True)
        make(Article, category=self.category, period=self.period_2, is_published=True)

        all_published_articles = Article.objects.filter(is_published=True).count()

        percent_of_read_user_articles = round(1 / all_published_articles * 100)
        url = reverse("articles-progress")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["percent_of_read_articles"], percent_of_read_user_articles)

    def test_no_articles_read_percentage(self):
        make(Article, category=self.category, period=self.period_2, is_published=True)
        make(Article, category=self.category, period=self.period_2, is_published=True)
        make(Article, category=self.category, period=self.period_2, is_published=True)
        make(Article, category=self.category, period=self.period_2, is_published=True)

        url = reverse("articles-progress")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["percent_of_read_articles"], 0)

    def test_unpublished_article_not_counted_in_percentage_of_articles_read(self):
        user_article_1 = UserArticle.objects.get(article=self.article_1, user=self.user)
        user_article_1.is_read = True
        user_article_1.save()

        make(Article, category=self.category, period=self.period_2, is_published=False)
        make(Article, category=self.category, period=self.period_2, is_published=True)
        make(Article, category=self.category, period=self.period_2, is_published=True)
        make(Article, category=self.category, period=self.period_2, is_published=True)

        all_published_articles = Article.objects.filter(is_published=True).count()

        percent_of_read_user_articles = round(1 / all_published_articles * 100)
        url = reverse("articles-progress")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["percent_of_read_articles"], percent_of_read_user_articles)

    def test_other_category_articles_not_counted_in_percentage_of_articles_read(self):
        user_article_1 = UserArticle.objects.get(article=self.article_1, user=self.user)
        user_article_1.is_read = True
        user_article_1.save()

        other_category = make(Category, name=CategoryName.SKIN_SCHOOL.value)

        make(Article, category=other_category, period=self.period_2, is_published=True)

        url = reverse("articles-progress")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["percent_of_read_articles"], 33)

    def test_creating_article_with_period_and_a_category_other_than_core_program_fails(
        self,
    ):
        test_category = make(Category, name=CategoryName.SKIN_SCHOOL.value)
        test_article = Article(category=test_category, period=self.period_1)

        with self.assertRaisesMessage(
            ValidationError,
            "Only articles with Core Program category should have period defined",
        ):
            test_article.clean()

    def test_articles_list_shows_only_published_articles(self):
        make(
            Article,
            name="unpublished",
            category=self.category,
            period=self.period_1,
            is_published=False,
        )
        url = reverse("articles-list")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(response.json()["results"][0]["id"], self.article_1.id)
        self.assertEqual(response.json()["results"][1]["id"], self.article_2.id)
        self.assertEqual(response.json()["results"][2]["id"], self.intro_article.id)

    def test_articles_list_filter_by_category_does_not_display_unpublished_article(
        self,
    ):
        make(
            Article,
            name="unpublished",
            category=self.category,
            period=self.period_1,
            is_published=False,
        )
        url = reverse("articles-list")
        query = f"?category={self.category.pk}"
        response = self.get(url + query)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(response.json()["results"][0]["id"], self.article_1.id)
        self.assertEqual(response.json()["results"][1]["id"], self.article_2.id)

    def test_articles_detail_does_not_find_unpublished_article(self):
        unpublished_article = make(
            Article,
            name="unpublished",
            category=self.category,
            period=self.period_1,
            is_published=False,
        )
        url = reverse("articles-detail", kwargs={"pk": str(unpublished_article.id)})
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_creating_article_with_both_video_file_and_video_url(self):
        test_article = Article(
            category=self.category,
            video="file.mp4",
            video_url="https://www.youtube.com/watch?v=GQJhGA2x_20",
        )
        with self.assertRaisesMessage(
            ValidationError,
            "Only one video source should be provided - either file or url",
        ):
            test_article.clean()

    def test_creating_two_periods_with_same_unlocking_week_fails(self):
        self.period_1.unlocks_after_week = 0
        self.period_1.save()
        self.period_2.unlocks_after_week = 0
        with self.assertRaises(IntegrityError):
            self.period_2.save()

    def test_creating_a_second_article_with_initial_category(self):
        test_article = Article(category=self.initial_category)
        with self.assertRaisesMessage(
            ValidationError,
            "Initial category can have one related article only and already has one",
        ):
            test_article.clean()

    def test_updating_article_with_initial_category(self):
        prev_name = self.intro_article.name
        updated_name = "updated initial article"
        self.intro_article.name = updated_name
        self.intro_article.save()
        self.assertEqual(self.intro_article.name, updated_name)
        self.assertNotEqual(self.intro_article.name, prev_name)

    def test_updating_non_initial_category_article_to_initial_article(self):
        non_initial_article = make(
            Article,
            name="non_initial_article",
            category=self.category,
            period=self.period_2,
            is_published=True,
        )
        self.assertEqual(non_initial_article.category, self.category)
        self.assertEqual(non_initial_article.name, "non_initial_article")

        update_non_initial_article = Article(
            id=non_initial_article.id,
            name=non_initial_article.name,
            category=self.initial_category,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Initial category can have one related article only and already has one",
        ):
            update_non_initial_article.clean()

    @parameterized.expand(SubCategoryName.group_by_category.items())
    def test_creating_articles_with_subcategory(self, category_name, subcategory_names):
        for i, subcategory_name in enumerate(subcategory_names):
            category = make(Category, name=category_name)
            subcategory = make(SubCategory, name=subcategory_name)
            article_name = f"Test Recipe Article {i}"
            article = make(Article, name=article_name, category=category, subcategory=subcategory)
            self.assertEqual(article.name, article_name)
            self.assertEqual(article.category, category)
            self.assertEqual(article.subcategory, subcategory)

    @parameterized.expand([[subcategory] for subcategory in CategoryName.without_subcategories])
    def test_adding_subcategory_to_articles_which_cannot_have_subcategory(self, category_name):
        sub_category = make(SubCategory)
        category = make(Category, name=category_name)
        non_recipe_article = Article(category=category, subcategory=sub_category)
        category_names = " or ".join(CategoryName.get_display_names(*CategoryName.with_subcategories))
        with self.assertRaisesMessage(
            ValidationError,
            f"Only articles with {category_names} category should have subcategory defined",
        ):
            non_recipe_article.clean()

    @parameterized.expand([[subcategory] for subcategory in CategoryName.with_subcategories])
    def test_creating_articles_without_any_subcategory(self, category_name):
        category = make(Category, name=category_name)
        article = Article(category=category)
        with self.assertRaisesMessage(
            ValidationError,
            f"Articles with {category.display_name} category should have subcategory defined",
        ):
            article.clean()

    @parameterized.expand(
        [
            [
                CategoryName.RECIPES.value,
                SubCategoryName.get_by_category(CategoryName.INDIAN_RECIPES.value),
            ],
            [
                CategoryName.CORE_PROGRAM.value,
                SubCategoryName.get_by_category(CategoryName.RECIPES.value),
            ],
            [
                CategoryName.INDIAN_RECIPES.value,
                SubCategoryName.get_by_category(CategoryName.CORE_PROGRAM.value),
            ],
        ]
    )
    def test_creating_articles_with_non_valid_subcategory(self, category_name, subcategory_names):
        for subcategory_name in subcategory_names:
            subcategory = make(SubCategory, name=subcategory_name)
            category = make(Category, name=category_name)
            article = Article(category=category, subcategory=subcategory)
            with self.assertRaisesMessage(
                ValidationError,
                f"{subcategory.display_name} subcategory doesn't belong to {category.display_name} category",
            ):
                article.clean()

    def test_lifestyle_articles_list(self):
        article_1 = make(
            Article,
            lifestyle_category=LifeStyleCategories.SLEEP.value,
            is_published=True,
        )
        article_2 = make(
            Article,
            lifestyle_category=LifeStyleCategories.STRESS.value,
            is_published=True,
        )
        article_3 = make(
            Article,
            lifestyle_category=LifeStyleCategories.EXERCISE.value,
            is_published=True,
        )
        article_4 = make(
            Article,
            lifestyle_category=LifeStyleCategories.NUTRITION.value,
            is_published=True,
        )
        url = reverse("articles-lifestyle-articles")
        response = self.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 4)
        self.assertEqual(response.json()[0]["id"], article_1.id)
        self.assertEqual(response.json()[1]["id"], article_2.id)
        self.assertEqual(response.json()[2]["id"], article_3.id)
        self.assertEqual(response.json()[3]["id"], article_4.id)

    def test_create_more_than_4_articles_with_lifestyle_category(self):
        make(
            Article,
            lifestyle_category=LifeStyleCategories.SLEEP.value,
            is_published=True,
        )
        make(
            Article,
            lifestyle_category=LifeStyleCategories.STRESS.value,
            is_published=True,
        )
        make(
            Article,
            lifestyle_category=LifeStyleCategories.EXERCISE.value,
            is_published=True,
        )
        make(
            Article,
            lifestyle_category=LifeStyleCategories.NUTRITION.value,
            is_published=True,
        )
        article = Article(lifestyle_category=LifeStyleCategories.NUTRITION.value)
        with self.assertRaisesMessage(ValidationError, "Max 4 articles should be marked with lifestyle category"):
            article.clean()

    def test_create_more_than_one_article_with_same_lifestyle_category(self):
        make(
            Article,
            lifestyle_category=LifeStyleCategories.NUTRITION.value,
            is_published=True,
        )
        article = Article(lifestyle_category=LifeStyleCategories.NUTRITION.value)
        with self.assertRaisesMessage(
            ValidationError,
            f"Only one article should be marked with lifestyle category {LifeStyleCategories.NUTRITION.value}",
        ):
            article.clean()
