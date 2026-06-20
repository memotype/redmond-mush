# mypy: ignore-errors
"""Website route overrides for the Redmond web surface."""

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns


urlpatterns = [
    # Add project-specific website URLs here when needed.
]
urlpatterns = urlpatterns + evennia_website_urlpatterns
