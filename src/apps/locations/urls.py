from __future__ import annotations

from django.urls import path

from . import views

app_name = "locations"

urlpatterns = [
    path("markets/", views.market_finder, name="market_finder"),
    path("in-search-of/", views.in_search_of, name="in_search_of"),
    path(
        "in-search-of/<slug:state_slug>/",
        views.in_search_of,
        name="in_search_of_state",
    ),
    path("images/<uuid:image_id>/", views.public_listing_image, name="public_listing_image"),
    path("videos/<uuid:video_id>/", views.public_listing_video, name="public_listing_video"),
    path(
        "<slug:state_slug>/<slug:county_slug>/listing/<uuid:listing_id>/",
        views.listing_detail,
        name="listing_detail",
    ),
    path("<slug:state_slug>/", views.state_context, name="state_context"),
    path(
        "<slug:state_slug>/<slug:county_slug>/",
        views.county_context,
        name="county_context",
    ),
]
