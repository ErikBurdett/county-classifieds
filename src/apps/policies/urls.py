from __future__ import annotations

from django.urls import path

from . import views

app_name = "policies"

urlpatterns = [path("policies/<str:kind>/", views.document, name="document")]
