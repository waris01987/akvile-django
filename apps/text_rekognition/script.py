from urllib.request import urlopen

import boto3
from django.conf import settings


class TextRekognition:
    @classmethod
    def run(cls, image_url):
        client = boto3.client(
            "rekognition",
            aws_access_key_id=settings.TEXT_REKOGNITION_ACCESS_KEY,
            aws_secret_access_key=settings.TEXT_REKOGNITION_SECRET_KEY,
            region_name="eu-central-1",
        )
        # load the input image as a raw binary file and make a request to
        # the Amazon Rekognition OCR API
        image = urlopen(image_url).read()  # noqa S310
        response = client.detect_text(Image={"Bytes": image})
        # grab the text detection results from the API and load the input
        # image again, this time in OpenCV format
        detections = response["TextDetections"]
        result = ""
        for detection in detections:
            text = detection["DetectedText"]
            result += f"{text} "
        return result

    @classmethod
    def run_bytes(cls, product_image):
        client = boto3.client(
            "rekognition",
            aws_access_key_id=settings.TEXT_REKOGNITION_ACCESS_KEY,
            aws_secret_access_key=settings.TEXT_REKOGNITION_SECRET_KEY,
            region_name="eu-central-1",
        )
        # load the input image as a raw binary file and make a request to
        # the Amazon Rekognition OCR API
        # image = urlopen(image_url).read()  # noqa S310
        image_bytes = product_image.read()
        # with open(product_image, "rb") as image:
        #     image_bytes = image.read()
        response = client.detect_text(Image={"Bytes": image_bytes})
        # grab the text detection results from the API and load the input
        # image again, this time in OpenCV format
        detections = response["TextDetections"]
        result = ""
        for detection in detections:
            text = detection["DetectedText"]
            result += f"{text} "
        return result
