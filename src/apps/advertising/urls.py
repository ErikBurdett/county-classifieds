from __future__ import annotations

from django.urls import path

from . import views

app_name = "advertising"
urlpatterns = [
    path("partners/", views.partners, name="partners"),
]
