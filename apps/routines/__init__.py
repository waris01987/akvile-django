from typing import Dict, Union

from apps.utils.enums import ChoicesEnum


class RoutineType(str, ChoicesEnum):
    AM = "AM"
    PM = "PM"


class FeelingToday(str, ChoicesEnum):
    LOVE_IT = "LOVE_IT"
    WELL = "WELL"
    MEHHH = "MEHHH"
    BAD = "BAD"


class SleepQuality(str, ChoicesEnum):
    LOVE_IT = "LOVE_IT"
    WELL = "WELL"
    MEHHH = "MEHHH"
    BAD = "BAD"


class SomethingSpecial(str, ChoicesEnum):
    MENSTRUATION = "MENSTRUATION"
    SHAVING = "SHAVING"
    VACATION = "VACATION"
    MEET_DR = "MEET_DR"
    START_DRUG_TREATMENT = "START_DRUG_TREATMENT"
    ALLERGIE = "ALLERGIE"


class SkinFeel(str, ChoicesEnum):
    NORMAL = "NORMAL"
    SENSITIVE = "SENSITIVE"
    DEHYDRATED = "DEHYDRATED"
    GREASY = "GREASY"


class DietBalance(str, ChoicesEnum):
    BALANCED = "BALANCED"
    MILDLY_BALANCED = "MILDLY_BALANCED"
    UNBALANCED = "UNBALANCED"


class StressLevel(str, ChoicesEnum):
    RELAXED = "RELAXED"
    MODERATE = "MODERATE"
    EXTREME = "EXTREME"


class LifeHappened(str, ChoicesEnum):
    COFFEE = "COFFEE"
    ALCOHOL = "ALCOHOL"
    JUNK_FOOD_AND_SWEETS = "JUNK_FOOD_AND_SWEETS"
    SMOKING = "SMOKING"
    INNOCENT = "INNOCENT"


class ProductType(str, ChoicesEnum):
    CLEANSER = "CLEANSER"
    MOISTURIZER = "MOISTURIZER"
    TREATMENT = "TREATMENT"


class ExerciseHours(str, ChoicesEnum):
    TWO_PLUS = "TWO_PLUS"
    TWO_HOURS = "TWO_HOURS"
    ONE_AND_A_HALF_HOURS = "ONE_AND_A_HALF_HOURS"
    ONE_HOUR = "ONE_HOUR"
    FORTY_FIVE_MIN = "FORTY_FIVE_MIN"
    THIRTY_MIN = "THIRTY_MIN"
    TWENTY_MIN = "TWENTY_MIN"
    ZERO = "ZERO"


class FaceScanNotificationTypes(str, ChoicesEnum):
    INVALID = "INVALID"
    SUCCESS = "SUCCESS"


PUSH_NOTIFICATION_TYPE_TO_CLICK_ACTION_LINK = {
    FaceScanNotificationTypes.INVALID: "face-scan-camera",
    FaceScanNotificationTypes.SUCCESS: "face-scan-results",
}

# Points chart for various attributes and their corresponding values for the daily statistics.
# Keys of the points are from `DailyQuestionnaire` model and values are from allowed values for those model attributes.
# Some values from the `DailyQuestionnaire` is not present here because they have no effect on points counting.
# For detail reference of the point distribution, please visit the following link:
# https://xd.adobe.com/view/d87117ca-cdc4-4b8b-bd53-7a206a39eca8-8d22/
# Please update points if it is changed in the reference. And if any field is renamed or removed from the
# `DailyQuestionnaire` then please update this POINTS table accordingly.

