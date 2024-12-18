from django.db.models import Count, Q, Max, Sum, Subquery, OuterRef
from fcm_django.models import FCMDevice
from import_export import resources, fields

from apps.orders.models import Order
from apps.users.models import User


class UserResource(resources.ModelResource):
    # onboarding questionnaire fields
    skin_goal = fields.Field("questionnaire__skin_goal", readonly=True)
    feeling_today = fields.Field("questionnaire__feeling_today", readonly=True)
    age = fields.Field("questionnaire__age", readonly=True)
    gender = fields.Field("questionnaire__gender", readonly=True)
    female_power_dt = fields.Field("questionnaire__female_power_dt", readonly=True)
    contraceptive_pill = fields.Field("questionnaire__contraceptive_pill", readonly=True)
    stoped_bc_dt = fields.Field("questionnaire__stoped_bc_dt", readonly=True)
    menstruating = fields.Field("questionnaire__menstruating_person", readonly=True)
    skin_type = fields.Field("questionnaire__skin_type", readonly=True)
    skin_feel = fields.Field("questionnaire__skin_feel", readonly=True)
    expectations = fields.Field("questionnaire__expectations", readonly=True)
    diet_balance = fields.Field("questionnaire__diet_balance", readonly=True)
    diet = fields.Field("questionnaire__diet", readonly=True)
    guilty_pleasures = fields.Field("questionnaire__guilty_pleasures", readonly=True)
    easily_stressed = fields.Field("questionnaire__easily_stressed", readonly=True)
    hours_sleep = fields.Field("questionnaire__hours_of_sleep", readonly=True)
    exercise_days = fields.Field("questionnaire__exercise_days_a_week", readonly=True)
    make_up = fields.Field("questionnaire__make_up", readonly=True)

    # routines
    total_rout = fields.Field("total_routines", readonly=True)
    total_pm_rout = fields.Field("pm_routines", readonly=True)
    total_am_rout = fields.Field("am_routines", readonly=True)
    last_rout = fields.Field("last_routine", readonly=True)

    # face scans
    f_scan_count = fields.Field("f_scan_count", readonly=True)
    last_f_scan = fields.Field("last_f_scan", readonly=True)

    # daily questionnaires
    total_daily_quest = fields.Field("total_daily_questionnaires", readonly=True)
    last_daily_quest = fields.Field("last_daily_questionnaire", readonly=True)

    # user articles
    total_read_art = fields.Field("total_read_articles", readonly=True)

    # orders
    total_amount_spent = fields.Field("total_amount_spent", readonly=True)
    total_orders_made = fields.Field("total_orders_made", readonly=True)
    last_order_amount = fields.Field("last_order_amount", readonly=True)
    last_order_date = fields.Field("last_order_date", readonly=True)

    # FCM Device types
    device_type = fields.Field("device_type", readonly=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "skin_goal",
            "feeling_today",
            "age",
            "gender",
            "female_power_dt",
            "contraceptive_pill",
            "stoped_bc_dt",
            "menstruating",
            "skin_type",
            "skin_feel",
            "expectations",
            "diet_balance",
            "diet",
            "guilty_pleasures",
            "easily_stressed",
            "hours_sleep",
            "exercise_days",
            "make_up",
        ]
        export_order = ["id", "email"]
        chunk_size = 5000

    def get_export_queryset(self):
        qs = (
            self.Meta.model.objects.prefetch_related("questionnaire")
            .annotate(total_routines=Count("routines", distinct=True))
            .annotate(am_routines=Count("routines", filter=Q(routines__routine_type="AM"), distinct=True))
            .annotate(pm_routines=Count("routines", filter=Q(routines__routine_type="PM"), distinct=True))
            .annotate(last_routine=Max("routines__created_at"))
            .annotate(f_scan_count=Count("face_scans", distinct=True))
            .annotate(last_f_scan=Max("face_scans__created_at"))
            .annotate(total_daily_questionnaires=Count("daily_questionnaires", distinct=True))
            .annotate(last_daily_questionnaire=Max("daily_questionnaires__created_at"))
            .annotate(
                total_read_articles=Count(
                    "user_articles",
                    filter=Q(user_articles__is_read=True),
                    distinct=True,
                )
            )
            .annotate(total_amount_spent=Sum("orders__total_price", distinct=True))
            .annotate(total_orders_made=Count("orders", distinct=True))
            .annotate(last_order_date=Max("orders__shopify_order_date"))
            .annotate(
                last_order_amount=Subquery(
                    Order.objects.filter(user=OuterRef("pk")).order_by("-shopify_order_date").values("total_price")[:1]
                )
            )
            .annotate(
                device_type=Subquery(
                    FCMDevice.objects.filter(user=OuterRef("pk")).order_by("-date_created").values("type")[:1]
                )
            )
        )
        return qs
