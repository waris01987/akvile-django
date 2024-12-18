import csv
import logging

from apps.chat_gpt.models import UserMessage
from apps.routines.models import DailyProduct

log = logging.getLogger(__name__)


class UpdateDailyProductBrand:
    @classmethod
    def run(cls):
        data = cls.read_data_csv()
        cls.update_daily_product_brand(data)

    @classmethod
    def read_data_csv(cls):
        with open("apps/csv_read/result2.csv", "r", encoding="utf-16-le") as file:
            reader = csv.reader(file)
            data = {}
            for row in reader:
                if row[0] == "id":
                    continue
                data[int(row[0])] = row[1]
        return data

    @classmethod
    def update_daily_product_brand(cls, data):
        products = DailyProduct.objects.filter(id__in=data.keys(), brand_updated=False)[:1000]
        for product in products:
            brand = data.get(product.id)
            if brand:
                product.brand = brand
            product.brand_updated = True
        DailyProduct.objects.bulk_update(products, ["brand", "brand_updated"])

    @classmethod
    def clear_update_field(cls):
        data = cls.read_data_csv()
        products = DailyProduct.objects.filter(id__in=data.keys())
        for product in products:
            product.brand_updated = False
        DailyProduct.objects.bulk_update(products, ["brand_updated"])


class UpdateChatgptMessageCategory:
    @classmethod
    def run(cls):
        data = cls.read_data_csv()
        cls.update_chatgpt_message_category(data)

    @classmethod
    def read_data_csv(cls):
        with open("apps/csv_read/chat_gpt_messages_categorised.csv", "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            data = {}
            for row in reader:
                if row[0] == "id":
                    continue
                data[int(row[0])] = row[4]
        return data

    @classmethod
    def update_chatgpt_message_category(cls, data):
        messages = UserMessage.objects.filter(id__in=data.keys(), category_updated=False)[:1000]
        for message in messages:
            category = data.get(message.id)
            if category:
                message.category = category
            message.category_updated = True
            log.warning(f"message.id: {message.id}")
            log.warning(f"message.category: {message.category}")
            log.warning(f"message.category_updated: {message.category_updated}")
        UserMessage.objects.bulk_update(messages, ["category", "category_updated"])

    @classmethod
    def clear_update_field(cls):
        messages = UserMessage.objects.filter()
        for message in messages:
            message.category_updated = False
        UserMessage.objects.bulk_update(messages, ["category_updated"])
