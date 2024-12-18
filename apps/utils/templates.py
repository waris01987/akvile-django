import logging

from django.conf import settings
from django.template import Context, Template

LOGGER = logging.getLogger("app")


def render_template_message(template: str, context: dict) -> str:
    context.update(get_global_params())
    template = Template(template)
    context = Context(context)
    return template.render(context)


def get_global_params() -> dict:
    return {"APP_HOST": settings.APP_HOST}
