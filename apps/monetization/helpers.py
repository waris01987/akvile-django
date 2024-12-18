import datetime
import json
import logging

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient import discovery
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
import pytz
import requests
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.utils.error_codes import Errors

LOGGER = logging.getLogger("app")


def get_app_store_response(data: dict) -> Response:
    """
    Helper for automatic switch between App Store Production and Sandbox environments.

    Apple recommends this validation flow to avoid switching between URLs while application is tested,
    reviewed by App Review, or live in the App Store.
    """
    app_store_response = requests.post(url=settings.APPLE_RECEIPT_VALIDATION_PRODUCTION_URL, json=data)
    if app_store_response.json().get("status") == settings.APPLE_ERROR_VALIDATE_RECEIPT_IN_SANDBOX:
        app_store_response = requests.post(url=settings.APPLE_RECEIPT_VALIDATION_SANDBOX_URL, json=data)
    return app_store_response


def validate_ios_subscription_purchase_receipt(  # noqa C901
    app_store_response: Response,
) -> tuple[str, str, datetime.datetime, datetime.datetime]:
    """Validate App Store IAP Receipt and provide informative message if it's invalid."""
    response = app_store_response.json()
    if status := response.get("status"):
        LOGGER.error("Purchase validation failed with status code [%s] from App Store!", status)
        raise ValidationError([Errors.UNEXPECTED_ERROR_FROM_APP_STORE.value])
    grace_period_expires_at = None
    pending_renewal_info = response.get("pending_renewal_info")
    if pending_renewal_info:
        if expiration_intent := pending_renewal_info[0].get("expiration_intent"):
            LOGGER.error(
                "Appstore subscription purchase was cancelled. Cancel reason [%s]",
                expiration_intent,
            )
            raise ValidationError([Errors.SUBSCRIPTION_PURCHASE_WAS_CANCELLED.value])
        if grace_period_expires_date_ms := pending_renewal_info[0].get("grace_period_expires_date_ms"):
            grace_period_expires_at = datetime.datetime.fromtimestamp(
                int(grace_period_expires_date_ms) / 1000, tz=pytz.UTC
            )
    latest_receipt_info = response.get("latest_receipt_info")
    if not latest_receipt_info:
        LOGGER.error("Receipt does not contain any purchases.")
        raise ValidationError([Errors.NO_PURCHASE_IN_RECEIPT.value])
    app_account_token = latest_receipt_info[0].get("app_account_token")
    if app_account_token is None:
        LOGGER.error("Receipt does not contain any purchases.")
        raise ValidationError([Errors.NO_APP_ACCOUNT_TOKEN_FOUND.value])
    start_time_in_milliseconds = latest_receipt_info[0].get("purchase_date_ms")
    start_time = datetime.datetime.fromtimestamp(int(start_time_in_milliseconds) / 1000, tz=pytz.UTC)
    transaction_id = latest_receipt_info[0].get("original_transaction_id")

    if grace_period_expires_at:
        expire_time = grace_period_expires_at
    else:
        expire_time_in_milliseconds = latest_receipt_info[0].get("expires_date_ms")
        expire_time = datetime.datetime.fromtimestamp(int(expire_time_in_milliseconds) / 1000, tz=pytz.UTC)
    return app_account_token, transaction_id, start_time, expire_time


def get_play_store_response(data: dict) -> dict:
    """Return response dict from Google Play Store with data about requested purchase."""
    try:
        return (
            get_service()
            .purchases()
            .subscriptions()
            .get(
                packageName=data["packageName"],
                subscriptionId=data["subscriptionId"],
                token=data["token"],
            )
            .execute()
        )
    except HttpError as err:
        LOGGER.exception(err)
        raise ValidationError([Errors.UNEXPECTED_ERROR_FROM_PLAY_STORE.value])


def validate_android_subscription_purchase_receipt(
    play_store_response: dict,
) -> tuple[str, str, datetime.datetime, datetime.datetime]:
    """Validate that Android IAP is fully purchased and"""
    payment_state = play_store_response.get("paymentState")
    cancel_reason = play_store_response.get("cancelReason")
    auto_resume_time_in_milliseconds = play_store_response.get("autoResumeTimeMillis")
    start_time_in_milliseconds = play_store_response.get("startTimeMillis")
    expire_time_in_milliseconds = play_store_response.get("expiryTimeMillis")
    transaction_id = play_store_response.get("orderId")
    obfuscated_account_id = play_store_response.get("obfuscatedExternalAccountId")
    if cancel_reason is not None:
        LOGGER.error(
            "Google play subscription purchase was cancelled. Cancel reason [%s]",
            cancel_reason,
        )
        raise ValidationError([Errors.SUBSCRIPTION_PURCHASE_WAS_CANCELLED.value])
    if payment_state is None or payment_state == 0:
        LOGGER.error("Payment not yet received. Payment State: [%s]", payment_state)
        raise ValidationError([Errors.PURCHASE_PAYMENT_IS_NOT_YET_RECEIVED.value])
    if obfuscated_account_id is None:
        LOGGER.error("Obfuscated account id is missing.")
        raise ValidationError([Errors.NO_OBFUSCATED_ACCOUNT_ID_FOUND.value])
    expire_time = datetime.datetime.fromtimestamp(int(expire_time_in_milliseconds) / 1000, tz=pytz.UTC)
    if auto_resume_time_in_milliseconds:
        start_time = datetime.datetime.fromtimestamp(int(auto_resume_time_in_milliseconds) / 1000, tz=pytz.UTC)
    else:
        start_time = datetime.datetime.fromtimestamp(int(start_time_in_milliseconds) / 1000, tz=pytz.UTC)
    return obfuscated_account_id, transaction_id, start_time, expire_time


def get_service() -> Resource:
    """Generates and returns google service resource from provided credentials on settings"""
    credentials = settings.GOOGLE_API_SERVICE_CREDENTIALS
    api_credentials = service_account.Credentials.from_service_account_info(json.loads(credentials))
    return discovery.build(
        settings.ANDROID_SERVICE_NAME,
        settings.ANDROID_SERVICE_VERSION,
        credentials=api_credentials,
    )
