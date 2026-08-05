from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

handler404 = "apps.core.views.page_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("manage/", include("apps.management_console.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.listings.urls")),
    path("", include("apps.billing.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.policies.urls")),
    path("", include("apps.advertising.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.locations.urls")),
]
