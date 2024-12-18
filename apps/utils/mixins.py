from import_export.admin import ExportMixin


class CeleryExportMixin(ExportMixin):
    """Mixin class that removes permission to export for django-import-export"""

    def has_export_permission(self, request):
        """Removing export permission through django import export"""
        return False
