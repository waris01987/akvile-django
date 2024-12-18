import json
import logging

import bs4
import pyuser_agent
import requests

LOGGER = logging.getLogger("app")


class GoogleLensApi:
    MINUS_WORDS = [
        "youtube",
        "instagram",
        "tiktok",
        "facebook",
        "like",
        "twitter",
        "your",
        "...",
        "?",
    ]

    @classmethod
    def query_google_lens(cls, image_url):  # pragma: no cover
        """
        Requests google lens via https://lens.google.com/uploadbyurl?url=image_url
        Sometimes it does not work (if so returns False) if YOUR_IMAGE_URL is not 'liked' by google lens

        :param image_url: string
        :return: list of dict or False
        """
        url = "https://lens.google.com/uploadbyurl?url={}".format(image_url)

        ua = pyuser_agent.UA()
        headers = {"User-Agent": ua.random}
        # check image_url
        if not cls.check_image_url(image_url, headers):
            return ""

        try:
            response = cls.request_to_google_lens(url, headers)
            if response.status_code != 200:
                LOGGER.info("response.status_code != 200")
                return ""
        except TimeoutError:
            LOGGER.info("TimeoutError")
            return ""
        product_list = cls.extract_data(response)
        return cls.get_best_product_title(product_list)

    @staticmethod
    def check_image_url(img_url, headers):  # pragma: no cover
        try:
            requests.get(url=img_url, headers=headers)
            return True
        except requests.exceptions.ConnectionError:
            LOGGER.info("Connection error with image address: {}".format(img_url))
            return False
        except requests.exceptions.MissingSchema:
            LOGGER.info("MissingSchema with image address: {}".format(img_url))
            return False

    @staticmethod
    def request_to_google_lens(url, headers):
        return requests.get(url=url, headers=headers)

    @classmethod
    def extract_data(cls, response):  # pragma: no cover
        """This function is used to extract the data from soup of a google lens page
        Args:
            soup (bs4.BeautifulSoup): the html of the page (response of bd_proxy_search
        Returns:
            product_list (list): a list of dictionaries containing the data"""
        json_data = cls.get_json_from_response(response)

        jason = []

        ###########################################
        # This is used beacuse sometimes the information is in json_data[1][0] and other times in json_data[1][1]
        try:
            jason = json_data[1][1][1][8][8][0][12] if len(json_data[1]) == 2 else json_data[1][0][1][8][8][0][12]
        except (IndexError, TypeError):
            LOGGER.info("The data is not in the expected format")
            return []
        ###########################################

        product_list = []
        for product in jason:
            information = {
                "google_image": product[0][0],
                "product_link": product[11],
                "title": product[3],
                "redirect_url": product[5],
                "redirect_name": product[14],
                # 'price': product[0][7][1] iflen(product[0]) > 6 else None
            }
            product_list.append(information)

        return product_list

    @staticmethod
    def get_json_from_response(response):  # pragma: no cover
        if not response.text:
            LOGGER.info("No response.text")
            return []
        soup = bs4.BeautifulSoup(response.text, features="html.parser")
        script_elements = soup.find_all("script")
        raw_data = [x for x in script_elements if "AF_initDataCallback" in x.text]
        try:
            raw_data = raw_data[2].text
        except IndexError:
            LOGGER.info("Possible wrong link to remote file!")
            return []
        start = raw_data.find("data:") + 5
        end = raw_data.find("sideChannel") - 2
        return json.loads(raw_data[start:end])

    @classmethod
    def get_best_product_title(cls, product_list):
        for product in product_list:
            title = cls.get_title(product)
            if not title:
                continue
            if not cls.check_title(title):
                continue
            return title
        return ""

    @staticmethod
    def get_title(product):
        try:
            return product.get("title")[:250]
        except (IndexError, TypeError):
            LOGGER.info("index error")
            return ""

    @classmethod
    def check_title(cls, title):
        if any(word in title.lower() for word in cls.MINUS_WORDS):
            return False
        return True
