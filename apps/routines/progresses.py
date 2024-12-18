import calendar
from collections import Counter
import datetime

from django.conf import settings
from django.db.models import Q, Count, Prefetch, QuerySet
from django.utils import timezone

from apps.home.models import PredictionTemplateTranslation
from apps.routines import (
    DietBalance,
    ExerciseHours,
    FeelingToday,
    POINTS,
    PredictionCategories,
    PredictionTypes,
    RoutineType,
    SkinFeel,
    SkinTrendCategories,
    SleepQuality,
    StressLevel,
    TagCategories,
)
from apps.routines.models import DailyQuestionnaire, Routine, UserTag, FaceScanAnalytics
from apps.routines.signals import get_points
from apps.users.models import User

# Monthly recommendation according to business logic
recommendation_types: dict[str, str] = {
    SkinFeel.SENSITIVE.value: PredictionTypes.SKIN_FEELING_SENSITIVE.value,
    SkinFeel.GREASY.value: PredictionTypes.SKIN_FEELING_GREASY.value,
    SkinFeel.DEHYDRATED.value: PredictionTypes.SKIN_FEELING_DEHYDRATED.value,
    SkinFeel.NORMAL.value: PredictionTypes.SKIN_FEELING_NORMAL.value,
    FeelingToday.BAD.value: PredictionTypes.SKIN_TODAY_BAD_OR_MEHHH.value,
    FeelingToday.MEHHH.value: PredictionTypes.SKIN_TODAY_BAD_OR_MEHHH.value,
    FeelingToday.WELL.value: PredictionTypes.SKIN_TODAY_WELL.value,
    FeelingToday.LOVE_IT.value: PredictionTypes.SKIN_TODAY_LOVE_IT.value,
    PredictionTypes.ROUTINE_SKIPPED.value: PredictionTypes.ROUTINE_SKIPPED.value,
    PredictionTypes.ROUTINE_MISSED.value: PredictionTypes.ROUTINE_MISSED.value,
    PredictionTypes.ROUTINE_DONE.value: PredictionTypes.ROUTINE_DONE.value,
}


# TODO: Need to think last 5 common answers


def generate_monthly_progress(start_date: datetime.date, end_date: datetime.date, user: User) -> dict:
    """Generates and returns monthly progress for the specified date range for a specific user"""
    current_months_data = generate_current_months_progress(start_date, end_date, user)
    end_of_previous_month = start_date - datetime.timedelta(days=1)
    start_of_previous_month = end_of_previous_month.replace(day=1)
    previous_months_data = generate_previous_months_progress(start_of_previous_month, end_of_previous_month, user)
    return compare_and_update_monthly_progresses(current_months_data, previous_months_data)


def generate_current_months_progress(start_date: datetime.date, end_date: datetime.date, user: User) -> dict:
    """Generates user's current month's data for a user from provided start and end date"""
    user_filters = Q(user=user) | Q(user=None)
    skin_care_tag_filters = user_filters & Q(category=TagCategories.SKIN_CARE.value)
    well_being_tag_filters = user_filters & Q(category=TagCategories.WELL_BEING.value)
    nutrition_tag_filters = user_filters & Q(category=TagCategories.NUTRITION.value)

    skin_care_prefetch = Prefetch(
        "tags_for_skin_care",
        queryset=UserTag.objects.filter(skin_care_tag_filters),
        to_attr="skin_care_tags",
    )
    well_being_prefetch = Prefetch(
        "tags_for_well_being",
        queryset=UserTag.objects.filter(well_being_tag_filters),
        to_attr="well_being_tags",
    )
    nutrition_prefetch = Prefetch(
        "tags_for_nutrition",
        queryset=UserTag.objects.filter(nutrition_tag_filters),
        to_attr="nutrition_tags",
    )
    daily_questionnaires = (
        DailyQuestionnaire.objects.prefetch_related(skin_care_prefetch, well_being_prefetch, nutrition_prefetch)
        .filter(user=user, created_at__date__range=[start_date, end_date])
        .order_by("created_at__date")
        .distinct("created_at__date")
    )
    total_daily_questionnaires = daily_questionnaires.count()

    face_analytics = FaceScanAnalytics.objects.filter(
        face_scan__user=user,
        is_valid=True,
        created_at__date__range=[start_date, end_date],
    ).order_by("created_at")
    total_face_scans = face_analytics.count()

    progress_data = {
        "total_daily_questionnaires": total_daily_questionnaires,
        "total_face_scans": total_face_scans,
        "message": get_progress_message(start_date, total_daily_questionnaires),
    }
    progress_data.update(get_monthly_routine_data(start_date, end_date, user))
    progress_data.update(get_daily_questionnaire_data(daily_questionnaires))

    progress_data.update({"skin_trend": get_face_analytics_data(face_analytics)})
    if is_recommendation_unlocked(end_date):
        progress_data.update(
            {
                "recommendation": get_recommendations_for_monthly_progress(
                    progress_data["skin_feel"]["avg_answer"],  # type: ignore
                    progress_data["feeling_today"]["avg_answer"],  # type: ignore
                    progress_data["routine"]["avg_status"],  # type: ignore
                    user,
                )
            }
        )
    progress_data.update({"total_score": get_overall_score(progress_data)})
    return progress_data


