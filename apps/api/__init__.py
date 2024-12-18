from apps.utils.enums import ChoicesEnum


class CheckAppVersionResultType(ChoicesEnum):
    OK = "OK"
    OK_UPDATE_RECOMMENDED = "OK_UPDATE_RECOMMENDED"
    NOT_OK_UPDATE_REQUIRED = "NOT_OK_UPDATE_REQUIRED"
