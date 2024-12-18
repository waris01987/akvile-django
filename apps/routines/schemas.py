from drf_spectacular.utils import OpenApiParameter, OpenApiExample

statistics_overview_schema: dict = {
    "parameters": [
        OpenApiParameter(
            "date",
            description="Date for which overview will be provided. i.e. 2022-06-01",
        )
    ],
    "examples": [
        OpenApiExample(
            name="Statistics overview Example",
            value={
                "current_month_average": 60,
                "last_month_average": 70,
                "today_average": 50,
                "yesterday_average": 40,
            },
            response_only=True,
        )
    ],
}

want_have_schema: dict = {
    "examples": [
        OpenApiExample(
            name="Want and have request example",
            value={
                "want": True,
                "have": False,
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Want and have response example",
            value={
                "id": 1,
                "image": "string",
                "title": "string",
                "brand": "string",
                "ingredients": "string",
                "want": True,
                "have": False,
                "recommended_product": True,
                "side_effects": "string",
                "positive_effects": "string",
                "type": "CLEANSER",
            },
            response_only=True,
        ),
    ]
}

monthly_progress_schema: dict = {
    "parameters": [
        OpenApiParameter(
            "month",
            description="Month for which progress will be provided. i.e. 2022-06",
        )
    ],
    "examples": [
        OpenApiExample(
            name="Monthly progress with previous data example",
            value={
                "total_daily_questionnaires": 11,
                "total_face_scans": 11,
                "message": {
                    "title": "0 days left till your full results",
                    "subtitle": "Keep tracking to get the most accurate result",
                },
                "total_days": 30,
                "routine": {
                    "current_month": {
                        "data": [
                            {"routine_type": "AM", "count": 11},
                            {"routine_type": "PM", "count": 11},
                        ],
                        "avg_status": "ROUTINE_MISSED",
                        "progress": 36.67,
                    },
                    "previous_month": {
                        "data": [
                            {"routine_type": "AM", "count": 11},
                            {"routine_type": "PM", "count": 11},
                        ],
                        "avg_status": "ROUTINE_MISSED",
                        "progress": 35.48,
                    },
                    "overall_progress": 1.19,
                },
                "skin_feel": {
                    "current_month": {
                        "data": [
                            {"answer": "SENSITIVE", "count": 1},
                            {"answer": "NORMAL", "count": 8},
                            {"answer": "GREASY", "count": 1},
                            {"answer": "DEHYDRATED", "count": 1},
                        ],
                        "total_points": 230,
                        "progress": 83.64,
                        "avg_answer": "NORMAL",
                    },
                    "previous_month": {
                        "data": [
                            {"answer": "SENSITIVE", "count": 1},
                            {"answer": "NORMAL", "count": 8},
                            {"answer": "GREASY", "count": 1},
                            {"answer": "DEHYDRATED", "count": 1},
                        ],
                        "total_points": 230,
                        "progress": 83.64,
                        "avg_answer": "NORMAL",
                    },
                    "overall_progress": 0.0,
                },
                "stress_levels": {
                    "data": [
                        {"answer": "MODERATE", "count": 2},
                        {"answer": "RELAXED", "count": 8},
                        {"answer": "EXTREME", "count": 1},
                    ],
                    "total_points": 235,
                    "progress": 85.45,
                    "avg_answer": "RELAXED",
                    "overall_progress": 0.0,
                },
                "feeling_today": {
                    "current_month": {
                        "data": [
                            {"answer": "BAD", "count": 2},
                            {"answer": "WELL", "count": 7},
                            {"answer": "MEHHH", "count": 1},
                            {"answer": "LOVE_IT", "count": 1},
                        ],
                        "total_points": 185,
                        "progress": 67.27,
                        "avg_answer": "WELL",
                    },
                    "previous_month": {
                        "data": [
                            {"answer": "BAD", "count": 2},
                            {"answer": "WELL", "count": 7},
                            {"answer": "MEHHH", "count": 1},
                            {"answer": "LOVE_IT", "count": 1},
                        ],
                        "total_points": 185,
                        "progress": 67.27,
                        "avg_answer": "WELL",
                    },
                    "overall_progress": 0.0,
                },
                "life_happened": {
                    "data": [
                        {"answer": "JUNK_FOOD_AND_SWEETS", "count": 3},
                        {"answer": "COFFEE", "count": 2},
                        {"answer": "INNOCENT", "count": 8},
                        {"answer": "ALCOHOL", "count": 1},
                    ],
                    "total_points": 240,
                    "progress": 68.57,
                    "avg_answer": "INNOCENT",
                    "overall_progress": 68.57,
                },
                "diet_today": {
                    "data": [
                        {"answer": "MILDLY_BALANCED", "count": 2},
                        {"answer": "BALANCED", "count": 8},
                        {"answer": "UNBALANCED", "count": 1},
                    ],
                    "total_points": 435,
                    "progress": 79.09,
                    "avg_answer": "BALANCED",
                    "overall_progress": 0.0,
                },
                "water": {
                    "data": [
                        {"answer": 0, "count": 1},
                        {"answer": 2, "count": 2},
                        {"answer": 1, "count": 1},
                        {"answer": 3, "count": 7},
                    ],
                    "total_points": 225,
                    "progress": 81.82,
                    "avg_answer": 3,
                    "overall_progress": 0.0,
                },
                "exercise_hours": {
                    "data": [
                        {"answer": "ZERO", "count": 1},
                        {"answer": "FORTY_FIVE_MIN", "count": 1},
                        {"answer": "TWENTY_MIN", "count": 1},
                        {"answer": "THIRTY_MIN", "count": 1},
                        {"answer": "TWO_HOURS", "count": 1},
                        {"answer": "TWO_PLUS", "count": 6},
                    ],
                    "total_points": 225,
                    "progress": 81.82,
                    "avg_answer": "TWO_PLUS",
                    "overall_progress": 0.0,
                },
                "sleep": {
                    "sleep_quality": {
                        "data": [
                            {"answer": "BAD", "count": 1},
                            {"answer": "LOVE_IT", "count": 7},
                            {"answer": "MEHHH", "count": 2},
                            {"answer": "WELL", "count": 1},
                        ],
                        "total_points": 220,
                        "progress": 80.0,
                        "avg_answer": "LOVE_IT",
                    },
                    "hours_of_sleep": {
                        "data": [
                            {"answer": 3, "count": 1},
                            {"answer": 7, "count": 1},
                            {"answer": 4, "count": 2},
                            {"answer": 6, "count": 1},
                            {"answer": 8, "count": 6},
                        ],
                        "total_points": 185,
                        "progress": 67.27,
                        "avg_answer": 8,
                    },
                    "progress": 73.63,
                    "overall_progress": 0.0,
                },
                "tags": [
                    {
                        "category": "skin_care_tags",
                        "data": [
                            {
                                "answer": "Skin Care Tag1",
                                "count": 9,
                            },
                            {
                                "answer": "Skin Care Tag2",
                                "count": 9,
                            },
                        ],
                    },
                    {
                        "category": "well_being_tags",
                        "data": [
                            {
                                "answer": "Well Being Tag1",
                                "count": 10,
                            },
                            {
                                "answer": "Well Being Tag2",
                                "count": 7,
                            },
                        ],
                    },
                    {
                        "category": "nutrition_tags",
                        "data": [
                            {
                                "answer": "Nutrition Tag1",
                                "count": 9,
                            }
                        ],
                    },
                ],
                "skin_trend": {
                    "other_score": {
                        "data": {
                            "acne": {"level": "INTERMEDIATE", "value": 70.0},
                            "hydration": {"level": "ADVANCED", "value": 90.0},
                            "pigmentation": {"level": "INTERMEDIATE", "value": 80.0},
                            "pores": {"level": "BEGINNER", "value": 0.0},
                            "redness": {"level": "ADVANCED", "value": 82.0},
                            "uniformness": {"level": "BEGINNER", "value": 0.0},
                        },
                        "progress": 62.25,
                        "avg_level": "INTERMEDIATE",
                    },
                    "skin_score": {
                        "data": [
                            {"answer": "INTERMEDIATE", "count": 3},
                            {"answer": "ADVANCED", "count": 6},
                            {"answer": "BEGINNER", "count": 3},
                        ],
                        "avg_level": "ADVANCED",
                        "progress": 62.25,
                    },
                    "overall_progress": 0.0,
                },
                "recommendation": {
                    "skin_feel": {
                        "recommendation": "SKIN_FEELING_NORMAL",
                        "image": None,
                        "title": None,
                    },
                    "feeling_today": {
                        "recommendation": "SKIN_TODAY_WELL",
                        "image": None,
                        "title": None,
                    },
                    "routine": {
                        "recommendation": "ROUTINE_MISSED",
                        "image": None,
                        "title": None,
                    },
                },
                "total_score": 67.68,
            },
            response_only=True,
        ),
        OpenApiExample(
            name="Monthly progress without previous data example",
            value={
                "total_daily_questionnaires": 11,
                "total_face_scans": 11,
                "message": {
                    "title": "0 days left till your full results",
                    "subtitle": "Keep tracking to get the most accurate result",
                },
                "total_days": 30,
                "routine": {
                    "current_month": {
                        "data": [
                            {"routine_type": "AM", "count": 11},
                            {"routine_type": "PM", "count": 11},
                        ],
                        "avg_status": "ROUTINE_MISSED",
                        "progress": 36.67,
                    },
                    "previous_month": None,
                },
                "skin_feel": {
                    "current_month": {
                        "data": [
                            {"answer": "SENSITIVE", "count": 1},
                            {"answer": "NORMAL", "count": 8},
                            {"answer": "GREASY", "count": 1},
                            {"answer": "DEHYDRATED", "count": 1},
                        ],
                        "total_points": 230,
                        "progress": 83.64,
                        "avg_answer": "NORMAL",
                    },
                    "previous_month": None,
                },
                "stress_levels": {
                    "data": [
                        {"answer": "MODERATE", "count": 2},
                        {"answer": "RELAXED", "count": 8},
                        {"answer": "EXTREME", "count": 1},
                    ],
                    "total_points": 235,
                    "progress": 85.45,
                    "avg_answer": "RELAXED",
                },
                "feeling_today": {
                    "current_month": {
                        "data": [
                            {"answer": "BAD", "count": 2},
                            {"answer": "WELL", "count": 7},
                            {"answer": "MEHHH", "count": 1},
                            {"answer": "LOVE_IT", "count": 1},
                        ],
                        "total_points": 185,
                        "progress": 67.27,
                        "avg_answer": "WELL",
                    },
                    "previous_month": None,
                },
                "life_happened": {
                    "data": [
                        {"answer": "JUNK_FOOD_AND_SWEETS", "count": 3},
                        {"answer": "COFFEE", "count": 2},
                        {"answer": "INNOCENT", "count": 8},
                        {"answer": "ALCOHOL", "count": 1},
                    ],
                    "total_points": 240,
                    "progress": 68.57,
                    "avg_answer": "INNOCENT",
                },
                "diet_today": {
                    "data": [
                        {"answer": "MILDLY_BALANCED", "count": 2},
                        {"answer": "BALANCED", "count": 8},
                        {"answer": "UNBALANCED", "count": 1},
                    ],
                    "total_points": 435,
                    "progress": 79.09,
                    "avg_answer": "BALANCED",
                },
                "water": {
                    "data": [
                        {"answer": 0, "count": 1},
                        {"answer": 2, "count": 2},
                        {"answer": 1, "count": 1},
                        {"answer": 3, "count": 7},
                    ],
                    "total_points": 225,
                    "progress": 81.82,
                    "avg_answer": 3,
                },
                "exercise_hours": {
                    "data": [
                        {"answer": "ZERO", "count": 1},
                        {"answer": "FORTY_FIVE_MIN", "count": 1},
                        {"answer": "TWENTY_MIN", "count": 1},
                        {"answer": "THIRTY_MIN", "count": 1},
                        {"answer": "TWO_HOURS", "count": 1},
                        {"answer": "TWO_PLUS", "count": 6},
                    ],
                    "total_points": 225,
                    "progress": 81.82,
                    "avg_answer": "TWO_PLUS",
                },
                "sleep": {
                    "sleep_quality": {
                        "data": [
                            {"answer": "BAD", "count": 1},
                            {"answer": "LOVE_IT", "count": 7},
                            {"answer": "MEHHH", "count": 2},
                            {"answer": "WELL", "count": 1},
                        ],
                        "total_points": 220,
                        "progress": 80.0,
                        "avg_answer": "LOVE_IT",
                    },
                    "hours_of_sleep": {
                        "data": [
                            {"answer": 3, "count": 1},
                            {"answer": 7, "count": 1},
                            {"answer": 4, "count": 2},
                            {"answer": 6, "count": 1},
                            {"answer": 8, "count": 6},
                        ],
                        "total_points": 185,
                        "progress": 67.27,
                        "avg_answer": 8,
                    },
                    "progress": 73.63,
                },
                "tags": [
                    {
                        "category": "skin_care_tags",
                        "data": [
                            {
                                "answer": "Skin Care Tag1",
                                "count": 9,
                            },
                            {
                                "answer": "Skin Care Tag2",
                                "count": 9,
                            },
                        ],
                    },
                    {
                        "category": "well_being_tags",
                        "data": [
                            {
                                "answer": "Well Being Tag1",
                                "count": 10,
                            },
                            {
                                "answer": "Well Being Tag2",
                                "count": 7,
                            },
                        ],
                    },
                    {
                        "category": "nutrition_tags",
                        "data": [
                            {
                                "answer": "Nutrition Tag1",
                                "count": 9,
                            }
                        ],
                    },
                ],
                "skin_trend": {
                    "other_score": {
                        "data": {
                            "acne": {"level": "INTERMEDIATE", "value": 70.0},
                            "hydration": {"level": "ADVANCED", "value": 90.0},
                            "pigmentation": {"level": "INTERMEDIATE", "value": 80.0},
                            "pores": {"level": "BEGINNER", "value": 0.0},
                            "redness": {"level": "ADVANCED", "value": 82.0},
                            "uniformness": {"level": "BEGINNER", "value": 0.0},
                        },
                        "progress": 62.25,
                        "avg_level": "INTERMEDIATE",
                    },
                    "skin_score": {
                        "data": [
                            {"answer": "INTERMEDIATE", "count": 3},
                            {"answer": "ADVANCED", "count": 6},
                            {"answer": "BEGINNER", "count": 3},
                        ],
                        "avg_level": "ADVANCED",
                        "progress": 62.25,
                    },
                },
                "recommendation": {
                    "skin_feel": {
                        "recommendation": "SKIN_FEELING_NORMAL",
                        "image": None,
                        "title": None,
                    },
                    "feeling_today": {
                        "recommendation": "SKIN_TODAY_WELL",
                        "image": None,
                        "title": None,
                    },
                    "routine": {
                        "recommendation": "ROUTINE_MISSED",
                        "image": None,
                        "title": None,
                    },
                },
                "total_score": 67.68,
            },
            response_only=True,
        ),
        OpenApiExample(
            name="Monthly progress example for empty data",
            value={
                "total_daily_questionnaires": 0,
                "total_face_scans": 0,
                "message": {
                    "title": "You filled 0/30 questionnaires",
                    "subtitle": "Enjoy your results",
                },
                "total_days": 30,
                "routine": {
                    "current_month": {
                        "data": [],
                        "avg_status": "ROUTINE_SKIPPED",
                        "progress": 0.0,
                    },
                    "previous_month": None,
                },
                "skin_feel": {
                    "current_month": {
                        "data": [],
                        "total_points": 0,
                        "progress": 0.0,
                        "avg_answer": None,
                    },
                    "previous_month": None,
                },
                "stress_levels": {
                    "data": [],
                    "total_points": 0,
                    "progress": 0.0,
                    "avg_answer": None,
                },
                "feeling_today": {
                    "current_month": {
                        "data": [],
                        "total_points": 0,
                        "progress": 0.0,
                        "avg_answer": None,
                    },
                    "previous_month": None,
                },
                "life_happened": {
                    "data": [],
                    "total_points": 0,
                    "progress": 0.0,
                    "avg_answer": None,
                },
                "diet_today": {
                    "data": [],
                    "total_points": 0,
                    "progress": 0.0,
                    "avg_answer": None,
                },
                "water": {
                    "data": [],
                    "total_points": 0,
                    "progress": 0.0,
                    "avg_answer": None,
                },
                "exercise_hours": {
                    "data": [],
                    "total_points": 0,
                    "progress": 0.0,
                    "avg_answer": None,
                },
                "sleep": {
                    "sleep_quality": {
                        "data": [],
                        "total_points": 0,
                        "progress": 0.0,
                        "avg_answer": None,
                    },
                    "hours_of_sleep": {
                        "data": [],
                        "total_points": 0,
                        "progress": 0.0,
                        "avg_answer": None,
                    },
                    "progress": 0.0,
                },
                "tags": [
                    {"category": "skin_care_tags", "data": []},
                    {"category": "well_being_tags", "data": []},
                    {"category": "nutrition_tags", "data": []},
                ],
                "skin_trend": {},
                "recommendation": {},
                "total_score": 0.0,
            },
            response_only=True,
        ),
    ],
}
