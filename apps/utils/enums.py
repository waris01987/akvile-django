from enum import Enum


class ChoicesEnum(Enum):
    """Enum for model char field choice constants."""

    @classmethod
    def get_choices(cls) -> list:
        choices = []
        for prop in cls:
            choices.append((prop.value, prop.name))
        return choices

    @staticmethod
    def get_display_name(name: str) -> str:
        return name.replace("_", " ").title()

    @classmethod
    def get_display_names(cls, *names: list) -> list:
        return list(map(cls.get_display_name, names))  # type: ignore