def generate_previous_months_progress(start_date: datetime.date, end_date: datetime.date, user: User) -> dict:
    """Generates and returns user's previous month data from the provided previous month's start and end date"""
    progress_data = {}
    daily_questionnaires = (
        DailyQuestionnaire.objects.filter(user=user, created_at__date__range=[start_date, end_date])
        .order_by("created_at__date")
        .distinct("created_at__date")
    )
    # No need to generate data if daily questionnaires doesn't exist for a month
    if daily_questionnaires.exists():
        progress_data.update(get_monthly_routine_data(start_date, end_date, user))
        progress_data.update(get_daily_questionnaire_data(daily_questionnaires, True))

        face_analytics = FaceScanAnalytics.objects.filter(
            face_scan__user=user,
            is_valid=True,
            created_at__date__range=[start_date, end_date],
        ).order_by("created_at")
        progress_data.update({"skin_trend": get_face_analytics_data(face_analytics)})
    return progress_data


def get_daily_questionnaire_data(daily_questionnaires: QuerySet[DailyQuestionnaire], skip_tags: bool = False) -> dict:
    """Generates and returns daily questionnaires data from the provided Queryset"""
    skin_feel_data = Counter({category.value: 0 for category in SkinFeel})  # type: ignore
    feeling_today_data = Counter({category.value: 0 for category in FeelingToday})  # type: ignore
    stress_level_data = Counter({category.value: 0 for category in StressLevel})  # type: ignore
    sleep_quality_data = Counter({category.value: 0 for category in SleepQuality})  # type: ignore
    exercise_hours_data = Counter({category.value: 0 for category in ExerciseHours})  # type: ignore
    diet_today_data = Counter({category.value: 0 for category in DietBalance})  # type: ignore
    # the below list is sorted by the optimal quality of hours of sleep according to predefined points (see __init__.py)
    hours_of_sleep_data = Counter({value: 0 for value in [8, 9, 10, 11, 12, 13, 14, 7, 6, 5, 4, 3, 2, 1, 0]})
    water_intake_data = Counter({value: 0 for value in reversed(range(4))})  # type: ignore
    life_happened_data = Counter()  # type: ignore
    skin_care_tags_data = Counter()  # type: ignore
    well_being_tags_data = Counter()  # type: ignore
    nutrition_tags_data = Counter()  # type: ignore

    for question in daily_questionnaires:
        skin_feel_data.update([question.skin_feel])
        feeling_today_data.update([question.feeling_today])
        stress_level_data.update([question.stress_levels])
        hours_of_sleep_data.update([question.hours_of_sleep])
        sleep_quality_data.update([question.sleep_quality])
        water_intake_data.update([question.water])
        diet_today_data.update([question.diet_today])
        exercise_hours_data.update([question.exercise_hours])
        if not skip_tags:
            skin_care_tags_data.update([tag.name for tag in question.skin_care_tags])  # type: ignore
            well_being_tags_data.update([tag.name for tag in question.well_being_tags])  # type: ignore
            nutrition_tags_data.update([tag.name for tag in question.nutrition_tags])  # type: ignore
            life_happened_data.update(question.life_happened)

    questionnaire_data = {
        "skin_feel": generate_questionnaire_data(skin_feel_data, "skin_feel"),
        "stress_levels": generate_questionnaire_data(stress_level_data, "stress_levels"),
        "feeling_today": generate_questionnaire_data(feeling_today_data, "feeling_today"),
        "life_happened": generate_questionnaire_data(life_happened_data, "life_happened"),
        "diet_today": generate_questionnaire_data(diet_today_data, "diet_today"),
        "water": generate_questionnaire_data(water_intake_data, "water"),
        "exercise_hours": generate_questionnaire_data(exercise_hours_data, "exercise_hours"),
    }
    questionnaire_data.update(
        generate_sleep_habit_data(
            generate_questionnaire_data(sleep_quality_data, "sleep_quality"),
            generate_questionnaire_data(hours_of_sleep_data, "hours_of_sleep"),
        )
    )
    if not skip_tags:
        for tags_data in [
            skin_care_tags_data,
            well_being_tags_data,
            nutrition_tags_data,
        ]:
            get_tags_of_minimum_occurrences(tags_data)
        questionnaire_data.update(
            {
                "tags": [  # type: ignore
                    {
                        "category": "skin_care_tags",
                        "data": generate_questionnaire_data(skin_care_tags_data, "skin_care_tags", True).get("data"),
                    },
                    {
                        "category": "well_being_tags",
                        "data": generate_questionnaire_data(well_being_tags_data, "well_being_tags", True).get("data"),
                    },
                    {
                        "category": "nutrition_tags",
                        "data": generate_questionnaire_data(nutrition_tags_data, "nutrition_tags", True).get("data"),
                    },
                ]
            }
        )
    return questionnaire_data


