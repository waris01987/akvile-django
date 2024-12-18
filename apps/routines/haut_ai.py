import logging
from typing import List, Tuple

from django.conf import settings
import requests

from apps.utils.helpers import redis_cache

LOGGER = logging.getLogger("app")


class HautAiException(Exception):
    pass


@redis_cache(ttl=settings.HAUT_AI_CACHE_TTL)
def get_auth_info() -> Tuple[str, str]:
    response = requests.post(
        f"{settings.HAUT_AI_HOST}/api/v1/login/",
        json={
            "username": settings.HAUT_AI_USERNAME,
            "password": settings.HAUT_AI_PASSWORD,
        },
    )

    if response.status_code != 200:
        LOGGER.error("Unable to authenticate Haut.ai. Body: %s", response.json())
        raise HautAiException()
    return response.json()["company_id"], response.json()["access_token"]


def get_subject_id(subject_name: str, company_id: str, token: str) -> str:
    if not token or not company_id:
        company_id, token = get_auth_info()
    response = requests.post(
        f"{settings.HAUT_AI_HOST}/api/v1/companies/{company_id}/datasets/{settings.HAUT_AI_DATA_SET_ID}/subjects/",
        json={"name": subject_name},
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code != 201:
        LOGGER.error("Unable to get subject id for Haut.ai. Body: %s", response.json())
        raise HautAiException()
    return response.json()["id"]


def get_smoothing_results(subject_id: str, batch_id: str, image_id: str, company_id: str, token: str) -> dict:
    if not token or not company_id:
        company_id, token = get_auth_info()
    response = requests.get(
        f"{settings.HAUT_AI_HOST}/api/v1/companies/{company_id}/"
        f"datasets/{settings.HAUT_AI_DATA_SET_ID}/"
        f"subjects/{subject_id}/batches/{batch_id}/"
        f"images/{image_id}/smoothed_results/"
        f"?sample_time_window=14&sample_max_size=10&smoothing_method=mean",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code != 200:
        LOGGER.error(
            "Unable to get smoothing results for Haut.ai. Image: %s, Body: %s",
            image_id,
            response.json(),
        )
        raise HautAiException()
    return response.json()


def get_image_results(subject_id: str, batch_id: str, image_id: str, company_id: str, token: str) -> dict:
    if not token or not company_id:
        company_id, token = get_auth_info()
    response = requests.get(
        f"{settings.HAUT_AI_HOST}/api/v1/companies/{company_id}/"
        f"datasets/{settings.HAUT_AI_DATA_SET_ID}/"
        f"subjects/{subject_id}/batches/{batch_id}/images/{image_id}/results/",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code != 200:
        LOGGER.error(
            "Unable to get image results for Haut.ai. Image: %s Body: %s",
            image_id,
            response.json(),
        )
        raise HautAiException()
    return response.json()


def upload_picture(subject_id: str, image_base64: str, company_id: str, token: str) -> Tuple[str, str]:
    if not token or not company_id:
        company_id, token = get_auth_info()
    resp = requests.post(
        f"{settings.HAUT_AI_HOST}/api/v1/companies/{company_id}/"
        f"datasets/{settings.HAUT_AI_DATA_SET_ID}/subjects/{subject_id}/batches/",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code != 201:
        LOGGER.error(
            "Unable create batch for subject on Haut.ai. Subject: %s Body: %s",
            subject_id,
            resp.json(),
        )
        raise HautAiException()

    batch_id = resp.json()["id"]

    image_upload_resp = requests.post(
        f"{settings.HAUT_AI_HOST}/api/v1/companies/{company_id}/"
        f"datasets/{settings.HAUT_AI_DATA_SET_ID}/subjects/{subject_id}/batches/{batch_id}/images/",
        json={
            # side_id = 1 is for front image
            "side_id": 1,
            # light_id = 1 is for regular light
            "light_id": 1,
            "b64data": image_base64,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    if image_upload_resp.status_code != 201:
        LOGGER.error(
            "Unable upload picture to Haut.ai. Subject: %s Batch: %s Body: %s",
            subject_id,
            batch_id,
            resp.json(),
        )
        raise HautAiException()

    image_id = image_upload_resp.json()["id"]

    return batch_id, image_id


HAUT_AI_ALGO_FIELD_MAPPING = {
    "selfie_v2.hydration": "hydration",
    "selfie_v2.translucency": "translucency",
    "selfie_v2.pores": "pores",
    "selfie_v2.redness": "redness",
    "selfie_v2.eye_bags": "eye_bags",
    "selfie_v2.uniformness": "uniformness",
    "selfie_v2.lines": "lines",
    "selfie_v2.pigmentation": "pigmentation",
    "selfie_v2.acne": "acne",
    "selfie_v2.quality": "quality",
    "selfie_v2.sagging": "sagging",
}


def build_orm_analytics_model(image_data: list) -> dict:
    image_raw_values = []
    for algo_result in image_data:
        if "area_results" in algo_result["result"] and algo_result["result"]["area_results"]:
            face_result = next((x for x in algo_result["result"]["area_results"] if x["area_name"] == "face"))
            image_raw_values.append(
                {
                    "algorithm_tech_name": algo_result["algorithm_family_tech_name"],
                    "value": face_result["main_metric"]["value"],
                }
            )
    data_to_save = {}
    for raw_data in image_raw_values:
        if raw_data["algorithm_tech_name"] in HAUT_AI_ALGO_FIELD_MAPPING:
            data_to_save[HAUT_AI_ALGO_FIELD_MAPPING[raw_data["algorithm_tech_name"]]] = raw_data["value"]
    return data_to_save


def build_orm_smoothing_analytics_model(data: List) -> dict:
    data_to_save = {}
    for raw_data in data:
        if raw_data["algorithm_tech_name"] in HAUT_AI_ALGO_FIELD_MAPPING:
            data_to_save[HAUT_AI_ALGO_FIELD_MAPPING[raw_data["algorithm_tech_name"]]] = raw_data["value"]
    return data_to_save
