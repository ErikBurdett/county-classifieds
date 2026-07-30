from __future__ import annotations

from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("robots.txt", views.robots, name="robots"),
    path("sitemap.xml", views.sitemap_index, name="sitemap_index"),
    path("sitemaps/<str:section>-<int:page>.xml", views.sitemap_page, name="sitemap_page"),
    path("health/live/", views.liveness, name="liveness"),
    path("health/ready/", views.readiness, name="readiness"),
]
