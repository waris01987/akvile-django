import logging

from django.conf import settings
import requests

from apps.celery import app
from apps.users.models import User

LOGGER = logging.getLogger("app")


@app.task
def set_user_amplitude_info(user_id: int) -> None:
    user = User.objects.get(id=user_id)
    headers = {"Authorization": f"Api-Key {settings.AMPLITUDE_API_KEY}"}
    url = f"https://profile-api.amplitude.com/v1/userprofile?user_id=user-{user.id}&get_amp_props=true"
    response = requests.request(method="GET", url=url, headers=headers)
    if response.status_code == 200:
        user_data = response.json()["userData"]
        if user_amp_props := user_data.get("amp_props"):
            user.geolocation = user_amp_props.get("country", "")
            device_type = user_amp_props.get("device_type")
            user.device = device_type if device_type else user_amp_props.get("device", "")
            user.operating_system = user_amp_props.get("os", "")
            user.is_amplitude_synced = True
            user.save(
                update_fields=[
                    "geolocation",
                    "device",
                    "operating_system",
                    "is_amplitude_synced",
                ]
            )
        else:
            user.is_amplitude_synced = True
            user.save(update_fields=["is_amplitude_synced"])
    elif response.status_code == 404:
        LOGGER.info(
            "Error while setting the device info for user %s. Status code: %s",
            user,
            response.status_code,
        )
        user.is_amplitude_synced = True
        user.save(update_fields=["is_amplitude_synced"])
    else:
        LOGGER.error("Error while setting the device info. Status code: %s", response.status_code)


@app.task
def set_user_device_info(user_ids: list[int]) -> None:
    for user_id in user_ids:
        set_user_amplitude_info.delay(user_id=user_id)
