from django.apps import AppConfig


class RoutinesConfig(AppConfig):
    name = "apps.routines"

    def ready(self):
        import apps.routines.signals  # noqa
