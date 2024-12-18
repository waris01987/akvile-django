from django.contrib import admin

from apps.questionnaire.models import UserQuestionnaire


@admin.register(UserQuestionnaire)
class UserQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ["user", "gender", "age", "created_at", "updated_at"]
    search_fields = ["user__email", "skin_goal", "gender", "age"]

    def has_change_permission(self, request, obj=None):
        return False
