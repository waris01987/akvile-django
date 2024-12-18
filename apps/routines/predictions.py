import datetime
from typing import Optional, List

from apps.routines import (
    PredictionTypes,
    FeelingToday,
    SkinFeel,
    SleepQuality,
    ExerciseHours,
    StressLevel,
    DietBalance,
    LifeHappened,
    PredictionCategories,
    HealthCareEventTypes,
)
from apps.routines.models import DailyStatistics


def get_routine_prediction(instance: DailyStatistics) -> Optional[str]:
    """Calculates routine prediction for last week"""
    min_limit_for_routine_done = 12
    prediction = None
    current_date = instance.date
    start_date = current_date - datetime.timedelta(days=7)
    # Checking if last prediction was not routine prediction type and the current prediction date is not within
    # last routine prediction date and 7 days after that.
    last_routine_prediction = instance.user.predictions.filter(
        date__lt=current_date, prediction_type__in=PredictionCategories.ROUTINE_TYPES
    ).first()
    between_invalid_routine_prediction_date_range = None
    if last_routine_prediction:
        between_invalid_routine_prediction_date_range = (
            last_routine_prediction.date < current_date < (last_routine_prediction.date + datetime.timedelta(days=6))
        )
    if not between_invalid_routine_prediction_date_range and (
        total_routines_on_this_week := instance.user.routines.filter(
            created_at__date__range=(start_date, current_date)
        ).count()
    ):
        if total_routines_on_this_week >= min_limit_for_routine_done:
            prediction = PredictionTypes.ROUTINE_DONE
        elif 0 < total_routines_on_this_week < min_limit_for_routine_done:
            prediction = PredictionTypes.ROUTINE_MISSED
        else:
            prediction = PredictionTypes.ROUTINE_SKIPPED
    return prediction


def get_daily_questionnaire_prediction(instance: DailyStatistics) -> Optional[str]:
    """Calculates daily prediction for last week"""
    prediction = None
    total_questionnaires_in_days = 7
    max_skipped_questionnaires_in_days = 3
    current_date_as_end_date = instance.date
    start_date = current_date_as_end_date - datetime.timedelta(days=7)
    # Checking if last prediction was not daily questionnaire prediction type and the current prediction date is not
    # within last daily questionnaire prediction date and 7 days after that.
    last_daily_questionnaire_prediction = instance.user.predictions.filter(
        date__lt=current_date_as_end_date,
        prediction_type__in=PredictionCategories.DAILY_QUESTIONNAIRE_TYPES,
    ).first()
    between_invalid_prediction_date_range = None
    if last_daily_questionnaire_prediction:
        between_invalid_prediction_date_range = (
            last_daily_questionnaire_prediction.date
            < current_date_as_end_date
            < (last_daily_questionnaire_prediction.date + datetime.timedelta(days=6))
        )
    if not between_invalid_prediction_date_range and (
        instance.user.daily_questionnaires.filter(
            created_at__date__range=[start_date, current_date_as_end_date]
        ).count()
        <= (total_questionnaires_in_days - max_skipped_questionnaires_in_days)
    ):
        prediction = PredictionTypes.DAILY_QUESTIONNAIRE_SKIPPED
    return prediction


def get_menstruation_prediction(instance: DailyStatistics, last_two_prediction_types: List) -> Optional[str]:
    """Calculates menstruation prediction for current cycle of 28 days"""
    prediction = None
    cycle_duration_in_days = 28
    current_date = instance.date
    # Get the last menstruation event within last 28 days. Menstruation events older than 28 days will not be
    # considered because they won't provide correct phase prediction.
    last_menstruation_event = instance.user.health_care_events.filter(
        start_date__lte=current_date, event_type=HealthCareEventTypes.MENSTRUATION
    ).first()

    if last_menstruation_event and (
        (days_since_last_period := (current_date - last_menstruation_event.start_date).days) <= cycle_duration_in_days
    ):
        calculated_prediction = get_menstruation_phase_prediction(days_since_last_period, cycle_duration_in_days)
        if not any(
            prediction_type in PredictionCategories.MENSTRUATION_TYPES for prediction_type in last_two_prediction_types
        ):
            latest_menstruation_prediction = instance.user.predictions.filter(
                prediction_type__in=PredictionCategories.MENSTRUATION_TYPES
            ).first()
            if (
                latest_menstruation_prediction
                and latest_menstruation_prediction.prediction_type != calculated_prediction
            ):
                prediction = calculated_prediction
            elif not latest_menstruation_prediction:
                prediction = calculated_prediction
    return prediction


