from apps.utils.enums import ChoicesEnum


class SkinGoal(str, ChoicesEnum):
    LESS_PIMPLES = "LESS_PIMPLES"
    LESS_SCARS = "LESS_SCARS"
    LESS_WRINKLES = "LESS_WRINKLES"
    OVERALL_SKIN_HEALTH = "OVERALL_SKIN_HEALTH"


class FeelingToday(str, ChoicesEnum):
    BAD = "BAD"
    MEHHH = "MEHHH"
    WELL = "WELL"
    LOVE_IT = "LOVE_IT"


class Age(str, ChoicesEnum):
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


class Gender(str, ChoicesEnum):
    FEMALE = "FEMALE"
    DIVERSE = "DIVERSE"
    MALE = "MALE"


class ContraceptivePill(str, ChoicesEnum):
    ON_BIRTH_CONTROL = "ON_BIRTH_CONTROL"
    STOPPED_BIRTH_CONTROL = "STOPPED_BIRTH_CONTROL"
    NEVER_BEEN_ON_IT = "NEVER_BEEN_ON_IT"
    IM_PREGNANT = "IM_PREGNANT"


class SkinType(str, ChoicesEnum):
    OILY_SKIN = "OILY_SKIN"
    NORMAL_SKIN = "NORMAL_SKIN"
    COMBINATION_SKIN = "COMBINATION_SKIN"
    DRY_SKIN = "DRY_SKIN"
    SKIPPED = "SKIPPED"


class SkinFeel(str, ChoicesEnum):
    SENSITIVE = "SENSITIVE"
    GREASY = "GREASY"
    DEHYDRATED = "DEHYDRATED"
    NORMAL = "NORMAL"
    SKIPPED = "SKIPPED"


class ExpectationsForFirstResults(str, ChoicesEnum):
    ASAP = "ASAP"
    AFTER_TWO_WEEKS = "AFTER_TWO_WEEKS"
    IT_TAKES_TIME = "IT_TAKES_TIME"
    SKIPPED = "SKIPPED"


class DietBalance(str, ChoicesEnum):
    BALANCED = "BALANCED"
    MILDLY_BALANCED = "MILDLY_BALANCED"
    UNBALANCED = "UNBALANCED"
    SKIPPED = "SKIPPED"


class Diet(str, ChoicesEnum):
    VEGAN_VEGETARIAN = "VEGAN_VEGETARIAN"
    DIARY_FREE = "DIARY_FREE"
    MIXED = "MIXED"
    LOW_CARB = "LOW_CARB"
    SKIPPED = "SKIPPED"


class GuiltyPleasures(str, ChoicesEnum):
    COFFEE = "COFFEE"
    ALCOHOL = "ALCOHOL"
    JUNK_FOOD_AND_SWEETS = "JUNK_FOOD_AND_SWEETS"
    SMOKING = "SMOKING"
    SKIPPED = "SKIPPED"
    IM_INNOCENT = "IM_INNOCENT"


class EasilyStressedAndUpset(str, ChoicesEnum):
    YES = "YES"
    MODERATE = "MODERATE"
    NO = "NO"
    SKIPPED = "SKIPPED"


class DailyBusiness(str, ChoicesEnum):
    STUDY = "STUDY"
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    NOT_BUSY = "NOT_BUSY"
    MATERNITY = "MATERNITY"


class HoursOfSleep(str, ChoicesEnum):
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    ELEVEN = "11"
    TWELVE = "12"
    THIRTEEN = "13"
    FOURTEEN = "14"
    SKIPPED = "SKIPPED"
    NINE_PLUS = "NINE_PLUS"
    SEVEN_EIGHT = "SEVEN_EIGHT"
    FIVE_SIX = "FIVE_SIX"
    ZERO_FOUR = "ZERO_FOUR"


class ExerciseDaysAWeek(str, ChoicesEnum):
    ZERO = "ZERO"
    ONE = "ONE"
    TWO = "TWO"
    THREE = "THREE"
    FOUR = "FOUR"
    FIVE = "FIVE"
    SIX_PLUS = "SIX_PLUS"
    SKIPPED = "SKIPPED"
    EVERY_DAY = "EVERY_DAY"
    FOUR_FIVE = "FOUR_FIVE"
    ONE_THREE = "ONE_THREE"
    NO_EXERCISE = "NO_EXERCISE"


class SmokingPreferences(str, ChoicesEnum):
    HABITUAL_SMOKER = "HABITUAL_SMOKER"
    SOCIAL_SMOKER = "SOCIAL_SMOKER"
    ANXIOUS_SMOKER = "ANXIOUS_SMOKER"
    NON_SMOKER = "NON_SMOKER"