POINTS: Dict[str, Dict[Union[str, int], int]] = {
    "skin_feel": {
        SkinFeel.SENSITIVE: 10,
        SkinFeel.GREASY: 10,
        SkinFeel.DEHYDRATED: 10,
        SkinFeel.NORMAL: 25,
    },
    "diet_today": {
        DietBalance.UNBALANCED: 5,
        DietBalance.MILDLY_BALANCED: 15,
        DietBalance.BALANCED: 50,
    },
    "water": {0: 0, 1: 10, 2: 20, 3: 25},
    "life_happened": {
        LifeHappened.ALCOHOL: 5,
        LifeHappened.JUNK_FOOD_AND_SWEETS: 5,
        LifeHappened.COFFEE: 10,
        LifeHappened.INNOCENT: 25,
    },
    "stress_levels": {
        StressLevel.EXTREME: 5,
        StressLevel.MODERATE: 15,
        StressLevel.RELAXED: 25,
    },
    "exercise_hours": {
        ExerciseHours.ZERO: 0,
        ExerciseHours.TWENTY_MIN: 10,
        ExerciseHours.THIRTY_MIN: 20,
        ExerciseHours.FORTY_FIVE_MIN: 20,
        ExerciseHours.ONE_HOUR: 25,
        ExerciseHours.ONE_AND_A_HALF_HOURS: 25,
        ExerciseHours.TWO_HOURS: 25,
        ExerciseHours.TWO_PLUS: 25,
    },
    "feeling_today": {
        FeelingToday.BAD: 5,
        FeelingToday.MEHHH: 10,
        FeelingToday.WELL: 20,
        FeelingToday.LOVE_IT: 25,
    },
    "hours_of_sleep": {
        0: 5,
        1: 5,
        2: 5,
        3: 5,
        4: 5,
        5: 5,
        6: 10,
        7: 10,
        8: 25,
        9: 25,
        10: 20,
        11: 20,
        12: 20,
        13: 20,
        14: 20,
    },
    "sleep_quality": {
        SleepQuality.BAD: 5,
        SleepQuality.MEHHH: 10,
        SleepQuality.WELL: 20,
        SleepQuality.LOVE_IT: 25,
    },
}


class RoutinePoints(int, ChoicesEnum):
    AM_ROUTINE_POINT = 25
    PM_ROUTINE_POINT = 25


class DailyRoutineCountStatus(str, ChoicesEnum):
    NOT_COUNTED = "NOT_COUNTED"
    ONLY_AM_COUNTED = "ONLY_AM_COUNTED"
    ONLY_PM_COUNTED = "ONLY_PM_COUNTED"
    COUNTING_COMPLETED = "COUNTING_COMPLETED"


class PredictionTypes(str, ChoicesEnum):
    NO_PREDICTION = "NO_PREDICTION"
    ROUTINE_SKIPPED = "ROUTINE_SKIPPED"
    ROUTINE_MISSED = "ROUTINE_MISSED"
    ROUTINE_DONE = "ROUTINE_DONE"
    SKIN_TODAY_BAD_OR_MEHHH = "SKIN_TODAY_BAD_OR_MEHHH"
    SKIN_TODAY_LOVE_IT = "SKIN_TODAY_LOVE_IT"
    SKIN_TODAY_WELL = "SKIN_TODAY_WELL"
    SKIN_FEELING_SENSITIVE = "SKIN_FEELING_SENSITIVE"
    SKIN_FEELING_GREASY = "SKIN_FEELING_GREASY"
    SKIN_FEELING_NORMAL = "SKIN_FEELING_NORMAL"
    SKIN_FEELING_DEHYDRATED = "SKIN_FEELING_DEHYDRATED"
    SLEEP_HOURS_LESS_THAN_SEVEN = "SLEEP_HOURS_LESS_THAN_SEVEN"
    SLEEP_HOURS_GREATER_EQUAL_SEVEN = "SLEEP_HOURS_GREATER_EQUAL_SEVEN"
    SLEEP_QUALITY_BAD_OR_MEHHH = "SLEEP_QUALITY_BAD_OR_MEHHH"
    SLEEP_QUALITY_WELL_OR_LOVE_IT = "SLEEP_QUALITY_WELL_OR_LOVE_IT"
    EXERCISE_HOURS_BAD = "EXERCISE_HOURS_BAD"
    EXERCISE_HOURS_GOOD = "EXERCISE_HOURS_GOOD"
    EXERCISE_HOURS_PERFECT = "EXERCISE_HOURS_PERFECT"
    STRESS_EXTREME = "STRESS_EXTREME"
    STRESS_MODERATE = "STRESS_MODERATE"
    STRESS_RELAXED = "STRESS_RELAXED"
    DIET_BALANCED = "DIET_BALANCED"
    DIET_UNBALANCED_or_MILDLY_BALANCED = "DIET_UNBALANCED_or_MILDLY_BALANCED"
    WATER_INTAKE_ZERO_OR_ONE = "WATER_INTAKE_ZERO_OR_ONE"
    WATER_INTAKE_TWO_OR_THREE = "WATER_INTAKE_TWO_OR_THREE"
    LIFE_HAPPENED_COFFEE_OR_ALCOHOL_OR_JUNK_FOOD = "LIFE_HAPPENED_COFFEE_OR_ALCOHOL_OR_JUNK_FOOD"
    MENSTRUATION_FOLLICULAR = "MENSTRUATION_FOLLICULAR"
    MENSTRUATION_DURING = "MENSTRUATION_DURING"
    MENSTRUATION_OVULATION = "MENSTRUATION_OVULATION"
    MENSTRUATION_LUTEAL = "MENSTRUATION_LUTEAL"
    DAILY_QUESTIONNAIRE_SKIPPED = "DAILY_QUESTIONNAIRE_SKIPPED"


