import base64
import binascii
from functools import wraps
import json
import logging
from typing import Callable, Optional

from django.conf import settings
from django.db.models import QuerySet
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message
import jwt
from redis import StrictRedis
from redis.exceptions import ConnectionError

LOGGER = logging.getLogger("app")


def redis_cache(
    func: Callable = None,
    ttl: int = settings.REDIS_CACHE_DEFAULT_TTL,
    redis_url: str = settings.REDIS_URL,
    sort_keys: bool = False,
):
    """
    Caches returned value by a callable using redis as a backend.
    The cached value is stored for `ttl` number of seconds.
    All arguments and result of a decorated callable have to be JSON serializable.
    If `sort_keys` is True - value keys are sorted before storing it in redis.

    Usage examples:
        @redis_cache
        def my_function():
            return "Hello world"

        @redis_cache(ttl=3600)
        def my_another_function(name):
            return {"greeting": f"Hello {name}"}
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            update_redis_cache = kwargs.pop("update_redis_cache", False)

            # Allow to override redis_url using django.test.override_setting in case redis_url is empty
            url = redis_url or settings.REDIS_URL

            if not url:
                return func(*args, **kwargs)

            return _get_cached_value_from_redis(url, ttl, update_redis_cache, sort_keys, func, *args, **kwargs)

        return wrapper

    if callable(func):
        return decorator(func)

    return decorator


def _get_cached_value_from_redis(  # noqa: CFQ002
    redis_url: str, ttl: int, update_redis_cache: bool, sort_keys: bool, func: Callable, *args, **kwargs
):
    key = json.dumps(
        {
            "__module__": func.__module__,
            "__qualname__": func.__qualname__,
            "args": args,
            "kwargs": kwargs,
        },
        sort_keys=True,
    )

    try:
        with StrictRedis.from_url(redis_url) as r:
            if not update_redis_cache:
                cached_value = r.get(key)
                if cached_value is not None:
                    return json.loads(cached_value)

            value = func(*args, **kwargs)
            r.setex(key, ttl, json.dumps(value, sort_keys=sort_keys))

    except ConnectionError:
        LOGGER.exception("Failed to connect to Redis to retrieve cached values.")
        value = func(*args, **kwargs)

    return value


def send_push_notifications(devices: QuerySet[FCMDevice], message: Message) -> None:
    """Sends FCM push notifications to devices"""
    for device in devices:
        device.send_message(message=message)
        LOGGER.debug("Successfully sent push notifications to device [%s].", device.device_id)


def decode_data(encoded_message: str) -> Optional[dict]:
    LOGGER.info("Starting decoding base64 encoded data.")
    try:
        decoded_message = json.loads(base64.b64decode(encoded_message).decode("utf-8"))
        LOGGER.debug("Successfully decoded base64 encoded data.")
    except (binascii.Error, json.JSONDecodeError) as err:
        decoded_message = None
        LOGGER.exception(
            "Decoding failed for providing string [%s] due to [%s].",
            encoded_message,
            err,
        )
    return decoded_message


def parse_jwt(signed_payload: str) -> dict:
    """Parses signed jwt using encryption algorithm ES256"""
    LOGGER.info("Starting parsing jwt.")
    try:
        parsed_data = jwt.decode(jwt=signed_payload, options={"verify_signature": False})
        LOGGER.debug("Successfully parsed jwt.")
    except jwt.DecodeError as err:
        parsed_data = None
        LOGGER.exception("Parsing failed for providing jwt [%s] due to [%s].", signed_payload, err)
    return parsed_data
