from django.conf import settings
from django.urls import reverse
from model_bakery.baker import make
from rest_framework import status

from apps.home.models import (
    SiteConfiguration,
    DashboardElement,
    DashboardElementTranslation,
    DashboardOrder,
)
from apps.utils.tests_utils import BaseTestCase


class AppConfigTestCase(BaseTestCase):
    def test_app_config(self):
        site_config = SiteConfiguration.get_solo()
        response = self.client.get(reverse("app-config"), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["version"], site_config.manifest_version)
        self.assertEqual(response.json()["default_language"], settings.DEFAULT_LANGUAGE)
        self.assertEqual(response.json()["enabled_languages"], [])
        self.assertEqual(response.json()["translations"]["en"], {})
        self.assertEqual(response.json()["dashboard_order"], {})
        self.assertEqual(response.json()["skin_journey"], {})
        self.assertEqual(response.json()["shop_block"], {})
        self.assertEqual(response.json()["scan_duration"], site_config.scan_duration)
        self.assertEqual(
            response.json()["android_payments_enabled"],
            site_config.android_payments_enabled,
        )
        self.assertEqual(response.json()["ios_payments_enabled"], site_config.ios_payments_enabled)
        self.assertTrue(response.json()["payments_enabled"])

    def test_regenerate_manifest(self):
        url = reverse("regenerate-cache")
        response = self.client.get(url, format="json", HTTP_REFERER="test/url")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, "test/url")

    def test_regenerate_manifest_redirects(self):
        site_config = SiteConfiguration.get_solo()
        url = reverse("regenerate-cache")
        url_final = reverse("app-config")

        response = self.client.get(url, format="json", HTTP_REFERER=url_final, follow=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["version"], site_config.manifest_version)
        self.assertEqual(response.json()["default_language"], settings.DEFAULT_LANGUAGE)
        self.assertEqual(response.json()["enabled_languages"], [])
        self.assertEqual(response.json()["translations"]["en"], {})
        self.assertEqual(response.json()["dashboard_order"], {})
        self.assertEqual(response.json()["scan_duration"], site_config.scan_duration)

    def test_regenerate_manifest_creates_site_config_with_authenticated_user(self):
        url = reverse("regenerate-cache")
        url_final = reverse("app-config")

        self.query_limits["ANY GET REQUEST"] = 10
        response = self.get(url, HTTP_REFERER=url_final, follow=True)
        site_config = SiteConfiguration.get_solo()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["version"], site_config.manifest_version)
        self.assertEqual(response.json()["default_language"], settings.DEFAULT_LANGUAGE)
        self.assertEqual(response.json()["enabled_languages"], [])
        self.assertEqual(response.json()["translations"]["en"], {})
        self.assertEqual(response.json()["dashboard_order"], {})
        self.assertEqual(response.json()["scan_duration"], site_config.scan_duration)

    def test_app_config_with_dashboard_order(self):
        dashboard_order = make(DashboardOrder)
        site_config = SiteConfiguration.get_solo()
        site_config.dashboard_order = dashboard_order
        site_config.save()

        response = self.client.get(reverse("app-config"), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["version"], site_config.manifest_version)
        self.assertEqual(response.json()["default_language"], settings.DEFAULT_LANGUAGE)
        self.assertEqual(response.json()["enabled_languages"], [])
        self.assertEqual(response.json()["translations"]["en"], {})
        self.assertEqual(
            response.json()["dashboard_order"]["core_program"],
            dashboard_order.core_program,
        )
        self.assertEqual(response.json()["dashboard_order"]["recipes"], dashboard_order.recipes)
        self.assertEqual(response.json()["dashboard_order"]["skin_tools"], dashboard_order.skin_tools)
        self.assertEqual(
            response.json()["dashboard_order"]["skin_school"],
            dashboard_order.skin_school,
        )
        self.assertEqual(
            response.json()["dashboard_order"]["skin_stories"],
            dashboard_order.skin_stories,
        )
        self.assertEqual(response.json()["scan_duration"], site_config.scan_duration)

    def test_app_config_with_dashboard_elements(self):
        skin_journey = make(DashboardElement, name="Test1")
        skin_journey.image.name = "random_img_1.jpg"
        skin_journey.save()
        skin_journey_translation = make(DashboardElementTranslation, dashboard_element=skin_journey)

        shop_block = make(DashboardElement, name="Test2")
        shop_block.image.name = "random_img_2.jpg"
        shop_block.save()
        shop_block_translation = make(DashboardElementTranslation, dashboard_element=shop_block)

        site_config = SiteConfiguration.get_solo()
        site_config.skin_journey = skin_journey
        site_config.shop_block = shop_block
        site_config.save()
        self.query_limits["ANY GET REQUEST"] = 10

        response = self.client.get(reverse("app-config"), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["version"], site_config.manifest_version)
        self.assertEqual(response.json()["default_language"], settings.DEFAULT_LANGUAGE)
        self.assertEqual(response.json()["enabled_languages"], [])
        self.assertEqual(response.json()["translations"]["en"], {})
        self.assertEqual(response.json()["skin_journey"]["title"], skin_journey_translation.title)
        self.assertEqual(
            response.json()["skin_journey"]["main_text"],
            skin_journey_translation.content,
        )
        self.assertIn(skin_journey.image.url, response.json()["skin_journey"]["image"])
        self.assertEqual(response.json()["shop_block"]["title"], shop_block_translation.title)
        self.assertEqual(response.json()["shop_block"]["main_text"], shop_block_translation.content)
        self.assertIn(shop_block.image.url, response.json()["shop_block"]["image"])
        self.assertEqual(response.json()["scan_duration"], site_config.scan_duration)

    def test_app_config_with_dashboard_elements_when_translations_are_missing(self):
        skin_journey = make(DashboardElement, name="Test")
        skin_journey.image.name = "random_img_1.jpg"
        skin_journey.save()

        shop_block = make(DashboardElement, name="Test2")
        shop_block.image.name = "random_img_2.jpg"
        shop_block.save()

        site_config = SiteConfiguration.get_solo()
        site_config.skin_journey = skin_journey
        site_config.shop_block = shop_block
        site_config.save()
        self.query_limits["ANY GET REQUEST"] = 10

        response = self.client.get(reverse("app-config"), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["version"], site_config.manifest_version)
        self.assertEqual(response.json()["default_language"], settings.DEFAULT_LANGUAGE)
        self.assertEqual(response.json()["enabled_languages"], [])
        self.assertEqual(response.json()["translations"]["en"], {})
        self.assertEqual(response.json()["skin_journey"]["title"], skin_journey.name)
        self.assertEqual(response.json()["skin_journey"]["main_text"], None)
        self.assertIn(skin_journey.image.url, response.json()["skin_journey"]["image"])
        self.assertEqual(response.json()["shop_block"]["title"], shop_block.name)
        self.assertEqual(response.json()["shop_block"]["main_text"], None)
        self.assertIn(shop_block.image.url, response.json()["shop_block"]["image"])
        self.assertEqual(response.json()["scan_duration"], site_config.scan_duration)