class PredictionCategories:
    ROUTINE_TYPES = [
        PredictionTypes.ROUTINE_SKIPPED,
        PredictionTypes.ROUTINE_MISSED,
        PredictionTypes.ROUTINE_DONE,
    ]
    SKIN_TODAY_TYPES = [
        PredictionTypes.SKIN_TODAY_BAD_OR_MEHHH,
        PredictionTypes.SKIN_TODAY_WELL,
        PredictionTypes.SKIN_TODAY_LOVE_IT,
    ]
    SKIN_FEELING_TYPES = [
        PredictionTypes.SKIN_FEELING_SENSITIVE,
        PredictionTypes.SKIN_FEELING_GREASY,
        PredictionTypes.SKIN_FEELING_NORMAL,
        PredictionTypes.SKIN_FEELING_DEHYDRATED,
    ]
    SLEEP_HOURS_TYPES = [
        PredictionTypes.SLEEP_HOURS_LESS_THAN_SEVEN,
        PredictionTypes.SLEEP_HOURS_GREATER_EQUAL_SEVEN,
    ]
    SLEEP_QUALITY_TYPES = [
        PredictionTypes.SLEEP_QUALITY_BAD_OR_MEHHH,
        PredictionTypes.SLEEP_QUALITY_WELL_OR_LOVE_IT,
    ]
    EXERCISE_HOURS_TYPES = [
        PredictionTypes.EXERCISE_HOURS_BAD,
        PredictionTypes.EXERCISE_HOURS_GOOD,
        PredictionTypes.EXERCISE_HOURS_PERFECT,
    ]
    STRESS_TYPES = [
        PredictionTypes.STRESS_EXTREME,
        PredictionTypes.STRESS_MODERATE,
        PredictionTypes.STRESS_RELAXED,
    ]
    DIET_TYPES = [
        PredictionTypes.DIET_UNBALANCED_or_MILDLY_BALANCED,
        PredictionTypes.DIET_BALANCED,
    ]
    WATER_INTAKE_TYPES = [
        PredictionTypes.WATER_INTAKE_ZERO_OR_ONE,
        PredictionTypes.WATER_INTAKE_TWO_OR_THREE,
    ]
    LIFE_HAPPENED_TYPES = [
        PredictionTypes.LIFE_HAPPENED_COFFEE_OR_ALCOHOL_OR_JUNK_FOOD,
    ]
    MENSTRUATION_TYPES = [
        PredictionTypes.MENSTRUATION_FOLLICULAR,
        PredictionTypes.MENSTRUATION_DURING,
        PredictionTypes.MENSTRUATION_OVULATION,
        PredictionTypes.MENSTRUATION_LUTEAL,
    ]
    DAILY_QUESTIONNAIRE_TYPES = [
        PredictionTypes.DAILY_QUESTIONNAIRE_SKIPPED,
    ]


class RecommendationCategory(str, ChoicesEnum):
    ACNE = "ACNE"
    PIGMENTATION = "PIGMENTATION"
    UNIFORMNESS = "UNIFORMNESS"
    HYDRATION = "HYDRATION"
    PORES = "PORES"
    REDNESS = "REDNESS"


class TagCategories(str, ChoicesEnum):
    SKIN_CARE = "SKIN_CARE"
    WELL_BEING = "WELL_BEING"
    NUTRITION = "NUTRITION"
    MEDICATION = "MEDICATION"
    APPOINTMENT = "APPOINTMENT"
    MENSTRUATION = "MENSTRUATION"


class HealthCareEventTypes(str, ChoicesEnum):
    MEDICATION = "MEDICATION"
    APPOINTMENT = "APPOINTMENT"
    MENSTRUATION = "MENSTRUATION"


class MedicationTypes(str, ChoicesEnum):
    PILL = "PILL"
    SKIN = "SKIN"


class SkinTrendCategories(str, ChoicesEnum):
    ADVANCED = "ADVANCED"
    INTERMEDIATE = "INTERMEDIATE"
    BEGINNER = "BEGINNER"


class PurchaseStatus(str, ChoicesEnum):
    STARTED = "STARTED"
    CANCELED = "CANCELED"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"


