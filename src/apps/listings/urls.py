from __future__ import annotations

from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "dashboard/listings/<uuid:listing_id>/detail/",
        views.owner_listing_detail,
        name="owner_listing_detail",
    ),
    path("dashboard/listings/new/", views.create_listing, name="create_listing"),
    path(
        "dashboard/listings/wanted/new/",
        views.create_listing,
        name="create_wanted_listing",
    ),
    path(
        "dashboard/listings/generic/new/",
        views.create_generic_draft,
        name="create_generic_draft",
    ),
    path(
        "dashboard/listings/county-candidates/",
        views.generic_county_candidates,
        name="generic_county_candidates",
    ),
    path(
        "dashboard/listings/state-candidates/",
        views.state_candidates,
        name="state_candidates",
    ),
    path(
        "dashboard/listings/categories/",
        views.generic_categories,
        name="generic_categories",
    ),
    path(
        "dashboard/listings/<uuid:listing_id>/",
        views.generic_draft_detail,
        name="generic_draft_detail",
    ),
    path(
        "dashboard/listings/<uuid:listing_id>/edit/",
        views.edit_listing,
        name="edit_listing",
    ),
    path(
        "dashboard/listings/<uuid:listing_id>/edit/",
        views.edit_listing,
        name="edit_generic_draft",
    ),
    path("favorites/", views.favorites, name="favorites"),
    path("favorites/<uuid:listing_id>/toggle/", views.favorite_toggle, name="favorite_toggle"),
    path(
        "dashboard/listings/<uuid:listing_id>/actions/<str:action>/",
        views.listing_action,
        name="listing_action",
    ),
    path("dashboard/drafts/<uuid:listing_id>/submit/", views.submit_draft, name="submit_draft"),
    path("staff/moderation/", views.moderation_queue_view, name="moderation_queue"),
    path(
        "staff/moderation/<uuid:listing_id>/",
        views.moderate_listing_view,
        name="moderate_listing",
    ),
    path("dashboard/autos/new/", views.create_auto_draft, name="create_auto_draft"),
    path("dashboard/homes/new/", views.create_home_draft, name="create_home_draft"),
    path("dashboard/rentals/new/", views.create_rental_draft, name="create_rental_draft"),
    path(
        "dashboard/ag-equipment/new/",
        views.create_ag_equipment_draft,
        name="create_ag_equipment_draft",
    ),
    path("dashboard/livestock/new/", views.create_livestock_draft, name="create_livestock_draft"),
    path("dashboard/pasture/new/", views.create_pasture_draft, name="create_pasture_draft"),
    path(
        "dashboard/home-garden/new/",
        views.create_home_garden_draft,
        name="create_home_garden_draft",
    ),
    path(
        "dashboard/appliances/new/",
        views.create_appliances_draft,
        name="create_appliances_draft",
    ),
    path(
        "dashboard/homes/<uuid:listing_id>/",
        views.home_draft_detail,
        name="home_draft_detail",
    ),
    path(
        "dashboard/homes/<uuid:listing_id>/edit/",
        views.edit_home_draft,
        name="edit_home_draft",
    ),
    path(
        "dashboard/rentals/<uuid:listing_id>/",
        views.rental_draft_detail,
        name="rental_draft_detail",
    ),
    path(
        "dashboard/rentals/<uuid:listing_id>/edit/",
        views.edit_rental_draft,
        name="edit_rental_draft",
    ),
    path(
        "dashboard/ag-equipment/<uuid:listing_id>/",
        views.ag_equipment_draft_detail,
        name="ag_equipment_draft_detail",
    ),
    path(
        "dashboard/ag-equipment/<uuid:listing_id>/edit/",
        views.edit_ag_equipment_draft,
        name="edit_ag_equipment_draft",
    ),
    path(
        "dashboard/livestock/<uuid:listing_id>/",
        views.livestock_draft_detail,
        name="livestock_draft_detail",
    ),
    path(
        "dashboard/livestock/<uuid:listing_id>/edit/",
        views.edit_livestock_draft,
        name="edit_livestock_draft",
    ),
    path(
        "dashboard/pasture/<uuid:listing_id>/",
        views.pasture_draft_detail,
        name="pasture_draft_detail",
    ),
    path(
        "dashboard/pasture/<uuid:listing_id>/edit/",
        views.edit_pasture_draft,
        name="edit_pasture_draft",
    ),
    path(
        "dashboard/home-garden/<uuid:listing_id>/",
        views.home_garden_draft_detail,
        name="home_garden_draft_detail",
    ),
    path(
        "dashboard/home-garden/<uuid:listing_id>/edit/",
        views.edit_home_garden_draft,
        name="edit_home_garden_draft",
    ),
    path(
        "dashboard/appliances/<uuid:listing_id>/",
        views.appliances_draft_detail,
        name="appliances_draft_detail",
    ),
    path(
        "dashboard/appliances/<uuid:listing_id>/edit/",
        views.edit_appliances_draft,
        name="edit_appliances_draft",
    ),
    path(
        "dashboard/drafts/<uuid:listing_id>/",
        views.draft_detail,
        name="draft_detail",
    ),
    path(
        "dashboard/drafts/<uuid:listing_id>/edit/",
        views.edit_auto_draft,
        name="edit_auto_draft",
    ),
    path(
        "dashboard/drafts/<uuid:listing_id>/media/",
        views.media_manage,
        name="media_manage",
    ),
    path(
        "dashboard/drafts/<uuid:listing_id>/media/upload/",
        views.upload_listing_image,
        name="upload_listing_image",
    ),
    path(
        "dashboard/drafts/<uuid:listing_id>/media/reorder/",
        views.reorder_listing_images,
        name="reorder_listing_images",
    ),
    path(
        "dashboard/drafts/<uuid:listing_id>/media/<uuid:image_id>/delete/",
        views.delete_listing_image_view,
        name="delete_listing_image",
    ),
    path(
        "dashboard/drafts/<uuid:listing_id>/media/<uuid:image_id>/<str:rendition>/",
        views.private_listing_image,
        name="private_listing_image",
    ),
]
