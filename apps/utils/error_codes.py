from apps.utils.enums import ChoicesEnum


class Errors(str, ChoicesEnum):
    BAD_CREDENTIALS = "error_login_bad_credentials"
    COMMON_PASSWORD_VALIDATION = "error_password_too_common"  # noqa S105
    EMAIL_REQUIRED = "error_email_is_a_required_field"
    EXERCISE_DAYS_VALUE = "error_exercise_days_value_has_to_be_between_1_and_7"
    FIELD_IS_REQUIRED = "error_field_is_required"
    FUTURE_DATE_NOT_ALLOWED = "error_future_date_not_allowed"
    HOURS_OF_SLEEP_VALUE = "error_hours_of_sleep_value_has_to_be_between_1_and_14"
    INVALID_APP_VERSION_VALUE = "error_invalid_app_version_value"
    INVALID_EMAIL = "error_invalid_email"
    MALE_CAN_NOT_BE_A_MENSTRUATING_PERSON = "error_male_cannot_be_a_menstruating_person"
    MENSTRUATING_PERSON_HAS_TO_PROVIDE_A_CONTRACEPTIVE_PILL_ANSWER = (
        "error_menstruating_person_has_to_provide_a_contraceptive_pill_answer"
    )
    MENSTRUATING_PERSON_DOES_NOT_HAVE_SHAVING_OPTION = "error_menstruating_person_does_not_have_shaving_option"
    MENSTRUATING_PERSON_HAS_TO_PROVIDE_A_POWER_DATE = "error_menstruating_person_has_to_have_a_power_date"
    MINIMUM_LENGTH_VALIDATION = "error_password_too_short"
    NEW_EMAIL_SAME_AS_OLD_ONE = "error_new_email_same_as_old_one"
    NOT_MENSTRUATING_PERSON_WITH_MENSTRUATING_PERSONS_ANSWERS = (
        "error_not_menstruating_person_with_menstruating_persons_answers"
    )
    NO_SUCH_LANGUAGE = "error_no_such_language"
    NUMERIC_PASSWOD_VALIDATION = "error_password_entirely_numeric"  # noqa S105
    PARTIAL_UPDATE_DISABLED = "error_partial_update_for_the_main_user_questionnaire_is_disabled"
    PASSWORDS_NOT_EQUAL = "error_passwords_not_equal"
    PASSWORD_IS_INCORRECT = "error_password_is_incorrect"  # noqa S105
    QUESTIONNAIRE_ALREADY_EXISTS_FOR_THIS_USER = "error_questionnaire_already_exists_for_this_user"
    USER_HAS_NO_USER_QUESTIONNAIRE = "error_user_has_no_user_questionnaire"
    RESET_PASSWORD_KEY_EXPIRED = "error_reset_password_key_expired"  # noqa S105
    THIS_PERSON_DOES_NOT_USE_MAKEUP = "error_this_person_does_not_use_make_up"
    USER_ALREADY_VERIFIED = "error_verify_already_verified"
    USER_ATRIBUTE_SIMILARITY_VALIDATION = "error_password_too_similar_to_email"
    USER_DATETIME_CLAIM_CHANGED = "error_user_datetime_claim_changed"
    USER_DOES_NOT_EXIST = "error_user_does_not_exist"
    USER_DOES_NOT_HAVE_FIRST_OR_LAST_NAME_SET = "error_this_user_does_not_have_first_or_last_name_set"
    USER_EMAIL_NOT_VERIFIED = "error_login_user_email_not_verified"
    USER_IS_NOT_ACTIVE = "error_user_is_not_active"
    EMAIL_ALREADY_EXISTS = "error_email_already_exists"
    DUPLICATE_PRODUCT_TYPE = "errors_duplicate_product_type"
    PRODUCT_GROUP_ALREADY_EXISTS = "errors_product_group_already_exists"
    PRODUCT_GROUP_DOESNT_EXIST = "errors_user_doesnt_have_product_group"
    INCORRECT_TERMS_OF_SERVICE_VERSION = "error_terms_of_service_version"
    INCORRECT_PRIVACY_POLICY_VERSION = "error_privacy_policy_version"
    USER_CAN_HAVE_ONE_RECOMMENDATION_PER_CATEGORY = "error_user_can_have_one_recommendation_per_category"
    CURRENT_INDEX_CANT_MATCH_PREVIOUS_INDEXES = "error_current_index_cant_match_previous_indexes"
    PREVIOUS_INDEXES_CAN_ONLY_BE_RESET = "error_previous_indexes_can_only_be_reset"
    MULTIPLE_FEATURED_RECOMMENDATIONS = "error_duplicate_featured_recommendations"
    DUPLICATE_RECOMMENDATION_CATEGORIES = "error_duplicate_recommendation_categories"
    SOCIAL_AUTH_MISSING_EMAIL = "error_missing_permission_to_retrieve_email"
    INNOCENT_PERSON_CAN_NOT_SELECT_MULTIPLE_LIFE_HAPPENED_ANSWERS = (
        "error_innocent_person_with_multiple_life_happened_answers"
    )
    TAG_NAME_ALREADY_EXISTS_FOR_SAME_CATEGORY = "error_tag_name_already_exists_for_same_category"
    INVALID_MEDICATION_EVENT = "error_invalid_medication_event"
    INVALID_APPOINTMENT_EVENT = "error_invalid_appointment_event"
    INVALID_MENSTRUATION_EVENT = "error_invalid_menstruation_event"
    APPOINTMENT_EVENT_ALREADY_EXISTS_FOR_SAME_DATE_TIME = "error_appointment_event_already_exists_for_same_date_time"
    FUTURE_MONTH_SELECTED_FOR_MONTHLY_PROGRESS = "error_future_month_selected_for_monthly_progress"
    USER_ALREADY_PURCHASED_STATISTICS = "error_user_already_purchased_statistics"
    INVALID_STATISTICS_PURCHASE_TO_CANCEL = "error_invalid_statistics_purchase_to_cancel"
    INVALID_STATISTICS_PURCHASE_TO_COMPLETE = "error_invalid_statistics_purchase_to_complete"
    PURCHASE_PAYMENT_IS_NOT_YET_RECEIVED = "error_purchase_payment_is_not_yet_received"
    UNEXPECTED_ERROR_FROM_APP_STORE = "error_unexpected_error_from_app_store"
    UNEXPECTED_ERROR_FROM_PLAY_STORE = "error_unexpected_error_from_play_store"
    NO_PURCHASE_IN_RECEIPT = "error_no_purchase_in_receipt"
    SUBSCRIPTION_PURCHASE_WAS_CANCELLED = "error_subscription_purchase_was_cancelled"
    NO_APP_ACCOUNT_TOKEN_FOUND = "error_no_app_account_token_found"  # noqa S105
    NO_OBFUSCATED_ACCOUNT_ID_FOUND = "error_no_obfuscated_account_id_found"
    PURCHASE_TOKEN_BELONGS_TO_OTHER_USER = "error_purchase_token_belongs_to_other_user"  # noqa S105
    NO_IMAGE_PROVIDED = "no_image_provided"
    FAILED_TO_PARSE_IMAGE = "failed_to_parse_image"