class AppStores(str, ChoicesEnum):
    APP_STORE = "APP_STORE"
    PLAY_STORE = "PLAY_STORE"


class PlayStoreSubscriptionNotificationTypes(int, ChoicesEnum):
    SUBSCRIPTION_RECOVERED = 1
    SUBSCRIPTION_RENEWED = 2
    SUBSCRIPTION_CANCELED = 3
    SUBSCRIPTION_PURCHASED = 4
    SUBSCRIPTION_ON_HOLD = 5
    SUBSCRIPTION_IN_GRACE_PERIOD = 6
    SUBSCRIPTION_RESTARTED = 7
    SUBSCRIPTION_PRICE_CHANGE_CONFIRMED = 8
    SUBSCRIPTION_DEFERRED = 9
    SUBSCRIPTION_PAUSED = 10
    SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED = 11
    SUBSCRIPTION_REVOKED = 12
    SUBSCRIPTION_EXPIRED = 13


# Categorised subscription purchase status based on following reference:
# https://developer.android.com/google/play/billing/rtdn-reference
class PlayStoreSubscriptionNotificationGroups:
    ACTIVE_TYPES = [
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_PURCHASED,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_RENEWED,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_RECOVERED,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_RESTARTED,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_PRICE_CHANGE_CONFIRMED,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_IN_GRACE_PERIOD,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_DEFERRED,
    ]
    EXPIRED_TYPES = [
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_CANCELED,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_EXPIRED,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_ON_HOLD,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_REVOKED,
    ]
    PAUSED_TYPES = [
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_PAUSED,
        PlayStoreSubscriptionNotificationTypes.SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED,
    ]


# Server push notification version 2 types are collected from the following reference:
# https://developer.apple.com/documentation/appstoreservernotifications/notificationtype
class AppStoreSubscriptionNotificationTypes(str, ChoicesEnum):
    CONSUMPTION_REQUEST = "CONSUMPTION_REQUEST"
    DID_CHANGE_RENEWAL_PREF = "DID_CHANGE_RENEWAL_PREF"
    DID_CHANGE_RENEWAL_STATUS = "DID_CHANGE_RENEWAL_STATUS"
    DID_FAIL_TO_RENEW = "DID_FAIL_TO_RENEW"
    DID_RENEW = "DID_RENEW"
    EXPIRED = "EXPIRED"
    GRACE_PERIOD_EXPIRED = "GRACE_PERIOD_EXPIRED"
    OFFER_REDEEMED = "OFFER_REDEEMED"
    PRICE_INCREASE = "PRICE_INCREASE"
    REFUND = "REFUND"
    REFUND_DECLINED = "REFUND_DECLINED"
    RENEWAL_EXTENDED = "RENEWAL_EXTENDED"
    REVOKE = "REVOKE"
    SUBSCRIBED = "SUBSCRIBED"
    TEST = "TEST"


# Categorised subscription purchase status based on following reference:
# https://developer.apple.com/documentation/appstoreservernotifications/notificationtype
class AppStoreSubscriptionNotificationGroups:
    ACTIVE_TYPES = [
        AppStoreSubscriptionNotificationTypes.DID_CHANGE_RENEWAL_PREF,
        AppStoreSubscriptionNotificationTypes.DID_CHANGE_RENEWAL_STATUS,
        AppStoreSubscriptionNotificationTypes.DID_FAIL_TO_RENEW,
        AppStoreSubscriptionNotificationTypes.DID_RENEW,
        AppStoreSubscriptionNotificationTypes.OFFER_REDEEMED,
        AppStoreSubscriptionNotificationTypes.PRICE_INCREASE,
        AppStoreSubscriptionNotificationTypes.REFUND_DECLINED,
        AppStoreSubscriptionNotificationTypes.RENEWAL_EXTENDED,
        AppStoreSubscriptionNotificationTypes.SUBSCRIBED,
    ]
    EXPIRED_TYPES = [
        AppStoreSubscriptionNotificationTypes.EXPIRED,
        AppStoreSubscriptionNotificationTypes.GRACE_PERIOD_EXPIRED,
        AppStoreSubscriptionNotificationTypes.REFUND,
        AppStoreSubscriptionNotificationTypes.REVOKE,
    ]
    RENEWAL_TYPES = [
        AppStoreSubscriptionNotificationTypes.DID_RENEW,
        AppStoreSubscriptionNotificationTypes.SUBSCRIBED,
        AppStoreSubscriptionNotificationTypes.OFFER_REDEEMED,
    ]