def get_menstruation_phase_prediction(days_since_last_period: int, cycle_duration_in_days: int) -> Optional[str]:
    """
    Calculates menstruation phase from days since last period. Menstruation cycle duration is usually 28 days long.
    There are four phases of menstruation period. Those are-
        1. During menstruation - 1-5 days in the cycle
        2. Follicular phase- 5-10 days in the cycle
        3. Ovulation phase- 10-14 days in the cycle
        4. Luteal phase- 14-28 days in the cycle
    """
    phase_prediction = None
    during_phase_starts_at = 0
    follicular_phase_starts_at = 6
    ovulation_phase_starts_at = 11
    luteal_phase_starts_at = 13

    # calculating phase of the current cycle
    if during_phase_starts_at <= days_since_last_period < follicular_phase_starts_at:
        phase_prediction = PredictionTypes.MENSTRUATION_DURING
    elif follicular_phase_starts_at <= days_since_last_period < ovulation_phase_starts_at:
        phase_prediction = PredictionTypes.MENSTRUATION_FOLLICULAR
    elif ovulation_phase_starts_at <= days_since_last_period < luteal_phase_starts_at:
        phase_prediction = PredictionTypes.MENSTRUATION_OVULATION
    elif luteal_phase_starts_at <= days_since_last_period <= cycle_duration_in_days:
        phase_prediction = PredictionTypes.MENSTRUATION_LUTEAL
    return phase_prediction


