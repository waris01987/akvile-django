from django.conf import settings
from rest_framework.request import Request

from apps.home.models import (
    SiteConfiguration,
    DashboardElement,
    DashboardElementTranslation,
)
from apps.translations.models import Language, Translation


def get_translations(language: Language) -> dict:
    return {trans.message.message_id: trans.text for trans in Translation.objects.filter(language=language)}


def generate_messages() -> dict:
    return {language.pk: get_translations(language) for language in Language.objects.all()}


def get_enabled_languages(config: SiteConfiguration) -> list:
    return [
        {"code": lang.pk, "flag": lang.flag.url if lang.flag else "", "name": lang.name}
        for lang in config.enabled_languages.all()
    ]


def generate_dashboard_order(config: SiteConfiguration) -> dict:
    if config.dashboard_order:
        return {
            "core_program": config.dashboard_order.core_program,
            "recipes": config.dashboard_order.recipes,
            "skin_tools": config.dashboard_order.skin_tools,
            "skin_school": config.dashboard_order.skin_school,
            "skin_stories": config.dashboard_order.skin_stories,
        }
    return {}


def generate_dashboard_element(dashboard_element: DashboardElement, request: Request) -> dict:
    if dashboard_element:
        user = request.user
        language = user.language if user.is_authenticated else Language.objects.get(code=settings.DEFAULT_LANGUAGE)
        try:
            dashboard_element_translation = DashboardElementTranslation.objects.get(
                dashboard_element=dashboard_element, language=language
            )
            return {
                "title": dashboard_element_translation.title,
                "main_text": dashboard_element_translation.content,
                "image": dashboard_element.image.url,
            }
        except DashboardElementTranslation.DoesNotExist:
            return {
                "title": dashboard_element.name,
                "main_text": None,
                "image": dashboard_element.image.url,
            }
    return {}


def generate_config(request: Request) -> dict:
    site_config = SiteConfiguration.get_solo()
    site_default_lang = site_config.default_language
    config = {
        "version": site_config.manifest_version,
        "enabled_languages": get_enabled_languages(site_config),
        "default_language": site_default_lang.code if site_default_lang else settings.DEFAULT_LANGUAGE,
        "translations": generate_messages(),
        "dashboard_order": generate_dashboard_order(site_config),
        "skin_journey": generate_dashboard_element(site_config.skin_journey, request),
        "shop_block": generate_dashboard_element(site_config.shop_block, request),
        "scan_duration": site_config.scan_duration,
        # payments_enabled is a mocked field for older app versions
        "payments_enabled": True,
        "android_payments_enabled": site_config.android_payments_enabled,
        "ios_payments_enabled": site_config.ios_payments_enabled,
    }

    return config
