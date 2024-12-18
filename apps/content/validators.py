from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.fields.files import FieldFile


def validate_size(uploaded_file: FieldFile):
    file_size = uploaded_file.file.size
    if file_size > settings.MAX_FILE_UPLOAD_SIZE_B:
        raise ValidationError("Max allowed size for video file is 200 MB")
