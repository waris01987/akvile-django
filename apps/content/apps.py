from django.apps import AppConfig


class ContentConfig(AppConfig):
    name = "apps.content"

    def ready(self):
        import apps.content.signals  # noqa