def generate_questionnaire_data(questionnaire_item_data: dict, attr: str, skip_percentage_count: bool = False) -> dict:
    """Generates daily questionnaires data"""
    questionnaire_item_data = Counter({key: value for key, value in questionnaire_item_data.items() if value > 0})
    final_data = {"data": []}  # type: ignore
    for key, value in questionnaire_item_data.items():
        final_data["data"].append({"answer": key, "count": value})
    if not skip_percentage_count:
        total_points, progress_percentage = count_points_and_progress_percentage(questionnaire_item_data, attr)
        final_data.update({"total_points": total_points, "progress": round(progress_percentage, 2)})  # type: ignore
        if level := questionnaire_item_data.most_common(1):  # type: ignore
            final_data.update({"avg_answer": level[0][0]})
        else:
            final_data.update({"avg_answer": None})
    return final_data


def get_progress_message(date: datetime.date, total_filled: int = 0) -> dict:
    """Generates monthly progress based on if the specified date is within current month or a different one"""
    days_in_month = calendar.monthrange(date.year, date.month)[1]
    current_date = timezone.now().date()
    if date.month == current_date.month and date.year == current_date.year:
        days_left = days_in_month - current_date.day
        message = {
            "title": f"{days_left} days left till your full results",
            "subtitle": "Keep tracking to get the most accurate result",
        }
    else:
        message = {
            "title": f"You filled {total_filled}/{days_in_month} questionnaires",
            "subtitle": "Enjoy your results",
        }
    return message


def get_face_analytics_data(face_analytics: QuerySet[FaceScanAnalytics]) -> dict:
    """Generates and returns face analytics data from provided Queryset"""
    face_analytics_data = {}
    attrs = [
        "acne",
        "hydration",
        "pigmentation",
        "pores",
        "redness",
        "uniformness",
    ]
    if skin_attrs := face_analytics.values(*attrs):
        skin_attrs_averages = {}  # type: ignore
        skin_score_data = Counter({category.value: 0 for category in SkinTrendCategories})  # type:ignore
        for item in skin_attrs:
            for attr in attrs:
                if skin_attrs_averages.get(attr):
                    skin_attrs_averages[attr] = (skin_attrs_averages[attr] + item.get(attr, 0)) / 2
                else:
                    skin_attrs_averages[attr] = item.get(attr)
            grade = get_skin_grade(sum(item.values()) / 6)
            skin_score_data.update([grade])
        # Calculating individual skin attributes' which includes grade of the attribute and average values
        other_data = {
            key: {"level": get_skin_grade(value), "value": round(value, 2)}
            for key, value in skin_attrs_averages.items()
        }
        skin_other_progress = round(sum(skin_attrs_averages.values()) / len(skin_attrs_averages.values()), 2)
        face_analytics_data = {
            "other_score": {
                "data": other_data,
                "progress": skin_other_progress,
                "avg_level": get_skin_grade(skin_other_progress),
            },
            "skin_score": {
                "data": [{"answer": k, "count": v} for k, v in skin_score_data.items()],
                "avg_level": skin_score_data.most_common(1)[0][0],
                "progress": skin_other_progress,
            },
        }
    return face_analytics_data


