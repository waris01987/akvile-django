import base64
import datetime
import logging
import random
from typing import Union

from django.db.models.signals import post_save
from django.utils import timezone

from apps.routines import (
    POINTS,
    RoutineType,
    DailyRoutineCountStatus,
    RoutinePoints,
)
from apps.routines.haut_ai import get_auth_info, get_subject_id, upload_picture
from apps.routines.models import (
    FaceScan,
    DailyQuestionnaire,
    DailyStatistics,
    Routine,
    Prediction,
)
from apps.routines.predictions import (
    get_routine_prediction,
    get_other_predictions,
    get_daily_questionnaire_prediction,
    get_menstruation_prediction,
)

LOGGER = logging.getLogger("app")


def upload_image_to_haut_ai(sender, instance, created, **kwargs):
    """
    Upload image to haut.ai service after creation
    """

    if created and instance.image:
        company_id, token = get_auth_info()

        if not instance.user.haut_ai_subject_id:
            instance.user.haut_ai_subject_id = get_subject_id(
                subject_name=instance.user.id, company_id=company_id, token=token
            )
            instance.user.save()
        batch_id, image_id = upload_picture(
            subject_id=instance.user.haut_ai_subject_id,
            image_base64=base64.b64encode(instance.image.file.read()).decode(),
            company_id=company_id,
            token=token,
        )
        instance.haut_ai_batch_id = batch_id
        instance.haut_ai_image_id = image_id
        instance.save()


def calculate_daily_statistics(sender, instance, created, **kwargs):
    """
    This function calculates and creates daily statistics based on DailyQuestionnaires. While creating the
    `DailyQuestionnaire` for a user, it calculates and creates `DailyStatistics`. During the calculation of the points,
    we divided all the attributes of the  `DailyQuestionnaire` to three different sections, and they are-
        1. skin care:
            a. skin_feel
            b. feeling_today
            c. routines
        2. well-being:
            a. hours_of_sleep
            b. sleep_quality
            c. exercise_hours
            d. stress_levels
        3. nutrition:
            a. diet_today
            b. water
            c. life_happened
    To calculate total points we're using `POINTS` as the reference for different attributes and their values.
    While calculating skin care points, we need to consider two things- 1. total routines
    and 2. Points based on values of skin care attributes.
    Sometimes user may have one routine, two routines or no routines at all. To track, how many routines were counted,
    we're using a flag `routine_count_status` which will be considered later if user creates daily routine and
    skin care points will be updated accordingly.
    """
    # am/pm routine points are set according to
    # `https://xd.adobe.com/view/d87117ca-cdc4-4b8b-bd53-7a206a39eca8-8d22`
    total_earned_routine_points = 0
    current_date = instance.created_at.date()
    today_routines = instance.user.routines.filter(created_at__date=current_date)
    has_today_am_routines = today_routines.filter(routine_type=RoutineType.AM).exists()
    has_today_pm_routines = today_routines.filter(routine_type=RoutineType.PM).exists()

    # calculating skin care routine points and setting `routine_count_status` accordingly
    if has_today_am_routines and has_today_pm_routines:
        total_earned_routine_points = RoutinePoints.AM_ROUTINE_POINT + RoutinePoints.PM_ROUTINE_POINT
        routine_count_status = DailyRoutineCountStatus.COUNTING_COMPLETED
    elif has_today_am_routines:
        total_earned_routine_points = RoutinePoints.AM_ROUTINE_POINT
        routine_count_status = DailyRoutineCountStatus.ONLY_AM_COUNTED
    elif has_today_pm_routines:
        total_earned_routine_points = RoutinePoints.PM_ROUTINE_POINT
        routine_count_status = DailyRoutineCountStatus.ONLY_PM_COUNTED
    else:
        routine_count_status = DailyRoutineCountStatus.NOT_COUNTED

    skin_care_attrs = ["skin_feel", "feeling_today"]
    well_being_attrs = [
        "stress_levels",
        "exercise_hours",
        "hours_of_sleep",
        "sleep_quality",
    ]
    nutrition_attrs = ["diet_today", "water", "life_happened"]

    skin_care_points_without_routines = _calculate_points(instance, skin_care_attrs)
    skin_care_points = skin_care_points_without_routines + total_earned_routine_points
    well_being_points = _calculate_points(instance, well_being_attrs)
    nutrition_points = _calculate_points(instance, nutrition_attrs)

    DailyStatistics.objects.update_or_create(
        user=instance.user,
        date=current_date,
        defaults={
            "skin_care": skin_care_points,
            "well_being": well_being_points,
            "nutrition": nutrition_points,
            "routine_count_status": routine_count_status,
        },
    )


