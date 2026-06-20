# mypy: ignore-errors
"""Root URL router for the Redmond Evennia web surfaces."""

from django.urls import include, path

from evennia.web.urls import urlpatterns as evennia_default_urlpatterns


urlpatterns = [
    path("", include("web.website.urls")),
    path("webclient/", include("web.webclient.urls")),
    path("admin/", include("web.admin.urls")),
]
urlpatterns = urlpatterns + evennia_default_urlpatterns