def get_tags_of_minimum_occurrences(tags_counter: dict, min_allowed: int = 5) -> dict:
    """Receives tags counter and removes tags which are below minimum allowed numbers"""
    for key, value in tags_counter.most_common():  # type: ignore
        if value < min_allowed:
            tags_counter.pop(key)
    return tags_counter


def count_points_and_progress_percentage(data: dict, attr: str) -> tuple[int, float]:
    """Calculate total points and progress percentages based on points"""
    total = 0
    total_items = 0
    progress_percentage = 0.0
    for key, value in data.items():
        total += get_points(attr, key) * value
        total_items += value
    # To avoid Zero Division Error
    if max_total := get_max_point(attr) * total_items:
        progress_percentage = (total * 100) / max_total
    return total, progress_percentage


def get_max_point(attr: str) -> int:
    """Determine the maximum value for a particular daily questionnaire attribute"""
    if attr not in POINTS:
        return 0
    return max(POINTS[attr].values())


def get_skin_grade(value: float) -> str:
    """
    Calculates skin attribute grades from provided value.
    Following this business logic to determine the skin grade:
        1. 0-50 Beginner
        2. 51-80 Intermediate
        3. 80+ Advanced
    """
    grade = None
    if value >= 80:
        grade = SkinTrendCategories.ADVANCED.value
    elif 50 <= value < 80:
        grade = SkinTrendCategories.INTERMEDIATE.value
    elif 0 <= value < 50:
        grade = SkinTrendCategories.BEGINNER.value
    return grade


def compare_and_update_monthly_progresses(current_months_progress: dict, previous_months_progress: dict) -> dict:
    """Compare and generate final monthly progress data from two consecutive months"""
    attrs_required_previous_data = ["skin_feel", "feeling_today", "routine"]
    attrs_required_only_current_data = [
        "stress_levels",
        "life_happened",
        "diet_today",
        "water",
        "exercise_hours",
        "sleep",
    ]
    considerable_attrs = attrs_required_previous_data + attrs_required_only_current_data
    for key in current_months_progress.keys():
        if key in considerable_attrs:
            current_data = current_months_progress.get(key)
            previous_data = previous_months_progress.get(key)
            if key in attrs_required_previous_data:
                current_months_progress[key] = {
                    "current_month": current_data,
                    "previous_month": previous_data,
                }
            if previous_data:
                current_months_progress[key].update(
                    {"overall_progress": round(current_data["progress"] - previous_data["progress"], 2)}
                )
        elif key == "skin_trend":
            if (current_data := current_months_progress.get(key).get("skin_score")) and (
                previous_data := previous_months_progress.get(key, {}).get("skin_score")
            ):
                current_months_progress[key]["overall_progress"] = round(
                    current_data["progress"] - previous_data["progress"], 2
                )

    return current_months_progress


def get_recommendations_for_monthly_progress(
    skin_progress: str, feeling_today: str, routine_progress: str, user: User
) -> dict:
    """Calculates and returns recommendations for monthly progress for a user"""
    recommendation_data = {}
    if all([skin_progress, feeling_today, routine_progress]):
        skin_recommendation = recommendation_types.get(skin_progress)
        feeling_today_recommendation = recommendation_types.get(feeling_today)
        routine_recommendation = recommendation_types.get(routine_progress)
        recommendation_data = {
            "skin_feel": {
                "recommendation": skin_recommendation,
                "image": None,
                "title": None,
            },
            "feeling_today": {
                "recommendation": feeling_today_recommendation,
                "image": None,
                "title": None,
            },
            "routine": {
                "recommendation": routine_recommendation,
                "image": None,
                "title": None,
            },
        }
        available_translations = PredictionTemplateTranslation.objects.select_related("template").filter(
            language=get_user_language_code(user),
            template__name__in=[
                skin_recommendation,
                feeling_today_recommendation,
                routine_recommendation,
            ],
        )
        if available_translations:
            for translation in available_translations:
                data = {
                    "recommendation": translation.body,
                    "image": translation.image.url if translation.image else None,
                    "title": translation.title,
                }
                if translation.template.name in PredictionCategories.SKIN_FEELING_TYPES:
                    recommendation_data["skin_feel"] = data
                elif translation.template.name in PredictionCategories.SKIN_TODAY_TYPES:
                    recommendation_data["feeling_today"] = data
                elif translation.template.name in PredictionCategories.ROUTINE_TYPES:
                    recommendation_data["routine"] = data
    return recommendation_data


