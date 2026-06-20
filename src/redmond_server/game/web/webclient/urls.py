# mypy: ignore-errors
"""Webclient route overrides for the Redmond web surface."""

from evennia.web.webclient.urls import (
    urlpatterns as evennia_webclient_urlpatterns,
)


urlpatterns = [
    # Add project-specific webclient URLs here when needed.
]
urlpatterns = urlpatterns + evennia_webclient_urlpatterns