def get_other_predictions(instance: DailyStatistics, last_two_prediction_types: List) -> list[str]:  # noqa: CFQ001,C901
    """According to business logic we need to consider 3 consecutive answers for these predictions from the
    `DailyQuestionnaire`. If we get same type of answers for 3 consecutive daily questionnaires and last prediction
    was not the same as currently selected one, only then we'll consider creating a prediction for that.
    """

    total_considerable_consecutive_answers = 3
    last_considerable_daily_questions = instance.user.daily_questionnaires.all().values_list(
        "feeling_today",
        "skin_feel",
        "hours_of_sleep",
        "sleep_quality",
        "exercise_hours",
        "stress_levels",
        "diet_today",
        "water",
        "life_happened",
    )[:total_considerable_consecutive_answers]
    selected_predictions_types = []

    # Calculate skin today prediction: 3 answers in a row
    if not any(
        prediction_type in PredictionCategories.SKIN_TODAY_TYPES for prediction_type in last_two_prediction_types
    ):
        skin_today_answers = [answers[0] for answers in last_considerable_daily_questions]
        if skin_today_prediction_type := get_skin_today_prediction(
            skin_today_answers, total_considerable_consecutive_answers
        ):
            selected_predictions_types.append(skin_today_prediction_type)

    # Calculate skin feeling prediction : 3 answers in a row
    if not any(
        prediction_type in PredictionCategories.SKIN_FEELING_TYPES for prediction_type in last_two_prediction_types
    ):
        skin_feeling_answers = [answers[1] for answers in last_considerable_daily_questions]
        if skin_feeling_prediction_type := get_skin_feeling_prediction(
            skin_feeling_answers, total_considerable_consecutive_answers
        ):
            selected_predictions_types.append(skin_feeling_prediction_type)

    # Calculate sleep hour prediction: 3 answers in a row (1. less than 7, 2. equal or greater than 7)
    if not any(
        prediction_type in PredictionCategories.SLEEP_HOURS_TYPES for prediction_type in last_two_prediction_types
    ):
        sleep_hours_answers = [answers[2] for answers in last_considerable_daily_questions]
        if sleep_hour_prediction_type := get_sleep_hour_prediction(
            sleep_hours_answers, total_considerable_consecutive_answers
        ):
            selected_predictions_types.append(sleep_hour_prediction_type)

    # Calculate sleep quality prediction: 3 answers in a row (1. BAD or MEH 2. Well or Love it)
    if not any(
        prediction_type in PredictionCategories.SLEEP_QUALITY_TYPES for prediction_type in last_two_prediction_types
    ):
        sleep_quality_answers = [answers[3] for answers in last_considerable_daily_questions]
        if sleep_quality_prediction_type := get_sleep_quality_prediction(
            sleep_quality_answers, total_considerable_consecutive_answers
        ):
            selected_predictions_types.append(sleep_quality_prediction_type)

    # Calculate exercise prediction: 3 answers in a row (1. Bad, 2. Good 3. Perfect)
    if not any(
        prediction_type in PredictionCategories.EXERCISE_HOURS_TYPES for prediction_type in last_two_prediction_types
    ):
        exercise_hours_answers = [answers[4] for answers in last_considerable_daily_questions]
        if exercise_hours_prediction_type := get_exercise_hours_prediction(
            exercise_hours_answers, total_considerable_consecutive_answers
        ):
            selected_predictions_types.append(exercise_hours_prediction_type)

    # Calculate stress prediction: 3 answers in a row (1. Extreme, 2. Moderate, 3. Relaxed)
    if not any(prediction_type in PredictionCategories.STRESS_TYPES for prediction_type in last_two_prediction_types):
        stress_level_answers = [answers[5] for answers in last_considerable_daily_questions]
        if stress_level_prediction_type := get_stress_level_prediction(
            stress_level_answers, total_considerable_consecutive_answers
        ):
            selected_predictions_types.append(stress_level_prediction_type)

    # Calculate diet prediction: 3 answers in a row (1. Balanced 2. Unbalanced or Mildly balanced)
    if not any(prediction_type in PredictionCategories.DIET_TYPES for prediction_type in last_two_prediction_types):
        diet_answers = [answers[6] for answers in last_considerable_daily_questions]
        if diet_prediction_type := get_diet_prediction(diet_answers, total_considerable_consecutive_answers):
            selected_predictions_types.append(diet_prediction_type)

    # Calculate water intake prediction: 3 answers in a row (1. 0 or 1 litre, 2. 2 or 3 litre)
    if not any(
        prediction_type in PredictionCategories.WATER_INTAKE_TYPES for prediction_type in last_two_prediction_types
    ):
        water_intake_answers = [answers[7] for answers in last_considerable_daily_questions]
        if water_intake_prediction_type := get_water_intake_prediction(
            water_intake_answers, total_considerable_consecutive_answers
        ):
            selected_predictions_types.append(water_intake_prediction_type)

    # Calculate life happened prediction: 3 answers in a row (1. Alcohol or coffee or junk food and sweets)
    if not any(
        prediction_type in PredictionCategories.LIFE_HAPPENED_TYPES for prediction_type in last_two_prediction_types
    ):
        life_happened_answers = [answers[8] for answers in last_considerable_daily_questions]
        if life_happened_prediction_type := get_life_happened_prediction(
            life_happened_answers, total_considerable_consecutive_answers
        ):
            selected_predictions_types.append(life_happened_prediction_type)
    return selected_predictions_types


def get_skin_today_prediction(  # noqa: C901
    skin_today_answers: list[str], total_considerable_consecutive_answers: int
) -> Optional[str]:
    """Calculates and returns skin today prediction from `DailyQuestionnaire`"""
    skin_today_prediction_type = None
    bad_or_mehhh_count = 0
    well_count = 0
    love_it_count = 0
    for feeling in skin_today_answers:
        if feeling in [FeelingToday.BAD, FeelingToday.MEHHH]:
            bad_or_mehhh_count += 1
        elif feeling == FeelingToday.WELL:
            well_count += 1
        elif feeling == FeelingToday.LOVE_IT:
            love_it_count += 1

    if bad_or_mehhh_count == total_considerable_consecutive_answers:
        skin_today_prediction_type = PredictionTypes.SKIN_TODAY_BAD_OR_MEHHH
    if well_count == total_considerable_consecutive_answers:
        skin_today_prediction_type = PredictionTypes.SKIN_TODAY_WELL
    if love_it_count == total_considerable_consecutive_answers:
        skin_today_prediction_type = PredictionTypes.SKIN_TODAY_LOVE_IT
    return skin_today_prediction_type


