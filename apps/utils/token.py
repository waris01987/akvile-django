from django.utils.dateformat import format as datetime_format
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


def get_token(user: User) -> RefreshToken:
    token = RefreshToken.for_user(user)
    # Claim dedicated to keep track of a valid datetime
    token["datetime_claim"] = int(datetime_format(user.password_last_change, "U"))
    return token
