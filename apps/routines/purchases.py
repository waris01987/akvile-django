import base64
import datetime
import json
import logging
import time
from typing import Optional

from django.conf import settings
from django.db.models import Q
import jwt
import pytz
import requests

from apps.monetization.helpers import get_play_store_response, get_app_store_response
from apps.routines import (
    PurchaseStatus,
    PlayStoreSubscriptionNotificationGroups,
    AppStoreSubscriptionNotificationGroups,
)
from apps.routines.models import PurchaseHistory, StatisticsPurchase
from apps.utils.helpers import parse_jwt

LOGGER = logging.getLogger("app")


def process_statistics_purchase_play_store_notifications(  # noqa: C901
    subscription_notification: dict,
) -> None:
    """Processes and updates statistics purchase notification from Playstore notification server"""
    LOGGER.info("Started to process play store statistics purchase notifications.")
    notification = subscription_notification.get("subscriptionNotification", {})
    package_name = subscription_notification.get("packageName")
    token = notification.get("purchaseToken")
    if token and (statistics_purchase := StatisticsPurchase.objects.filter(receipt_data=token).first()):
        notification_type = notification.get("notificationType")
        subscription_id = notification.get("subscriptionId")
        verified_data = get_play_store_response(
            {
                "packageName": package_name,
                "subscriptionId": subscription_id,
                "token": token,
            }
        )
        start_time_in_milliseconds = verified_data.get("startTimeMillis")
        expire_time_in_milliseconds = verified_data.get("expiryTimeMillis")
        start_time = datetime.datetime.fromtimestamp(int(start_time_in_milliseconds) / 1000, tz=pytz.UTC)
        expire_time = datetime.datetime.fromtimestamp(int(expire_time_in_milliseconds) / 1000, tz=pytz.UTC)
        obfuscated_account_id = verified_data.get("obfuscatedExternalAccountId")
        if str(statistics_purchase.id) == obfuscated_account_id:
            if notification_type in PlayStoreSubscriptionNotificationGroups.ACTIVE_TYPES:
                statistics_purchase.status = PurchaseStatus.COMPLETED.value
                # ending of the orderId contains total number of renewals for the subscription
                # i.e. GPA.3326-1565-4756-41190..0 is the second renewal transaction and the first does not contain any
                # renewal information. To determine actual total transactions, we need to add 2 and the last part of the
                # orderid for only active states.
                order_id = verified_data.get("orderId")
                if ".." in order_id:
                    statistics_purchase.total_transactions = int(order_id.split("..")[-1]) + 2
                    LOGGER.info(
                        "Statistics subscription purchase [%s] validity remains until [%s].",
                        statistics_purchase.id,
                        expire_time,
                    )
                else:
                    LOGGER.error(
                        "Could not parse orderId [%s] for statistics purchase [%s].",
                        order_id,
                        statistics_purchase.id,
                    )
            elif notification_type in PlayStoreSubscriptionNotificationGroups.EXPIRED_TYPES:
                statistics_purchase.status = PurchaseStatus.EXPIRED.value
                LOGGER.info(
                    "Statistics subscription purchase [%s] has been expired at [%s].",
                    statistics_purchase.id,
                    expire_time,
                )
            elif notification_type in PlayStoreSubscriptionNotificationGroups.PAUSED_TYPES:
                statistics_purchase.status = PurchaseStatus.PAUSED.value
                if auto_resume_time_in_milliseconds := verified_data.get("autoResumeTimeMillis"):
                    start_time = datetime.datetime.fromtimestamp(
                        int(auto_resume_time_in_milliseconds) / 1000, tz=pytz.UTC
                    )
                LOGGER.info(
                    "Statistics subscription purchase [%s] has been paused until [%s].",
                    statistics_purchase.id,
                    start_time,
                )

            statistics_purchase.purchase_started_on = start_time
            statistics_purchase.purchase_ends_after = expire_time
            statistics_purchase.save(is_verified=True)
            PurchaseHistory.objects.create(purchase=statistics_purchase, status=statistics_purchase.status)
            LOGGER.debug(
                "Statistics subscription purchase [%s] has been updated successfully.",
                statistics_purchase.id,
            )
        else:
            LOGGER.warning(
                "Statistics subscription purchase [%s] mismatched with obfuscated account id [%s].",
                statistics_purchase.id,
                obfuscated_account_id,
            )
    else:
        LOGGER.warning(
            "Statistics subscription purchase token [%s] is not associated with any statistics purchase.",
            token,
        )


