from copy import deepcopy
from datetime import timedelta

from django.utils import timezone
from model_bakery.baker import make
from rest_framework import status
from rest_framework.reverse import reverse

from apps.home.models import SiteConfiguration
from apps.routines import RecommendationCategory
from apps.routines.models import Recommendation, FaceScan, FaceScanAnalytics
from apps.utils.error_codes import Errors
from apps.utils.tests_utils import BaseTestCase


class DailyProductGroupTest(BaseTestCase):
    url = reverse("recommendations-list")

    def setUp(self):
        super().setUp()
        siteconfig = SiteConfiguration.get_solo()
        current_time = timezone.now()
        self.face_scan = make(FaceScan, user=self.user, created_at=current_time)
        FaceScan.objects.filter(id=self.face_scan.id).update(
            created_at=current_time - timedelta(days=siteconfig.scan_duration - 1)
        )
        make(FaceScanAnalytics, face_scan=self.face_scan, is_valid=True)

    def test_create_recommendations_mandatory_fields(self):
        self.query_limits["ANY POST REQUEST"] = 17

        payload = [{"category": category.value} for category in RecommendationCategory]

        response = self.authorize().post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        recommendations = Recommendation.objects.filter(user=self.user)

        self.assertEqual(len(payload), len(response.data))

        for request_recommendation, response_recommendation in zip(payload, response.data):
            recommendation = recommendations.get(category=request_recommendation["category"])

            self.assertEqual(response_recommendation["id"], recommendation.id)
            self.assertEqual(response_recommendation["category"], recommendation.category)
            self.assertEqual(
                response_recommendation["previuos_indexes"],
                recommendation.previuos_indexes,
            )
            self.assertEqual(response_recommendation["current_index"], recommendation.current_index)
            self.assertEqual(response_recommendation["is_featured"], recommendation.is_featured)

            for key, value in request_recommendation.items():
                self.assertEqual(response_recommendation[key], value)

    def test_create_recommendations_optional_fields(self):
        self.query_limits["ANY POST REQUEST"] = 17

        payload = [
            {
                "category": category.value,
                "current_index": i,
                "previuos_indexes": [100, 200],
                "is_featured": False,
            }
            for i, category in enumerate(RecommendationCategory, 1)
        ]

        response = self.authorize().post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        recommendations = Recommendation.objects.filter(user=self.user)

        self.assertEqual(len(payload), len(response.data))

        for request_recommendation, response_recommendation in zip(payload, response.data):
            recommendation = recommendations.get(category=request_recommendation["category"])

            self.assertEqual(response_recommendation["id"], recommendation.id)
            self.assertEqual(response_recommendation["category"], recommendation.category)
            self.assertEqual(
                response_recommendation["previuos_indexes"],
                recommendation.previuos_indexes,
            )
            self.assertEqual(response_recommendation["current_index"], recommendation.current_index)
            self.assertEqual(response_recommendation["is_featured"], recommendation.is_featured)

            for key, value in request_recommendation.items():
                self.assertEqual(
                    response_recommendation[key],
                    value if key != "previuos_indexes" else [],
                )

    def test_create_multiple_featured_recommendations(self):
        self.query_limits["ANY POST REQUEST"] = 11

        payload = [
            {
                "category": category.value,
                "current_index": i,
                "previuos_indexes": [10 * i, 20 * i],
                "is_featured": True,
            }
            for i, category in enumerate(RecommendationCategory, 1)
        ]

        response = self.authorize().post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data, [Errors.MULTIPLE_FEATURED_RECOMMENDATIONS.value])

    def test_create_recommendations_duplicate_categories(self):
        self.query_limits["ANY POST REQUEST"] = 11

        payload = [{"category": RecommendationCategory.ACNE.value} for _ in range(len(RecommendationCategory))]

        response = self.authorize().post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data, [Errors.DUPLICATE_RECOMMENDATION_CATEGORIES.value])

    def test_get_recommendations(self):
        self.query_limits["ANY GET REQUEST"] = 6

        recommendations = [
            make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            for i, category in enumerate(RecommendationCategory, 1)
        ]

        response = self.authorize().get(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(len(recommendations), len(response.data))

        for recommendation, response_recommendation in zip(recommendations, response.data):
            self.assertEqual(response_recommendation["id"], recommendation.id)
            self.assertEqual(response_recommendation["category"], recommendation.category)
            self.assertEqual(
                response_recommendation["previuos_indexes"],
                recommendation.previuos_indexes,
            )
            self.assertEqual(response_recommendation["current_index"], recommendation.current_index)
            self.assertEqual(response_recommendation["is_featured"], recommendation.is_featured)

    def test_get_recommendations_facescan_unavailable(self):
        self.face_scan.delete()

        recommendations = [
            make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            for i, category in enumerate(RecommendationCategory, 1)
        ]

        response = self.authorize().get(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(len(recommendations), len(response.data))

        for recommendation, response_recommendation in zip(recommendations, response.data):
            self.assertEqual(response_recommendation["id"], recommendation.id)
            self.assertEqual(response_recommendation["category"], recommendation.category)
            self.assertEqual(
                response_recommendation["previuos_indexes"],
                recommendation.previuos_indexes + [recommendation.current_index],
            )
            self.assertEqual(response_recommendation["current_index"], None)
            self.assertEqual(response_recommendation["is_featured"], recommendation.is_featured)

    def test_update_recommendations_current_index(self):
        self.query_limits["ANY PATCH REQUEST"] = 32

        recommendations = []
        payload = []

        for i, category in enumerate(RecommendationCategory, 1):
            recommendation = make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            recommendations.append(recommendation)

            payload.append({"id": recommendation.id, "current_index": i * 2})

        response = self.authorize().patch(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(len(recommendations), len(response.data))
        self.assertEqual(len(recommendations), len(payload))

        for recommendation, response_recommendation, request_recommendation in zip(
            recommendations, response.data, payload
        ):
            recommendation.refresh_from_db()

            self.assertEqual(response_recommendation["id"], recommendation.id)
            self.assertEqual(response_recommendation["category"], recommendation.category)
            self.assertEqual(
                response_recommendation["previuos_indexes"],
                recommendation.previuos_indexes,
            )
            self.assertEqual(response_recommendation["current_index"], recommendation.current_index)
            self.assertEqual(response_recommendation["is_featured"], recommendation.is_featured)

            for key, value in request_recommendation.items():
                self.assertEqual(response_recommendation[key], value)

    def test_update_recommendations_previous_indexes(self):
        self.query_limits["ANY PATCH REQUEST"] = 32

        recommendations = []
        payload = []

        for i, category in enumerate(RecommendationCategory, 1):
            recommendation = make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            recommendations.append(recommendation)

            payload.append({"id": recommendation.id, "previuos_indexes": []})

        response = self.authorize().patch(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(len(recommendations), len(response.data))
        self.assertEqual(len(recommendations), len(payload))

        for recommendation, response_recommendation, request_recommendation in zip(
            recommendations, response.data, payload
        ):
            recommendation.refresh_from_db()

            self.assertEqual(response_recommendation["id"], recommendation.id)
            self.assertEqual(response_recommendation["category"], recommendation.category)
            self.assertEqual(
                response_recommendation["previuos_indexes"],
                recommendation.previuos_indexes,
            )
            self.assertEqual(response_recommendation["current_index"], recommendation.current_index)
            self.assertEqual(response_recommendation["is_featured"], recommendation.is_featured)

            for key, value in request_recommendation.items():
                self.assertEqual(response_recommendation[key], value)

    def test_update_recommendations_category(self):
        self.query_limits["ANY PATCH REQUEST"] = 32

        recommendations = []
        payload = []

        for i, category in enumerate(RecommendationCategory, 1):
            recommendation = make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            recommendations.append(recommendation)

            payload.append({"id": recommendation.id, "category": "Python"})

        response = self.authorize().patch(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(len(recommendations), len(response.data))
        self.assertEqual(len(recommendations), len(payload))

        for recommendation, response_recommendation, request_recommendation in zip(
            recommendations, response.data, payload
        ):
            recommendation.refresh_from_db()

            self.assertEqual(response_recommendation["id"], recommendation.id)
            self.assertEqual(response_recommendation["category"], recommendation.category)
            self.assertEqual(
                response_recommendation["previuos_indexes"],
                recommendation.previuos_indexes,
            )
            self.assertEqual(response_recommendation["current_index"], recommendation.current_index)
            self.assertEqual(response_recommendation["is_featured"], recommendation.is_featured)

            for key, value in request_recommendation.items():
                if key == "category":
                    self.assertNotEqual(response_recommendation[key], value)
                else:
                    self.assertEqual(response_recommendation[key], value)

    def test_update_multiple_featured_recommendations(self):
        self.query_limits["ANY PATCH REQUEST"] = 10

        recommendations = []
        payload = []

        for i, category in enumerate(RecommendationCategory, 1):
            recommendation = make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            recommendations.append(recommendation)

            payload.append({"id": recommendation.id, "is_featured": True})

        response = self.authorize().patch(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        self.assertEqual(response.data, [Errors.MULTIPLE_FEATURED_RECOMMENDATIONS.value])

    def test_update_recommendations_no_ids(self):
        recommendations = []
        payload = []

        for i, category in enumerate(RecommendationCategory, 1):
            recommendation = make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            recommendations.append(recommendation)
            payload.append({"is_featured": True})

        response = self.authorize().patch(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.data)
        self.assertEqual(response.data, {"detail": "Not found."})

    def test_update_recommendations_non_valid_previuos_indexes(self):
        self.query_limits["ANY PATCH REQUEST"] = 26

        recommendations = []
        payload = []
        expected = []

        for i, category in enumerate(RecommendationCategory, 1):
            recommendation = make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            recommendations.append(recommendation)

            payload.append({"id": recommendation.id, "previuos_indexes": [i * 100, i * 200]})

            expected.append({"previuos_indexes": [Errors.PREVIOUS_INDEXES_CAN_ONLY_BE_RESET.value]})

        response = self.authorize().patch(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data, expected)

    def test_update_recommendations_to_featured(self):
        self.query_limits["ANY PATCH REQUEST"] = 34

        recommendations = []
        payload = []

        number_of_categories = len(RecommendationCategory)

        for i, category in enumerate(RecommendationCategory, 1):
            recommendation = make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=i != number_of_categories,
            )
            recommendations.append(recommendation)

            payload.append({"id": recommendation.id, "is_featured": i == number_of_categories})

        response = self.authorize().patch(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(len(recommendations), len(response.data))
        self.assertEqual(len(recommendations), len(payload))

        for recommendation, response_recommendation, request_recommendation in zip(
            recommendations, response.data, payload
        ):
            recommendation.refresh_from_db()

            self.assertEqual(response_recommendation["id"], recommendation.id)
            self.assertEqual(response_recommendation["category"], recommendation.category)
            self.assertEqual(
                response_recommendation["previuos_indexes"],
                recommendation.previuos_indexes,
            )
            self.assertEqual(response_recommendation["current_index"], recommendation.current_index)
            self.assertEqual(response_recommendation["is_featured"], recommendation.is_featured)

            for key, value in request_recommendation.items():
                self.assertEqual(response_recommendation[key], value)

    def test_update_recommendations_current_index_matches_previous_indexes(self):
        self.query_limits["ANY PATCH REQUEST"] = 26

        recommendations = []
        payload = []
        expected = []

        for i, category in enumerate(RecommendationCategory, 1):
            recommendation = make(
                Recommendation,
                user=self.user,
                category=category,
                current_index=i,
                previuos_indexes=[10 * i, 20 * i],
                is_featured=False,
            )
            recommendations.append(recommendation)

            payload.append({"id": recommendation.id, "current_index": 10 * i})

            expected.append({"non_field_errors": [Errors.CURRENT_INDEX_CANT_MATCH_PREVIOUS_INDEXES.value]})

        response = self.authorize().patch(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data, expected)

        self.assertEqual(len(recommendations), len(payload))

        for recommendation, request_recommendation in zip(recommendations, payload):
            old_recommendation = deepcopy(recommendation)

            recommendation.refresh_from_db()

            for key in request_recommendation.keys():
                self.assertEqual(getattr(old_recommendation, key), getattr(recommendation, key))
