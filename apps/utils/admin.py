from django.conf import settings
from django.contrib.admin import AdminSite as Site, apps


class AdminSite(Site):
    site_header = "Django admin"
    site_title = "Django site"

    def each_context(self, request) -> dict:
        context = super().each_context(request)
        context["color"] = settings.ADMIN_COLOR
        return context


class AdminConfig(apps.AdminConfig):
    default_site = "apps.utils.admin.AdminSite"


site = AdminSite(name="admin")
