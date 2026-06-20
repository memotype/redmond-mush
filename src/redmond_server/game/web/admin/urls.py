# mypy: ignore-errors
"""Admin route overrides for the Redmond web surface."""

from evennia.web.admin.urls import urlpatterns as evennia_admin_urlpatterns


urlpatterns = [
    # Add project-specific admin URLs here when needed.
]
urlpatterns = urlpatterns + evennia_admin_urlpatterns