def process_statistics_purchase_app_store_notification(notification_type: str, subscription_notification: dict) -> None:
    """Processes and updates statistics purchase notification from Appstore notification server"""
    LOGGER.info("Started to process appstore statistics purchase notifications.")
    if signed_transaction_info := subscription_notification.get("data", {}).get("signedTransactionInfo"):
        transaction_id = signed_transaction_info.get("originalTransactionId")
        if statistics_purchase := StatisticsPurchase.objects.filter(
            ~Q(status=PurchaseStatus.CANCELED.value), transaction_id=transaction_id
        ).first():
            if receipt_data := get_verified_appstore_receipt_data(statistics_purchase.receipt_data):
                verified_latest_transactions = receipt_data.get("latest_receipt_info")
                app_account_token = (
                    verified_latest_transactions[0].get("app_account_token") if verified_latest_transactions else None
                )
                pending_renewal_info = receipt_data.get("pending_renewal_info")
                if (
                    verified_latest_transactions
                    and str(statistics_purchase.id) == app_account_token
                    and pending_renewal_info
                ):
                    (start_time, expire_time, expiration_intent,) = get_start_and_expiration_time_with_expire_intent(
                        pending_renewal_info[0], verified_latest_transactions[0]
                    )
                    if notification_type in AppStoreSubscriptionNotificationGroups.EXPIRED_TYPES or expiration_intent:
                        statistics_purchase.status = PurchaseStatus.EXPIRED.value
                        LOGGER.info(
                            "Statistics subscription purchase [%s] has been expired at [%s].",
                            statistics_purchase.id,
                            expire_time,
                        )
                    elif notification_type in AppStoreSubscriptionNotificationGroups.ACTIVE_TYPES:
                        statistics_purchase.status = PurchaseStatus.COMPLETED.value
                        update_total_transaction_count(statistics_purchase, notification_type)
                        LOGGER.info(
                            "Statistics subscription purchase [%s] validity remains until [%s].",
                            statistics_purchase.id,
                            expire_time,
                        )
                    statistics_purchase.purchase_started_on = start_time
                    statistics_purchase.purchase_ends_after = expire_time
                    statistics_purchase.save(is_verified=True)
                    PurchaseHistory.objects.create(purchase=statistics_purchase, status=statistics_purchase.status)
                    LOGGER.debug(
                        "Statistics subscription purchase [%s] has been updated successfully.",
                        statistics_purchase.id,
                    )
                else:
                    LOGGER.warning(
                        "Current statistics subscription purchase notification belongs to [%s] is not matched"
                        " with current one.",
                        app_account_token,
                    )
        else:
            LOGGER.warning(
                "Statistics subscription purchase transaction [%s] is not associated with any statistics purchase.",
                transaction_id,
            )


def get_verified_appstore_receipt_data(receipt_data: str) -> dict:
    """Verifies and returns Appstore subscription receipt"""
    verified_receipt_data = None
    LOGGER.info("Verifying appstore receipt data.")
    response = get_app_store_response(
        {
            "receipt-data": receipt_data,
            "password": settings.APPLE_SHARED_APP_SECRET,
            "exclude-old-transactions": True,
        }
    )
    verified_data = response.json()
    # Only invalid receipt data will contain status on response
    if verified_data.get("status"):
        LOGGER.error("Subscription purchase receipt data [%s] is unverified.", receipt_data)
    else:
        verified_receipt_data = verified_data
        LOGGER.debug("Successfully verified subscription purchase receipt data.")
    return verified_receipt_data


def get_start_and_expiration_time_with_expire_intent(
    pending_renewal_info: dict, verified_latest_transaction: dict
) -> tuple[datetime.datetime, datetime.datetime, Optional[str]]:
    """Calculates and returns start and expiration time along with expire_intent"""
    expiration_intent = None
    grace_period_expires_at = None
    start_time_in_milliseconds = verified_latest_transaction.get("purchase_date_ms")
    start_time = datetime.datetime.fromtimestamp(int(start_time_in_milliseconds) / 1000, tz=pytz.UTC)
    if pending_renewal_info:
        expiration_intent = pending_renewal_info.get("expiration_intent")
        if grace_period_expires_date_ms := pending_renewal_info.get("grace_period_expires_date_ms"):
            grace_period_expires_at = datetime.datetime.fromtimestamp(
                int(grace_period_expires_date_ms) / 1000, tz=pytz.UTC
            )
    if grace_period_expires_at:
        expire_time = grace_period_expires_at
    else:
        expire_time_in_milliseconds = verified_latest_transaction.get("expires_date_ms")
        expire_time = datetime.datetime.fromtimestamp(int(expire_time_in_milliseconds) / 1000, tz=pytz.UTC)
    return start_time, expire_time, expiration_intent