def get_routine_percentages(total_morning_routine: int, total_evening_routine: int, total_days: int) -> float:
    """Calculates routine progress in percentages"""
    progress_in_percentage = 0.0
    if total_days:
        progress_in_percentage = round(
            ((total_evening_routine + total_morning_routine) * 100) / (total_days * 2),
            2,
        )
    return progress_in_percentage


def get_monthly_routine_data(start_date: datetime.date, end_date: datetime.date, user: User) -> dict:
    """Calculates and returns routine data from total morning and evening routines for a month for a user"""
    total_days = (end_date - start_date).days + 1
    total_routines = Routine.objects.filter(user=user, created_at__date__range=[start_date, end_date]).aggregate(
        morning=Count("routine_type", Q(routine_type=RoutineType.AM.value)),
        evening=Count("routine_type", Q(routine_type=RoutineType.PM.value)),
    )
    routine_data = {"total_days": total_days}

    data = {
        "routine": {
            "data": [
                {
                    "routine_type": RoutineType.AM.value,
                    "count": total_routines["morning"],
                },
                {
                    "routine_type": RoutineType.PM.value,
                    "count": total_routines["evening"],
                },
            ]
            if total_routines["morning"] or total_routines["evening"]
            else [],
            "avg_status": get_routine_progress(total_routines["morning"], total_routines["evening"]),
            "progress": get_routine_percentages(total_routines["morning"], total_routines["evening"], total_days),
        }
    }
    routine_data.update(data)  # type: ignore
    return routine_data


def get_routine_progress(total_morning_routine: int, total_evening_routine: int) -> str:
    """Calculates and returns routine status from total morning and evening routines for a month"""
    status = PredictionTypes.ROUTINE_SKIPPED.value
    total_routines = total_morning_routine + total_evening_routine
    if total_routines >= 50:
        status = PredictionTypes.ROUTINE_DONE.value
    elif 0 < total_routines < 50:
        status = PredictionTypes.ROUTINE_MISSED.value
    return status


def is_recommendation_unlocked(end_date: datetime.date) -> bool:
    """Checks whether monthly progress recommendation was unlocked or not"""
    today = timezone.now().date()
    _, last_day_of_month = calendar.monthrange(end_date.year, end_date.month)
    is_last_day_of_month = end_date.month == today.month and end_date.day == today.day == last_day_of_month
    if end_date.year < today.year or (
        end_date.year == today.year and (end_date.month < today.month or is_last_day_of_month)
    ):
        return True
    return False


def get_user_language_code(user: User) -> str:
    """Returns language code for a particular user"""
    language_code = user.language.code or settings.DEFAULT_LANGUAGE
    return language_code


def get_overall_score(progress_data: dict) -> float:
    """Calculates and returns overall monthly progress score"""
    skip_attrs = [
        "total_daily_questionnaires",
        "total_face_scans",
        "total_days",
        "message",
        "skin_trend",
        "tags",
        "recommendation",
    ]
    avg_face_score = 0.0
    total_daily_score = 0.0
    for attr, value in progress_data.items():
        if attr not in skip_attrs:
            total_daily_score += value["progress"]
    avg_daily_score = total_daily_score / 9
    if skin_trend := progress_data.get("skin_trend"):
        avg_face_score = skin_trend["skin_score"]["progress"]
    score = round((avg_daily_score + avg_face_score) / 2, 2)
    return score


def generate_sleep_habit_data(sleep_quality: dict, sleep_hours: dict) -> dict:
    """Generates and returns sleep habits with monthly progress"""
    return {
        "sleep": {
            "sleep_quality": sleep_quality,
            "hours_of_sleep": sleep_hours,
            "progress": round((sleep_quality.get("progress") + sleep_hours.get("progress")) / 2, 2),
        }
    }
