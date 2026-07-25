"""Django app configuration for chargen state."""

from django.apps import AppConfig


class ChargenConfig(AppConfig):
    """Chargen workflow storage and read surfaces."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "chargen"