def get_skin_feeling_prediction(  # noqa: C901
    skin_feeling_answers: list[str], total_considerable_consecutive_answers: int
) -> Optional[str]:
    """Calculates and returns skin feel prediction from `DailyQuestionnaire`"""
    skin_feeling_prediction_type = None
    sensitive_count = 0
    greasy_count = 0
    normal_count = 0
    dehydrated_count = 0

    for feeling in skin_feeling_answers:
        if feeling == SkinFeel.SENSITIVE:
            sensitive_count += 1
        elif feeling == SkinFeel.GREASY:
            greasy_count += 1
        elif feeling == SkinFeel.DEHYDRATED:
            dehydrated_count += 1
        elif feeling == SkinFeel.NORMAL:
            normal_count += 1

    if sensitive_count == total_considerable_consecutive_answers:
        skin_feeling_prediction_type = PredictionTypes.SKIN_FEELING_SENSITIVE
    if greasy_count == total_considerable_consecutive_answers:
        skin_feeling_prediction_type = PredictionTypes.SKIN_FEELING_GREASY
    if normal_count == total_considerable_consecutive_answers:
        skin_feeling_prediction_type = PredictionTypes.SKIN_FEELING_NORMAL
    if dehydrated_count == total_considerable_consecutive_answers:
        skin_feeling_prediction_type = PredictionTypes.SKIN_FEELING_DEHYDRATED
    return skin_feeling_prediction_type


def get_sleep_hour_prediction(
    sleep_hour_answers: list[int], total_considerable_consecutive_answers: int
) -> Optional[str]:
    """Calculates and returns sleep hours prediction from `DailyQuestionnaire`"""
    sleep_hour_prediction_type = None
    less_than_seven_count = 0
    greater_or_equal_seven_count = 0
    min_optimal_sleep_hours = 7

    for hours in sleep_hour_answers:
        if hours < min_optimal_sleep_hours:
            less_than_seven_count += 1
        elif hours >= min_optimal_sleep_hours:
            greater_or_equal_seven_count += 1

    if greater_or_equal_seven_count == total_considerable_consecutive_answers:
        sleep_hour_prediction_type = PredictionTypes.SLEEP_HOURS_GREATER_EQUAL_SEVEN
    if less_than_seven_count == total_considerable_consecutive_answers:
        sleep_hour_prediction_type = PredictionTypes.SLEEP_HOURS_LESS_THAN_SEVEN
    return sleep_hour_prediction_type


def get_sleep_quality_prediction(
    sleep_quality_answers: list[str], total_considerable_consecutive_answers: int
) -> Optional[str]:
    """Calculates and returns sleep quality prediction from `DailyQuestionnaire`"""
    sleep_quality_prediction_type = None
    bad_or_mehhh_count = 0
    well_or_love_it_count = 0

    for quality in sleep_quality_answers:
        if quality == SleepQuality.BAD or quality == SleepQuality.MEHHH:
            bad_or_mehhh_count += 1
        elif quality == SleepQuality.WELL or quality == SleepQuality.LOVE_IT:
            well_or_love_it_count += 1

    if bad_or_mehhh_count == total_considerable_consecutive_answers:
        sleep_quality_prediction_type = PredictionTypes.SLEEP_QUALITY_BAD_OR_MEHHH
    if well_or_love_it_count == total_considerable_consecutive_answers:
        sleep_quality_prediction_type = PredictionTypes.SLEEP_QUALITY_WELL_OR_LOVE_IT
    return sleep_quality_prediction_type


def get_exercise_hours_prediction(  # noqa: C901
    exercise_hours_answers: list[str], total_considerable_consecutive_answers: int
) -> Optional[str]:
    """Calculates and returns exercise hours prediction from `DailyQuestionnaire`"""
    exercise_hours_prediction_type = None
    bad_count = 0
    good_count = 0
    perfect_count = 0

    for hours in exercise_hours_answers:
        if hours == ExerciseHours.ZERO:
            bad_count += 1
        elif hours in [
            ExerciseHours.TWENTY_MIN,
            ExerciseHours.THIRTY_MIN,
            ExerciseHours.FORTY_FIVE_MIN,
        ]:
            good_count += 1
        elif hours in [
            ExerciseHours.ONE_HOUR,
            ExerciseHours.ONE_AND_A_HALF_HOURS,
            ExerciseHours.TWO_HOURS,
            ExerciseHours.TWO_PLUS,
        ]:
            perfect_count += 1

    if bad_count == total_considerable_consecutive_answers:
        exercise_hours_prediction_type = PredictionTypes.EXERCISE_HOURS_BAD
    if good_count == total_considerable_consecutive_answers:
        exercise_hours_prediction_type = PredictionTypes.EXERCISE_HOURS_GOOD
    if perfect_count == total_considerable_consecutive_answers:
        exercise_hours_prediction_type = PredictionTypes.EXERCISE_HOURS_PERFECT
    return exercise_hours_prediction_type


