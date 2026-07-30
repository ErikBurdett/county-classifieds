from __future__ import annotations

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("report-listing/<uuid:listing_id>/", views.report_listing, name="report_listing"),
    path("staff/reports/", views.queue, name="queue"),
    path("staff/reports/<uuid:report_id>/", views.triage, name="triage"),
]