def update_daily_statistics_for_routine(sender, instance, created, **kwargs):
    """
    This function updates already calculated `DailyStatistics` after `Routine` creation. If the `routine_count_status`
    attribute of the `DailyStatistics` is `COUNTING_COMPLETED` then it has no effect otherwise it updates skin care
    points and `routine_count_status` accordingly.
    """
    # AM/PM routine points are set according to this reference:
    # `https://xd.adobe.com/view/d87117ca-cdc4-4b8b-bd53-7a206a39eca8-8d22`
    routine_point = RoutinePoints.AM_ROUTINE_POINT
    today = datetime.datetime.now(datetime.timezone.utc)
    daily_statistics = instance.user.daily_statistics.filter(date=today.date()).first()
    if daily_statistics and created:
        if daily_statistics.routine_count_status != DailyRoutineCountStatus.COUNTING_COMPLETED:
            if instance.routine_type == RoutineType.AM and daily_statistics.routine_count_status in [
                DailyRoutineCountStatus.NOT_COUNTED,
                DailyRoutineCountStatus.ONLY_PM_COUNTED,
            ]:
                daily_statistics.skin_care += routine_point
                if daily_statistics.routine_count_status == DailyRoutineCountStatus.ONLY_PM_COUNTED:
                    daily_statistics.routine_count_status = DailyRoutineCountStatus.COUNTING_COMPLETED
                else:
                    daily_statistics.routine_count_status = DailyRoutineCountStatus.ONLY_AM_COUNTED

            if instance.routine_type == RoutineType.PM and daily_statistics.routine_count_status in [
                DailyRoutineCountStatus.NOT_COUNTED,
                DailyRoutineCountStatus.ONLY_AM_COUNTED,
            ]:
                daily_statistics.skin_care += routine_point
                if daily_statistics.routine_count_status == DailyRoutineCountStatus.ONLY_AM_COUNTED:
                    daily_statistics.routine_count_status = DailyRoutineCountStatus.COUNTING_COMPLETED
                else:
                    daily_statistics.routine_count_status = DailyRoutineCountStatus.ONLY_PM_COUNTED
            daily_statistics.save()


def _calculate_points(instance: DailyQuestionnaire, attrs: list[str]) -> int:
    """Calculates total points from an object and the given list of attributes"""
    total = 0
    for attr in attrs:
        value = getattr(instance, attr)
        if isinstance(value, list):
            # Some attrs could contain list of items
            values = []
            for item in value:
                if points := get_points(attr, item):
                    values.append(points)
            if values:
                total += min(values)
        else:
            total += get_points(attr, value)
    return total


def get_points(attr: str, item: Union[str, int]) -> int:
    """Returns points from the point chart"""
    if attr not in POINTS:
        LOGGER.exception(f"Key [{attr}] not found in POINTS table.")
        return 0

    if item not in POINTS[attr]:
        LOGGER.exception(f"Key [{item}] not found in POINTS table [{attr}] section.")
        return 0
    return POINTS[attr][item]


def calculate_prediction_based_on_statistics(sender, instance, created, **kwargs):
    """
    This function calculates various types of predictions from the user input as the form of `DailyQuestionnaire`.
    Predictions start being calculated one week after user starts the main Onboarding Questionnaire.

    Here, we mainly categorize four types of prediction based on `DailyQuestionnaire` and `Routine`. According to
    business logic, there are a priority for categories:
    1. Menstruation prediction (if user is having related phases)
    2. Other predictions (based on Daily questionnaire answers where 3 consecutive answers for the same question
    will be considered).
    3. Daily questionnaire prediction (if user skips 3 Daily Qs in a row during a 7 day period)
    4. Routine prediction - we need to consider weekly total number of routines that user completed.

    We can not show the same type of prediction for two consecutive predictions.
    """
    current_time = timezone.now()
    predictions_unlock_at = instance.user.questionnaire.created_at + datetime.timedelta(weeks=1)
    is_unlocked = current_time > predictions_unlock_at
    if not created or not is_unlocked:
        return
    final_prediction_type = None
    current_date = instance.date
    last_two_predictions = instance.user.predictions.filter(date__lt=current_date)[:2]
    last_two_prediction_types = [prediction.prediction_type for prediction in last_two_predictions]
    if menstruation_prediction_type := get_menstruation_prediction(instance, last_two_prediction_types):
        final_prediction_type = menstruation_prediction_type
    elif other_prediction_types := get_other_predictions(instance, last_two_prediction_types):
        # we choose a random prediction type from calculated list of prediction types based on user inputs
        final_prediction_type = random.choice(other_prediction_types)  # noqa: S311
    elif daily_questionnaire_prediction_type := get_daily_questionnaire_prediction(instance):
        final_prediction_type = daily_questionnaire_prediction_type
    elif routine_prediction_type := get_routine_prediction(instance):
        final_prediction_type = routine_prediction_type

    # Creates prediction only if we get a prediction type based on user input. We are considering only create even
    # though sometimes user might create daily routines after creating `DailyQuestionnaire`. In that situation, we will
    # recalculate the DailyStatistics, but will not change the prediction which was already shown to the user.
    if final_prediction_type:
        Prediction.objects.create(user=instance.user, date=current_date, prediction_type=final_prediction_type)


post_save.connect(upload_image_to_haut_ai, sender=FaceScan)

post_save.connect(calculate_daily_statistics, sender=DailyQuestionnaire)

post_save.connect(update_daily_statistics_for_routine, sender=Routine)

post_save.connect(calculate_prediction_based_on_statistics, sender=DailyStatistics)
