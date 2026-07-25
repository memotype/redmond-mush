"""Django app configuration for permanent character sheets."""

from django.apps import AppConfig


class SheetsConfig(AppConfig):
    """Permanent sheet storage and read surfaces."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "sheets"
