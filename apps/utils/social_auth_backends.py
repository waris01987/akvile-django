from rest_framework.exceptions import ValidationError
from social_core.backends.apple import AppleIdAuth
from social_core.backends.facebook import FacebookOAuth2
from social_core.exceptions import AuthMissingParameter
from social_core.utils import parse_qs, handle_http_errors

from apps.users import SocialClient
from apps.utils.error_codes import Errors


class FacebookExchangeTokenOAuth2(FacebookOAuth2):
    """
    Facebook authentication backend which uses short lived `exchange_token` instead of `code` to
    retrieve long lived access token.
    This custom backend class is needed because library chosen by Front-end uses this type of authentication.
    """

    @handle_http_errors
    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance"""
        self.process_error(self.data)
        if not self.data.get("code"):
            raise AuthMissingParameter(self, "code")
        state = self.validate_state()
        key, secret = self.get_key_and_secret()
        response = self.request(
            self.access_token_url(),
            params={
                "client_id": key,
                "client_secret": secret,
                "fb_exchange_token": self.data["code"],
                "grant_type": "fb_exchange_token",
                "redirect_uri": self.get_redirect_uri(state),
            },
        )
        # API v2.3 returns a JSON, according to the documents linked at issue
        # #592, but it seems that this needs to be enabled(?), otherwise the
        # usual querystring type response is returned.
        try:
            response = response.json()
        except ValueError:
            response = parse_qs(response.text)
        access_token = response["access_token"]
        return self.do_auth(access_token, response, *args, **kwargs)

    def user_data(self, access_token, *args, **kwargs):
        user_data = super().user_data(access_token, *args, **kwargs)

        if not user_data.get("email"):
            raise ValidationError(Errors.SOCIAL_AUTH_MISSING_EMAIL.value)

        return user_data


class MultiClientAppleIdAuth(AppleIdAuth):
    CLIENT_ID_SETTING_MAP = {
        SocialClient.WEB.value: "CLIENT_WEB",
        SocialClient.APP.value: "CLIENT_APP",
    }
    DEFAULT_CLIENT_ID_SETTING = SocialClient.APP.value

    def setting(self, name, default=None):
        if name == "CLIENT":
            name = self.CLIENT_ID_SETTING_MAP[self.data.get("client_type", self.DEFAULT_CLIENT_ID_SETTING)]
        return super(MultiClientAppleIdAuth, self).setting(name, default)
