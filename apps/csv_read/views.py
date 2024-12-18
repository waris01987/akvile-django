from rest_framework.response import Response
from rest_framework.views import APIView

from apps.csv_read.read import UpdateChatgptMessageCategory


class RemoveUpdate(APIView):
    def post(self, request):
        if not request.user.is_superuser:
            return Response({"error": "you are not superuser"})
        UpdateChatgptMessageCategory.clear_update_field()
        return Response({"status": "completed"})
