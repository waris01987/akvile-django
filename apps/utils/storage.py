import os

from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """Class for public uploaded files that will not have a querystring auth, e.g.
    images that are intended to be included in the emails"""

    bucket_name = os.getenv("STORAGE_BUCKET_NAME")
    default_region = os.getenv("AWS_DEFAULT_REGION")
    location = "media"
    file_overwrite = False


class StaticStorage(S3Boto3Storage):
    """Static files storage"""

    bucket_name = os.getenv("STATIC_BUCKET_NAME")
    default_region = os.getenv("AWS_DEFAULT_REGION")
    location = "static"
    file_overwrite = True


class PrivateMediaStorage(MediaStorage):
    """Class for restricted uploaded files that will have a querystring auth"""

    querystring_auth = True
    default_acl = "private"


restricted_file_storage = PrivateMediaStorage() if os.getenv("STORAGE_BUCKET_NAME") is not None else FileSystemStorage()
