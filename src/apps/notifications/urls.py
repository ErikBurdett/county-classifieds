from __future__ import annotations

from django.urls import path

from . import views

app_name = "notifications"
urlpatterns = [
    path("notifications/", views.feed, name="feed"),
    path(
        "notifications/<uuid:notification_id>/visit/",
        views.visit,
        name="visit",
    ),
    path(
        "notifications/<uuid:notification_id>/read/",
        views.mark_read,
        name="mark_read",
    ),
    path("notifications/read-all/", views.mark_all_read, name="mark_all_read"),
]
