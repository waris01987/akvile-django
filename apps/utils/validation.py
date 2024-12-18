from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.template import Template, exceptions


def check_template(template):
    """Checks whether the template is valid"""
    try:
        Template(template)
    except exceptions.TemplateSyntaxError:
        raise ValidationError("Invalid template syntax")


# Allowed extension for image fields
validate_image_file_extensions = FileExtensionValidator(
    ["jpg", "jpeg", "png", "svg", "bmp", "gif", "webp", "psd", "tiff"]
)