def get_stress_level_prediction(  # noqa: C901
    sleep_level_answers: list[str], total_considerable_consecutive_answers: int
) -> Optional[str]:
    """Calculates and returns stress level prediction from `DailyQuestionnaire`"""
    stress_level_prediction_type = None
    extreme_count = 0
    moderate_count = 0
    relaxed_count = 0

    for level in sleep_level_answers:
        if level == StressLevel.EXTREME:
            extreme_count += 1
        elif level == StressLevel.MODERATE:
            moderate_count += 1
        elif level == StressLevel.RELAXED:
            relaxed_count += 1

    if extreme_count == total_considerable_consecutive_answers:
        stress_level_prediction_type = PredictionTypes.STRESS_EXTREME
    if moderate_count == total_considerable_consecutive_answers:
        stress_level_prediction_type = PredictionTypes.STRESS_MODERATE
    if relaxed_count == total_considerable_consecutive_answers:
        stress_level_prediction_type = PredictionTypes.STRESS_RELAXED
    return stress_level_prediction_type


def get_diet_prediction(diet_answers: list[str], total_considerable_consecutive_answers: int) -> Optional[str]:
    """Calculates and returns diet prediction from `DailyQuestionnaire`"""
    diet_prediction_type = None
    unbalanced_or_mildly_count = 0
    balanced_count = 0

    for diet in diet_answers:
        if diet == DietBalance.UNBALANCED or diet == DietBalance.MILDLY_BALANCED:
            unbalanced_or_mildly_count += 1
        elif diet == DietBalance.BALANCED:
            balanced_count += 1

    if unbalanced_or_mildly_count == total_considerable_consecutive_answers:
        diet_prediction_type = PredictionTypes.DIET_UNBALANCED_or_MILDLY_BALANCED
    if balanced_count == total_considerable_consecutive_answers:
        diet_prediction_type = PredictionTypes.DIET_BALANCED
    return diet_prediction_type


def get_water_intake_prediction(
    water_intake_answers: list[int], total_considerable_consecutive_answers: int
) -> Optional[str]:
    """Calculates and returns water intake prediction from `DailyQuestionnaire`"""
    water_intake_prediction_type = None
    zero_or_one_litre_count = 0
    two_or_three_litre_count = 0

    for litre in water_intake_answers:
        if litre <= 1:
            zero_or_one_litre_count += 1
        elif litre >= 2:
            two_or_three_litre_count += 1

    if zero_or_one_litre_count == total_considerable_consecutive_answers:
        water_intake_prediction_type = PredictionTypes.WATER_INTAKE_ZERO_OR_ONE
    if two_or_three_litre_count == total_considerable_consecutive_answers:
        water_intake_prediction_type = PredictionTypes.WATER_INTAKE_TWO_OR_THREE
    return water_intake_prediction_type


def get_life_happened_prediction(
    life_happened_answers: list[list[str]], total_considerable_consecutive_answers: int
) -> Optional[str]:
    """Calculates and returns life happened prediction from `DailyQuestionnaire`"""
    life_happened_prediction_type = None
    coffee_alcohol_junk_food_count = 0

    for answer in life_happened_answers:
        if answer in [
            LifeHappened.COFFEE,
            LifeHappened.ALCOHOL,
            LifeHappened.JUNK_FOOD_AND_SWEETS,
        ]:
            coffee_alcohol_junk_food_count += 1

    if coffee_alcohol_junk_food_count == total_considerable_consecutive_answers:
        life_happened_prediction_type = PredictionTypes.LIFE_HAPPENED_COFFEE_OR_ALCOHOL_OR_JUNK_FOOD
    return life_happened_prediction_type
