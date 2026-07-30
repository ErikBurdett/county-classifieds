from __future__ import annotations

from django.urls import path

from . import views

app_name = "management_console"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.staff_login, name="login"),
    path("logout/", views.staff_logout, name="logout"),
]