def update_total_transaction_count(
    statistics_purchase: StatisticsPurchase, notification_type: str
) -> StatisticsPurchase:
    """Calculates and sets total_transactions for statistics purchase instance from notification_type"""
    if notification_type in AppStoreSubscriptionNotificationGroups.RENEWAL_TYPES:
        statistics_purchase.total_transactions += 1
    return statistics_purchase


def generate_unified_receipt(parsed_data: dict) -> dict:
    """Generates unified notification data from parsed appstore notification data"""
    LOGGER.info("Generating unified receipt info from parsed appstore server notification")
    unified_receipt_data = {}
    parsed_data_attrs = [
        "notificationType",
        "subtype",
        "notificationUUID",
        "data",
        "version",
        "signedDate",
    ]
    for attr in parsed_data_attrs:
        if attr == "data":
            parsable_notification_data_attrs = [
                "signedTransactionInfo",
                "signedRenewalInfo",
            ]
            notification_data_attrs = [
                "bundleId",
                "bundleVersion",
                "environment",
            ] + parsable_notification_data_attrs
            notification_data = {}
            for notification_data_attr in notification_data_attrs:
                if notification_data_attr in parsable_notification_data_attrs:
                    # signedTransactionInfo and signedRenewalInfo attributes of the data are signed jwt. So we need to
                    # parse them to get actual data
                    notification_data.update(
                        {notification_data_attr: parse_jwt(parsed_data[attr][notification_data_attr])}
                    )
                else:
                    notification_data.update({notification_data_attr: parsed_data[attr][notification_data_attr]})
            unified_receipt_data.update({attr: notification_data})
        else:
            unified_receipt_data.update({attr: parsed_data.get(attr)})
    LOGGER.debug("Successfully generated unified receipt info from parsed appstore server notification")
    return unified_receipt_data


class AppstoreTransactionValidation:
    @classmethod
    def run(cls, transaction_id):
        auth_token = cls.generate_token()
        url = f"{settings.APP_STORE_CONNECT_KEY_ID}{transaction_id}"
        response = requests.get(url=url, headers={"Authorization": "Bearer " + auth_token})
        return cls.check_response(response)

    @classmethod
    def generate_token(cls):
        payload = cls.generate_payload()
        headers = {
            "alg": "ES256",
            "kid": settings.APP_STORE_CONNECT_KEY_ID,
            "typ": "JWT",
        }
        secret = settings.APP_STORE_CONNECT_SECRET_KEY
        return jwt.encode(
            payload=payload,
            key=secret,
            algorithm="ES256",
            headers=headers,
        )

    @classmethod
    def generate_payload(cls):
        return {
            "iss": settings.APP_STORE_CONNECT_ISSUER_ID,
            "iat": cls.generate_issued_at(),
            "exp": cls.generate_expires_at(),
            "aud": "appstoreconnect-v1",
            "bid": settings.APP_STORE_CONNECT_BUNDLE_ID,
        }

    @staticmethod
    def generate_issued_at():
        return time.mktime(datetime.datetime.now().timetuple())

    @staticmethod
    def generate_expires_at():
        date = datetime.datetime.now() + datetime.timedelta(minutes=60)
        return time.mktime(date.timetuple())

    @classmethod
    def check_response(cls, response):
        response = cls.decode_response(response)
        expires_at = response.get("expiresDate")
        expires_at = datetime.datetime.fromtimestamp(expires_at / 1000.0)
        now = datetime.datetime.now()
        return now < expires_at

    @classmethod
    def decode_response(cls, response):
        response = response.json()
        jwt_token = response.get("signedTransactionInfo")
        header, payload, signature = jwt_token.split(".")
        decoded_payload = base64.urlsafe_b64decode(payload + "===").decode("utf-8")
        return json.loads(decoded_payload)
