from typing import no_type_check

from django.utils.functional import classproperty  # type: ignore

from apps.utils.enums import ChoicesEnum


class ArticleType(str, ChoicesEnum):
    TEXT = "TEXT"
    VIDEO = "VIDEO"


class AboutAndNoticeSectionType(str, ChoicesEnum):
    TERMS_OF_SERVICE = "TERMS_OF_SERVICE"
    PRIVACY_POLICY = "PRIVACY_POLICY"


class UserQuestionnaireVariable(str, ChoicesEnum):
    SKIN_GOAL = "SKIN_GOAL"
    FEELING_TODAY = "FEELING_TODAY"
    AGE = "AGE"
    GENDER = "GENDER"
    CONTRACEPTIVE_PILL = "CONTRACEPTIVE_PILL"
    MENSTRUATING_PERSON = "MENSTRUATING_PERSON"


class ComparisonOperator(str, ChoicesEnum):
    IS_GREATER_THAN = "IS_GREATER_THAN"
    IS_EQUAL_TO = "IS_EQUAL_TO"
    IS_LESS_THAN = "IS_LESS_THAN"


class ContentRuleValues(str, ChoicesEnum):
    LESS_PIMPLES = "LESS_PIMPLES"
    LESS_SCARS = "LESS_SCARS"
    LESS_WRINKLES = "LESS_WRINKLES"
    OVERALL_SKIN_HEALTH = "OVERALL_SKIN_HEALTH"
    AGE_12_16 = "AGE_12_16"
    AGE_17_21 = "AGE_17_21"
    AGE_22_26 = "AGE_22_26"
    AGE_27_31 = "AGE_27_31"
    AGE_32_36 = "AGE_32_36"
    AGE_37_41 = "AGE_37_41"
    AGE_42_46 = "AGE_42_46"
    AGE_47_51 = "AGE_47_51"
    AGE_52_56 = "AGE_52_56"
    AGE_57_61 = "AGE_57_61"
    AGE_61_PLUS = "AGE_61_PLUS"
    FEMALE = "FEMALE"
    DIVERSE = "DIVERSE"
    MALE = "MALE"
    BAD = "BAD"
    MEHHH = "MEHHH"
    WELL = "WELL"
    LOVE_IT = "LOVE_IT"
    ON_BIRTH_CONTROL = "ON_BIRTH_CONTROL"
    STOPPED_BIRTH_CONTROL = "STOPPED_BIRTH_CONTROL"
    NEVER_BEEN_ON_IT = "NEVER_BEEN_ON_IT"
    IM_PREGNANT = "IM_PREGNANT"
    TRUE = True
    FALSE = False


class CategoryName(str, ChoicesEnum):
    CORE_PROGRAM = "CORE_PROGRAM"
    SKIN_STORIES = "SKIN_STORIES"
    SKIN_SCHOOL = "SKIN_SCHOOL"
    RECIPES = "RECIPES"
    INITIAL = "INITIAL"
    INDIAN_RECIPES = "INDIAN_RECIPES"
    INDIAN_ARTICLES = "INDIAN_ARTICLES"

    @classproperty
    def with_subcategories(cls) -> list:  # noqa: N805
        return [cls.CORE_PROGRAM, cls.RECIPES, cls.INDIAN_RECIPES]

    @classproperty
    def without_subcategories(cls) -> list:  # noqa: N805
        return [cls.SKIN_STORIES, cls.SKIN_SCHOOL, cls.INITIAL, cls.INDIAN_ARTICLES]


class SubCategoryName(str, ChoicesEnum):
    RECIPE_NUTRITION = "RECIPE_NUTRITION"
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
    SNACKS = "SNACKS"
    HABITS = "HABITS"
    SKINCARE = "SKINCARE"
    WELLBEING = "WELLBEING"
    NUTRITIONS = "NUTRITIONS"
    INDIAN_BREAKFAST = "INDIAN_BREAKFAST"
    INDIAN_LUNCH = "INDIAN_LUNCH"
    INDIAN_DINNER = "INDIAN_DINNER"
    INDIAN_SNACK = "INDIAN_SNACK"

    @no_type_check
    @classproperty
    def group_by_category(cls) -> dict:  # noqa: N805
        return {
            CategoryName.CORE_PROGRAM.value: [
                cls.HABITS.value,
                cls.SKINCARE.value,
                cls.WELLBEING.value,
                cls.NUTRITIONS.value,
            ],
            CategoryName.RECIPES.value: [
                cls.RECIPE_NUTRITION.value,
                cls.BREAKFAST.value,
                cls.LUNCH.value,
                cls.DINNER.value,
                cls.SNACKS.value,
            ],
            CategoryName.INDIAN_RECIPES.value: [
                cls.INDIAN_BREAKFAST.value,
                cls.INDIAN_LUNCH.value,
                cls.INDIAN_DINNER.value,
                cls.INDIAN_SNACK.value,
            ],
        }

    @classmethod
    def get_by_category(cls, category: str) -> list:
        return cls.group_by_category.get(category, [])


class LifeStyleCategories(str, ChoicesEnum):
    NUTRITION = "NUTRITION"
    SLEEP = "SLEEP"
    STRESS = "STRESS"
    EXERCISE = "EXERCISE"
