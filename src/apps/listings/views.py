from __future__ import annotations

from contextlib import suppress
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import SellerProfile, User
from apps.catalog.selectors import (
    active_postable_categories,
    automatic_primary_category,
    category_hierarchy_label,
)
from apps.locations.models import County, State, ZipCountyReference
from apps.locations.zip_county import zip_county_candidates
from apps.policies.services import active_listing_documents

from .forms import (
    AgEquipmentDetailsForm,
    AgEquipmentListingForm,
    AppliancesListingForm,
    AutoDetailsForm,
    AutoListingForm,
    GenericListingForm,
    HomeDetailsForm,
    HomeGardenListingForm,
    HomeGoodsDetailsForm,
    HomeListingForm,
    ListingCategoryForm,
    ListingTaxonomyAndFactsForm,
    LivestockDetailsForm,
    LivestockListingForm,
    PastureDetailsForm,
    PastureListingForm,
    ProfileAttributesForm,
    RentalDetailsForm,
    RentalListingForm,
    WantedListingForm,
)
from .models import (
    GenericListingDetails,
    ListingImage,
    ListingImageState,
    ListingIntent,
    ListingStatus,
    ModerationActionType,
    ModerationReasonCode,
)
from .selectors import (
    get_owned_listing,
    get_seller_listings,
    get_user_favorites,
    moderation_queue,
)
from .services import (
    accept_policies_and_submit_listing,
    begin_image_upload,
    create_unified_draft,
    create_wanted_draft,
    delete_listing_image,
    finalize_image_upload,
    image_policy_for_listing,
    moderate_listing,
    reorder_images,
    submit_listing,
    toggle_favorite,
    transition_owned_listing,
    update_ag_equipment_draft,
    update_appliances_draft,
    update_auto_draft,
    update_generic_draft,
    update_home_draft,
    update_home_garden_draft,
    update_livestock_draft,
    update_pasture_draft,
    update_rental_draft,
    update_unified_listing,
)
from .services import create_ag_equipment_draft as create_ag_equipment_draft_service
from .services import create_appliances_draft as create_appliances_draft_service
from .services import create_auto_draft as create_auto_draft_service
from .services import create_generic_draft as create_generic_draft_service
from .services import create_home_draft as create_home_draft_service
from .services import create_home_garden_draft as create_home_garden_draft_service
from .services import create_livestock_draft as create_livestock_draft_service
from .services import create_pasture_draft as create_pasture_draft_service
from .services import create_rental_draft as create_rental_draft_service
from .workflows import resolve_listing_workflow

POSTAL_CODE_LENGTH = 5
COUNTY_SEARCH_RESULT_LIMIT = 20
COUNTY_SEARCH_QUERY_MAX_LENGTH = 80
STATE_SEARCH_RESULT_LIMIT = 20
STATE_SEARCH_QUERY_MAX_LENGTH = 80


def _seller_profile_or_redirect(request: HttpRequest) -> SellerProfile | HttpResponse:
    assert isinstance(request.user, User)
    try:
        return request.user.seller_profile
    except SellerProfile.DoesNotExist:
        return redirect("accounts:seller_profile")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listings = get_seller_listings(seller=profile_or_response)
    return render(
        request,
        "listings/dashboard.html",
        {
            "listings": listings,
            "status_counts": {
                status: listings.filter(status=status).count()
                for status, _label in ListingStatus.choices
            },
        },
    )


@login_required
def create_generic_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    if request.method == "POST":
        form = GenericListingForm(request.POST)
        if form.is_valid():
            values = form.cleaned_data.copy()
            values.pop("vertical")
            additional_counties = list(values.pop("additional_counties"))
            generic_values = {
                field: values.pop(field)
                for field in ("price_mode", "postal_code", "street_address")
            }
            listing = create_generic_draft_service(
                seller=profile_or_response,
                listing_values=values,
                generic_values=generic_values,
                additional_counties=additional_counties,
            )
            return redirect("listings:generic_draft_detail", listing_id=listing.id)
    else:
        form = GenericListingForm(initial={"currency": "USD"})
    return render(request, "listings/generic_draft_form.html", {"form": form})


def _typed_forms_for_workflow(
    *,
    workflow: str,
    data: Any = None,
    listing_instance: Any = None,
    details_instance: Any = None,
) -> tuple[Any, Any]:
    pairs = {
        "auto": (AutoListingForm, AutoDetailsForm),
        "home": (HomeListingForm, HomeDetailsForm),
        "rental": (RentalListingForm, RentalDetailsForm),
        "ag_equipment": (AgEquipmentListingForm, AgEquipmentDetailsForm),
        "livestock": (LivestockListingForm, LivestockDetailsForm),
        "pasture": (PastureListingForm, PastureDetailsForm),
        "home_goods": (HomeGardenListingForm, HomeGoodsDetailsForm),
    }
    listing_class, detail_class = pairs[workflow]
    return (
        listing_class(data, instance=listing_instance),
        detail_class(data, instance=details_instance),
    )


def _typed_workflow_post_data(data: Any) -> Any:
    """Carry common first-step values into the typed form without trusting a workflow."""

    typed_data = data.copy()
    asking_price = str(data.get("asking_price", "")).strip()
    if (
        not typed_data.get("price_minor")
        and data.get("price_mode") in {"fixed", "negotiable"}
        and asking_price
    ):
        with suppress(InvalidOperation, ValueError):
            typed_data["price_minor"] = str(int(Decimal(asking_price) * 100))
    if not typed_data.get("currency"):
        typed_data["currency"] = "USD"
    return typed_data


def _allowlisted_form_initial(*, data: Any, form: Any) -> dict[str, Any]:
    """Retain display values without binding or validating an advance request."""

    initial: dict[str, Any] = {}
    for name, field in form.fields.items():
        values = data.getlist(name)
        if not values:
            continue
        initial[name] = (
            values if getattr(field.widget, "allow_multiple_selected", False) else values[-1]
        )
    return initial


def _is_category_only_advance(*, data: Any) -> bool:
    """Support old no-JavaScript category submissions without masking a save."""

    return not any(
        key not in {"csrfmiddlewaretoken", "vertical", "category", "show_fields"} for key in data
    )


def _is_workflow_advance(*, data: Any, category_is_valid: bool) -> bool:
    return data.get("show_fields") == "1" or (
        data.get("save_listing_draft") != "1"
        and category_is_valid
        and _is_category_only_advance(data=data)
    )


def _unbound_workflow_forms(
    *,
    workflow: Any,
    category: Any,
    data: Any,
    wanted: bool = False,
) -> tuple[Any, Any, Any, Any]:
    """Build workflow controls from allowlisted initial values, never POST-bound."""

    listing_form = details_form = profile_form = None
    if workflow.typed:
        listing_form, details_form = _typed_forms_for_workflow(workflow=workflow.key)
        typed_data = _typed_workflow_post_data(data)
        listing_form.initial.update(_allowlisted_form_initial(data=typed_data, form=listing_form))
        details_form.initial.update(_allowlisted_form_initial(data=data, form=details_form))
    else:
        blank_listing_form = WantedListingForm() if wanted else GenericListingForm()
        listing_initial = _allowlisted_form_initial(data=data, form=blank_listing_form)
        listing_initial.update({"vertical": category.vertical_id, "category": category.id})
        listing_form = (WantedListingForm if wanted else GenericListingForm)(
            initial=listing_initial
        )
        profile = getattr(category, "posting_profile", None)
        if not wanted and profile is not None and profile.is_active:
            profile_form = ProfileAttributesForm(profile=profile)
            profile_form.initial.update(_allowlisted_form_initial(data=data, form=profile_form))

    # The resolver, not POST data, owns these workflow-selection values.
    listing_form.initial["vertical"] = category.vertical_id
    listing_form.initial["category"] = category.id
    taxonomy_form = ListingTaxonomyAndFactsForm(
        vertical=category.vertical,
        primary_category=category,
        enforce_seller_tag=False,
    )
    taxonomy_form.initial.update(_allowlisted_form_initial(data=data, form=taxonomy_form))
    return listing_form, details_form, profile_form, taxonomy_form


@login_required
def create_listing(request: HttpRequest) -> HttpResponse:  # noqa: PLR0912, PLR0915
    """One server-resolved create workflow for typed and catalog-profile listings."""

    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    # Start with the established full-page form so sellers retain the common
    # location, county, and price controls immediately. Its enhanced category
    # control posts back here to resolve and render the matching typed/profile
    # fields before a draft can be saved.
    wanted = bool(
        request.resolver_match and request.resolver_match.url_name == "create_wanted_listing"
    )
    if request.method == "GET":
        form = (WantedListingForm if wanted else GenericListingForm)(initial={"currency": "USD"})
        return render(
            request,
            "listings/generic_draft_form.html",
            {
                "form": form,
                "unified_create": True,
                "wanted_create": wanted,
            },
        )
    category_form = ListingCategoryForm(request.POST or None)
    selected_category = None
    workflow = None
    category_is_valid = category_form.is_valid()
    if category_is_valid:
        selected_category = category_form.cleaned_data["category"]
        workflow = resolve_listing_workflow(
            category=selected_category,
            intent=ListingIntent.WANTED if wanted else ListingIntent.OFFER,
        )
    advancing = _is_workflow_advance(data=request.POST, category_is_valid=category_is_valid)
    listing_form = details_form = profile_form = taxonomy_form = None
    if selected_category is not None and workflow is not None:
        if advancing:
            listing_form, details_form, profile_form, taxonomy_form = _unbound_workflow_forms(
                workflow=workflow,
                category=selected_category,
                data=request.POST,
                wanted=wanted,
            )
        elif workflow.typed:
            listing_form, details_form = _typed_forms_for_workflow(
                workflow=workflow.key,
                data=_typed_workflow_post_data(request.POST),
            )
        else:
            listing_data = request.POST.copy()
            listing_data["category"] = str(selected_category.id)
            listing_form = (WantedListingForm if wanted else GenericListingForm)(listing_data)
            profile = getattr(selected_category, "posting_profile", None)
            if not wanted and profile is not None and profile.is_active:
                profile_form = ProfileAttributesForm(
                    request.POST,
                    profile=profile,
                )
        if not advancing:
            taxonomy_form = ListingTaxonomyAndFactsForm(
                request.POST,
                vertical=selected_category.vertical,
                primary_category=selected_category,
            )

    if advancing:
        return render(
            request,
            "listings/create_listing.html",
            {
                "category_form": category_form,
                "listing_form": listing_form,
                "details_form": details_form,
                "profile_form": profile_form,
                "taxonomy_form": taxonomy_form,
                "workflow": workflow,
                "selected_category": selected_category,
            },
        )

    if (
        request.method == "POST"
        and selected_category is not None
        and workflow is not None
        and listing_form is not None
    ):
        valid = category_is_valid and listing_form.is_valid()
        if workflow.typed:
            valid = bool(valid and details_form is not None and details_form.is_valid())
        elif profile_form is not None:
            valid = bool(valid and profile_form.is_valid())
        valid = bool(valid and taxonomy_form is not None and taxonomy_form.is_valid())
        if valid:
            assert taxonomy_form is not None
            listing_values = listing_form.cleaned_data.copy()
            listing_values["category"] = selected_category
            if wanted:
                additional_counties = list(listing_values.pop("additional_counties"))
                generic_values = {
                    field: listing_values.pop(field)
                    for field in ("price_mode", "postal_code", "street_address")
                }
                generic_values["schema_version"] = 1
                generic_values["attributes"] = {}
                listing_values.pop("vertical", None)
                listing = create_wanted_draft(
                    seller=profile_or_response,
                    listing_values=listing_values,
                    generic_values=generic_values,
                    additional_counties=additional_counties,
                    controlled_categories=list(taxonomy_form.cleaned_data["controlled_tags"]),
                    seller_tags=taxonomy_form.cleaned_data["seller_tags"],
                    custom_fields=taxonomy_form.cleaned_data["custom_fields"],
                )
            elif workflow.typed:
                assert details_form is not None
                listing = create_unified_draft(
                    seller=profile_or_response,
                    workflow=workflow,
                    listing_values=listing_values,
                    detail_values=details_form.cleaned_data,
                    controlled_categories=list(taxonomy_form.cleaned_data["controlled_tags"]),
                    seller_tags=taxonomy_form.cleaned_data["seller_tags"],
                    custom_fields=taxonomy_form.cleaned_data["custom_fields"],
                )
            else:
                additional_counties = list(listing_values.pop("additional_counties"))
                generic_values = {
                    field: listing_values.pop(field)
                    for field in ("price_mode", "postal_code", "street_address")
                }
                generic_values["schema_version"] = (
                    profile_form.profile.version if profile_form is not None else 1
                )
                generic_values["attributes"] = profile_form.cleaned_data if profile_form else {}
                listing_values.pop("vertical", None)
                listing = create_unified_draft(
                    seller=profile_or_response,
                    workflow=workflow,
                    listing_values=listing_values,
                    detail_values={},
                    generic_values=generic_values,
                    additional_counties=additional_counties,
                    controlled_categories=list(taxonomy_form.cleaned_data["controlled_tags"]),
                    seller_tags=taxonomy_form.cleaned_data["seller_tags"],
                    custom_fields=taxonomy_form.cleaned_data["custom_fields"],
                )
            return redirect("listings:owner_listing_detail", listing_id=listing.id)

    return render(
        request,
        "listings/create_listing.html",
        {
            "category_form": category_form,
            "listing_form": listing_form,
            "details_form": details_form,
            "profile_form": profile_form,
            "taxonomy_form": taxonomy_form,
            "workflow": workflow,
            "selected_category": selected_category,
            "wanted_create": wanted,
        },
    )


def _details_for_workflow(*, listing: Any, workflow: str) -> Any:
    relations = {
        "auto": "auto_details",
        "home": "home_details",
        "rental": "rental_details",
        "ag_equipment": "ag_equipment_details",
        "livestock": "livestock_details",
        "pasture": "pasture_details",
        "home_goods": "home_goods_details",
    }
    try:
        return getattr(listing, relations[workflow])
    except (KeyError, ObjectDoesNotExist) as error:
        raise Http404("Listing detail not found.") from error


@login_required
def edit_listing(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    """Edit an existing listing through its persisted, server-resolved workflow."""
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    workflow = resolve_listing_workflow(category=listing.category, intent=listing.intent)
    category_form = ListingCategoryForm(
        initial={"vertical": listing.vertical_id, "category": listing.category_id},
    )
    # A listing's primary category is its persisted workflow contract. The edit
    # endpoint intentionally does not bind category input from the request.
    taxonomy_initial = {
        "controlled_tags": [tag.category_id for tag in listing.controlled_tags.all()],
        **{f"seller_tag_{index}": tag.value for index, tag in enumerate(listing.seller_tags.all())},
        **{
            f"custom_field_label_{index}": field.label
            for index, field in enumerate(listing.custom_fields.all())
        },
        **{
            f"custom_field_value_{index}": field.value
            for index, field in enumerate(listing.custom_fields.all())
        },
    }
    taxonomy_form = ListingTaxonomyAndFactsForm(
        request.POST or None,
        initial=taxonomy_initial,
        vertical=listing.vertical,
        primary_category=listing.category,
    )
    profile_form = None
    if workflow.typed:
        details = _details_for_workflow(listing=listing, workflow=workflow.key)
        listing_form, details_form = _typed_forms_for_workflow(
            workflow=workflow.key,
            data=request.POST or None,
            listing_instance=listing,
            details_instance=details,
        )
        listing_form.fields["category"].disabled = True
    else:
        details = listing.generic_details
        generic_initial = {
            "vertical": listing.vertical_id,
            "category": listing.category_id,
            "price_mode": details.price_mode,
            "postal_code": details.postal_code,
            "street_address": details.street_address,
            "additional_counties": list(
                listing.additional_counties.values_list("county_id", flat=True)
            ),
        }
        listing_form_class = (
            WantedListingForm if listing.intent == ListingIntent.WANTED else GenericListingForm
        )
        listing_form = listing_form_class(
            request.POST or None,
            instance=listing,
            initial=generic_initial,
        )
        listing_form.fields["vertical"].disabled = True
        listing_form.fields["category"].disabled = True
        details_form = None
        profile = getattr(listing.category, "posting_profile", None)
        if listing.intent != ListingIntent.WANTED and profile is not None and profile.is_active:
            profile_form = ProfileAttributesForm(
                request.POST or None,
                initial=details.attributes,
                profile=profile,
            )

    if request.method == "POST":
        valid = bool(listing_form.is_valid() and taxonomy_form.is_valid())
        if workflow.typed:
            valid = bool(valid and details_form is not None and details_form.is_valid())
        elif profile_form is not None:
            valid = bool(valid and profile_form.is_valid())
        if valid:
            listing_values = listing_form.cleaned_data.copy()
            listing_values["category"] = listing.category
            if workflow.typed:
                assert details_form is not None
                updated = update_unified_listing(
                    listing_id=listing.id,
                    seller=profile_or_response,
                    workflow=workflow,
                    listing_values=listing_values,
                    detail_values=details_form.cleaned_data,
                    controlled_categories=list(taxonomy_form.cleaned_data["controlled_tags"]),
                    seller_tags=taxonomy_form.cleaned_data["seller_tags"],
                    custom_fields=taxonomy_form.cleaned_data["custom_fields"],
                )
            else:
                additional_counties = list(listing_values.pop("additional_counties"))
                generic_values = {
                    field: listing_values.pop(field)
                    for field in ("price_mode", "postal_code", "street_address")
                }
                listing_values.pop("vertical", None)
                generic_values["schema_version"] = (
                    profile_form.profile.version if profile_form is not None else 1
                )
                generic_values["attributes"] = profile_form.cleaned_data if profile_form else {}
                updated = update_unified_listing(
                    listing_id=listing.id,
                    seller=profile_or_response,
                    workflow=workflow,
                    listing_values=listing_values,
                    detail_values={},
                    generic_values=generic_values,
                    additional_counties=additional_counties,
                    controlled_categories=list(taxonomy_form.cleaned_data["controlled_tags"]),
                    seller_tags=taxonomy_form.cleaned_data["seller_tags"],
                    custom_fields=taxonomy_form.cleaned_data["custom_fields"],
                )
            return redirect("listings:owner_listing_detail", listing_id=updated.id)

    return render(
        request,
        "listings/create_listing.html",
        {
            "category_form": category_form,
            "listing_form": listing_form,
            "details_form": details_form,
            "profile_form": profile_form,
            "taxonomy_form": taxonomy_form,
            "workflow": workflow,
            "editing": True,
            "listing": listing,
            "selected_category": listing.category,
        },
    )


@login_required
def edit_generic_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    try:
        details = listing.generic_details
    except GenericListingDetails.DoesNotExist as error:
        raise Http404("Listing not found.") from error
    initial = {
        "vertical": listing.vertical_id,
        "price_mode": details.price_mode,
        "postal_code": details.postal_code,
        "street_address": details.street_address,
        "additional_counties": list(
            listing.additional_counties.values_list("county_id", flat=True)
        ),
    }
    if request.method == "POST":
        form = GenericListingForm(request.POST, instance=listing, initial=initial)
        if form.is_valid():
            values = form.cleaned_data.copy()
            values.pop("vertical")
            additional_counties = list(values.pop("additional_counties"))
            generic_values = {
                field: values.pop(field)
                for field in ("price_mode", "postal_code", "street_address")
            }
            listing = update_generic_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=values,
                generic_values=generic_values,
                additional_counties=additional_counties,
            )
            return redirect("listings:generic_draft_detail", listing_id=listing.id)
    else:
        form = GenericListingForm(instance=listing, initial=initial)
    return render(request, "listings/generic_draft_form.html", {"form": form, "editing": True})


@login_required
@login_required
def generic_county_candidates(request: HttpRequest) -> JsonResponse:
    """Allowlisted enhancement endpoint; the form remains authoritative without JavaScript."""

    state_id = request.GET.get("state", "")
    postal_code = request.GET.get("postal_code", "").strip()
    county_query = request.GET.get("q")
    if (
        not state_id.isdigit()
        or not State.objects.filter(pk=int(state_id), is_active=True).exists()
    ):
        return JsonResponse(
            {
                "counties": [],
                "status": "invalid_state",
                "crosswalk_loaded": ZipCountyReference.objects.exists(),
            }
        )
    selected_state_id = int(state_id)
    counties = County.objects.filter(state_id=selected_state_id, is_active=True).order_by("name")
    if county_query is not None:
        county_query = county_query.strip()
        if not county_query or len(county_query) > COUNTY_SEARCH_QUERY_MAX_LENGTH:
            return JsonResponse(
                {
                    "counties": [],
                    "status": "invalid_query",
                    "crosswalk_loaded": ZipCountyReference.objects.exists(),
                }
            )
        counties = counties.filter(name__icontains=county_query)[:COUNTY_SEARCH_RESULT_LIMIT]
    zip_is_valid = len(postal_code) == POSTAL_CODE_LENGTH and postal_code.isdigit()
    verified_ids = {
        county.id
        for county in (
            zip_county_candidates(postal_code=postal_code, state_id=selected_state_id)
            if zip_is_valid
            else []
        )
    }
    crosswalk_loaded = ZipCountyReference.objects.exists()
    status = "state_counties"
    if zip_is_valid:
        status = "zip_verified" if verified_ids else "zip_no_candidates"
    return JsonResponse(
        {
            "counties": [
                {
                    "id": county.id,
                    "name": county.name,
                    "verified": county.id in verified_ids,
                }
                for county in counties
            ],
            "status": status,
            "crosswalk_loaded": crosswalk_loaded,
        }
    )


@login_required
def state_candidates(request: HttpRequest) -> JsonResponse:
    """Return a bounded active-only state list for the authenticated form enhancement."""

    query = request.GET.get("q", "").strip()
    if len(query) > STATE_SEARCH_QUERY_MAX_LENGTH:
        return JsonResponse({"states": []})
    states = State.objects.filter(is_active=True).order_by("name")
    if query:
        states = states.filter(name__icontains=query) | states.filter(usps_code__icontains=query)
    states = states.order_by("name")[:STATE_SEARCH_RESULT_LIMIT]
    return JsonResponse(
        {
            "states": [
                {"id": state.id, "name": state.name, "code": state.usps_code} for state in states
            ]
        }
    )


@login_required
def generic_categories(request: HttpRequest) -> JsonResponse:
    vertical_id = request.GET.get("vertical", "")
    if not vertical_id.isdigit():
        return JsonResponse({"categories": []})
    categories = active_postable_categories(vertical_id=int(vertical_id)).order_by(
        "display_order", "name"
    )
    first_category = categories.first()
    automatic_category = (
        automatic_primary_category(vertical=first_category.vertical)
        if first_category is not None
        else None
    )
    return JsonResponse(
        {
            "categories": [
                {"id": category.id, "name": category_hierarchy_label(category=category)}
                for category in categories
            ],
            "automatic_category_id": automatic_category.id if automatic_category else None,
        }
    )


@login_required
def generic_draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    try:
        details = listing.generic_details
    except GenericListingDetails.DoesNotExist as error:
        raise Http404("Listing not found.") from error
    return render(
        request,
        "listings/generic_draft_detail.html",
        {
            "listing": listing,
            "details": details,
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


@login_required
@require_POST
def listing_action(request: HttpRequest, listing_id: UUID, action: str) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    try:
        transition_owned_listing(listing_id=listing_id, seller=profile_or_response, action=action)
        messages.success(request, "Listing updated.")
    except (PermissionDenied, ValidationError):
        messages.error(request, "That listing cannot take this action.")
    return redirect("listings:dashboard")


@login_required
@require_POST
def favorite_toggle(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    try:
        saved = toggle_favorite(listing_id=listing_id, user=request.user)  # type: ignore[arg-type]
        messages.success(request, "Listing saved." if saved else "Listing removed from favorites.")
    except ValidationError as error:
        raise Http404("Listing not found.") from error
    return redirect(request.POST.get("next") or "listings:favorites")


@login_required
def favorites(request: HttpRequest) -> HttpResponse:
    assert isinstance(request.user, User)
    return render(
        request,
        "listings/favorites.html",
        {"listings": get_user_favorites(user=request.user)},
    )


def _draft_form_context(
    *, listing_form: AutoListingForm, auto_form: AutoDetailsForm, heading: str
) -> dict[str, Any]:
    return {"listing_form": listing_form, "auto_form": auto_form, "heading": heading}


def _media_context(*, listing: Any) -> dict[str, Any]:
    required_count, maximum_count = image_policy_for_listing(listing=listing)
    return {
        "images": listing.images.filter(state=ListingImageState.READY).order_by("ordering"),
        "required_image_count": required_count,
        "maximum_image_count": maximum_count,
    }


def _submission_context() -> dict[str, Any]:
    return {"required_listing_policies": active_listing_documents()}


def _owner_detail_url_name(*, listing: Any) -> str:
    """Resolve the actual owner detail from its attached detail model, not status."""
    try:
        _details = listing.generic_details
        return "listings:generic_draft_detail"
    except GenericListingDetails.DoesNotExist:
        pass
    routes = (
        ("home_details", "listings:home_draft_detail"),
        ("rental_details", "listings:rental_draft_detail"),
        ("ag_equipment_details", "listings:ag_equipment_draft_detail"),
        ("livestock_details", "listings:livestock_draft_detail"),
        ("pasture_details", "listings:pasture_draft_detail"),
        ("home_goods_details", "listings:home_garden_draft_detail"),
        ("auto_details", "listings:draft_detail"),
    )
    for relation, route_name in routes:
        try:
            getattr(listing, relation)
        except ObjectDoesNotExist:
            continue
        if relation == "home_goods_details" and listing.vertical.slug == "appliances":
            return "listings:appliances_draft_detail"
        return route_name
    raise Http404("Listing detail not found.")


@login_required
def owner_listing_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    try:
        profile_attributes = listing.generic_details.attributes.items()
    except GenericListingDetails.DoesNotExist:
        profile_attributes = ()
    return render(
        request,
        "listings/owner_listing_detail.html",
        {
            "listing": listing,
            "secondary_controlled_tags": listing.controlled_tags.exclude(
                category_id=listing.category_id
            ).select_related("category"),
            "profile_attributes": profile_attributes,
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


def _media_return(listing_id: UUID) -> HttpResponse:
    return redirect("listings:media_manage", listing_id=listing_id)


@login_required
def create_auto_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response

    if request.method == "POST":
        listing_form = AutoListingForm(request.POST)
        auto_form = AutoDetailsForm(request.POST)
        if listing_form.is_valid() and auto_form.is_valid():
            listing = create_auto_draft_service(
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                auto_values=auto_form.cleaned_data,
            )
            return redirect("listings:draft_detail", listing_id=listing.id)
    else:
        listing_form = AutoListingForm(initial={"currency": "USD"})
        auto_form = AutoDetailsForm()
    return render(
        request,
        "listings/auto_draft_form.html",
        _draft_form_context(
            listing_form=listing_form, auto_form=auto_form, heading="Create auto draft"
        ),
    )


@login_required
def edit_auto_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)

    if request.method == "POST":
        listing_form = AutoListingForm(request.POST, instance=listing)
        auto_form = AutoDetailsForm(request.POST, instance=listing.auto_details)
        if listing_form.is_valid() and auto_form.is_valid():
            listing = update_auto_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                auto_values=auto_form.cleaned_data,
            )
            return redirect("listings:draft_detail", listing_id=listing.id)
    else:
        listing_form = AutoListingForm(instance=listing)
        auto_form = AutoDetailsForm(instance=listing.auto_details)
    return render(
        request,
        "listings/auto_draft_form.html",
        _draft_form_context(
            listing_form=listing_form, auto_form=auto_form, heading="Edit auto draft"
        ),
    )


@login_required
def draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/draft_detail.html",
        {"listing": listing, **_media_context(listing=listing), **_submission_context()},
    )


@login_required
def create_home_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    if request.method == "POST":
        listing_form = HomeListingForm(request.POST)
        details_form = HomeDetailsForm(request.POST)
        if listing_form.is_valid() and details_form.is_valid():
            listing = create_home_draft_service(
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                home_values=details_form.cleaned_data,
            )
            return redirect("listings:home_draft_detail", listing_id=listing.id)
    else:
        listing_form = HomeListingForm(initial={"currency": "USD"})
        details_form = HomeDetailsForm()
    return render(
        request,
        "listings/property_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Create home draft",
            "draft_kind": "Home",
        },
    )


@login_required
def edit_home_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    if request.method == "POST":
        listing_form = HomeListingForm(request.POST, instance=listing)
        details_form = HomeDetailsForm(request.POST, instance=listing.home_details)
        if listing_form.is_valid() and details_form.is_valid():
            listing = update_home_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                home_values=details_form.cleaned_data,
            )
            return redirect("listings:home_draft_detail", listing_id=listing.id)
    else:
        listing_form = HomeListingForm(instance=listing)
        details_form = HomeDetailsForm(instance=listing.home_details)
    return render(
        request,
        "listings/property_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Edit home draft",
            "draft_kind": "Home",
        },
    )


@login_required
def home_draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/home_draft_detail.html",
        {
            "listing": listing,
            "details": listing.home_details,
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


@login_required
def create_rental_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    if request.method == "POST":
        listing_form = RentalListingForm(request.POST)
        details_form = RentalDetailsForm(request.POST)
        if listing_form.is_valid() and details_form.is_valid():
            listing = create_rental_draft_service(
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                rental_values=details_form.cleaned_data,
            )
            return redirect("listings:rental_draft_detail", listing_id=listing.id)
    else:
        listing_form = RentalListingForm(initial={"currency": "USD"})
        details_form = RentalDetailsForm(initial={"security_deposit_minor": 0})
    return render(
        request,
        "listings/property_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Create rental draft",
            "draft_kind": "Rental",
        },
    )


@login_required
def edit_rental_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    if request.method == "POST":
        listing_form = RentalListingForm(request.POST, instance=listing)
        details_form = RentalDetailsForm(request.POST, instance=listing.rental_details)
        if listing_form.is_valid() and details_form.is_valid():
            listing = update_rental_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                rental_values=details_form.cleaned_data,
            )
            return redirect("listings:rental_draft_detail", listing_id=listing.id)
    else:
        listing_form = RentalListingForm(instance=listing)
        details_form = RentalDetailsForm(instance=listing.rental_details)
    return render(
        request,
        "listings/property_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Edit rental draft",
            "draft_kind": "Rental",
        },
    )


@login_required
def rental_draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/rental_draft_detail.html",
        {
            "listing": listing,
            "details": listing.rental_details,
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


@login_required
def create_ag_equipment_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    if request.method == "POST":
        listing_form = AgEquipmentListingForm(request.POST)
        details_form = AgEquipmentDetailsForm(request.POST)
        if listing_form.is_valid() and details_form.is_valid():
            listing = create_ag_equipment_draft_service(
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                ag_equipment_values=details_form.cleaned_data,
            )
            return redirect("listings:ag_equipment_draft_detail", listing_id=listing.id)
    else:
        listing_form = AgEquipmentListingForm(initial={"currency": "USD"})
        details_form = AgEquipmentDetailsForm()
    return render(
        request,
        "listings/rural_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Create agricultural equipment draft",
            "draft_kind": "Agricultural equipment",
        },
    )


@login_required
def edit_ag_equipment_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    if request.method == "POST":
        listing_form = AgEquipmentListingForm(request.POST, instance=listing)
        details_form = AgEquipmentDetailsForm(request.POST, instance=listing.ag_equipment_details)
        if listing_form.is_valid() and details_form.is_valid():
            listing = update_ag_equipment_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                ag_equipment_values=details_form.cleaned_data,
            )
            return redirect("listings:ag_equipment_draft_detail", listing_id=listing.id)
    else:
        listing_form = AgEquipmentListingForm(instance=listing)
        details_form = AgEquipmentDetailsForm(instance=listing.ag_equipment_details)
    return render(
        request,
        "listings/rural_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Edit agricultural equipment draft",
            "draft_kind": "Agricultural equipment",
        },
    )


@login_required
def ag_equipment_draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/ag_equipment_draft_detail.html",
        {
            "listing": listing,
            "details": listing.ag_equipment_details,
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


@login_required
def create_livestock_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    if request.method == "POST":
        listing_form = LivestockListingForm(request.POST)
        details_form = LivestockDetailsForm(request.POST)
        if listing_form.is_valid() and details_form.is_valid():
            listing = create_livestock_draft_service(
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                livestock_values=details_form.cleaned_data,
            )
            return redirect("listings:livestock_draft_detail", listing_id=listing.id)
    else:
        listing_form = LivestockListingForm(initial={"currency": "USD"})
        details_form = LivestockDetailsForm()
    return render(
        request,
        "listings/rural_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Create livestock draft",
            "draft_kind": "Livestock",
        },
    )


@login_required
def edit_livestock_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    if request.method == "POST":
        listing_form = LivestockListingForm(request.POST, instance=listing)
        details_form = LivestockDetailsForm(request.POST, instance=listing.livestock_details)
        if listing_form.is_valid() and details_form.is_valid():
            listing = update_livestock_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                livestock_values=details_form.cleaned_data,
            )
            return redirect("listings:livestock_draft_detail", listing_id=listing.id)
    else:
        listing_form = LivestockListingForm(instance=listing)
        details_form = LivestockDetailsForm(instance=listing.livestock_details)
    return render(
        request,
        "listings/rural_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Edit livestock draft",
            "draft_kind": "Livestock",
        },
    )


@login_required
def livestock_draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/livestock_draft_detail.html",
        {
            "listing": listing,
            "details": listing.livestock_details,
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


@login_required
def create_pasture_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    if request.method == "POST":
        listing_form = PastureListingForm(request.POST)
        details_form = PastureDetailsForm(request.POST)
        if listing_form.is_valid() and details_form.is_valid():
            listing = create_pasture_draft_service(
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                pasture_values=details_form.cleaned_data,
            )
            return redirect("listings:pasture_draft_detail", listing_id=listing.id)
    else:
        listing_form = PastureListingForm(initial={"currency": "USD"})
        details_form = PastureDetailsForm()
    return render(
        request,
        "listings/rural_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Create pasture draft",
            "draft_kind": "Pasture",
        },
    )


@login_required
def edit_pasture_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    if request.method == "POST":
        listing_form = PastureListingForm(request.POST, instance=listing)
        details_form = PastureDetailsForm(request.POST, instance=listing.pasture_details)
        if listing_form.is_valid() and details_form.is_valid():
            listing = update_pasture_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                pasture_values=details_form.cleaned_data,
            )
            return redirect("listings:pasture_draft_detail", listing_id=listing.id)
    else:
        listing_form = PastureListingForm(instance=listing)
        details_form = PastureDetailsForm(instance=listing.pasture_details)
    return render(
        request,
        "listings/rural_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Edit pasture draft",
            "draft_kind": "Pasture",
        },
    )


@login_required
def pasture_draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/pasture_draft_detail.html",
        {
            "listing": listing,
            "details": listing.pasture_details,
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


@login_required
def create_home_garden_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    if request.method == "POST":
        listing_form = HomeGardenListingForm(request.POST)
        details_form = HomeGoodsDetailsForm(request.POST)
        if listing_form.is_valid() and details_form.is_valid():
            listing = create_home_garden_draft_service(
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                home_goods_values=details_form.cleaned_data,
            )
            return redirect("listings:home_garden_draft_detail", listing_id=listing.id)
    else:
        listing_form = HomeGardenListingForm(initial={"currency": "USD"})
        details_form = HomeGoodsDetailsForm()
    return render(
        request,
        "listings/home_goods_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Create Home & Garden draft",
            "draft_kind": "Home & Garden",
        },
    )


@login_required
def edit_home_garden_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    if request.method == "POST":
        listing_form = HomeGardenListingForm(request.POST, instance=listing)
        details_form = HomeGoodsDetailsForm(request.POST, instance=listing.home_goods_details)
        if listing_form.is_valid() and details_form.is_valid():
            listing = update_home_garden_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                home_goods_values=details_form.cleaned_data,
            )
            return redirect("listings:home_garden_draft_detail", listing_id=listing.id)
    else:
        listing_form = HomeGardenListingForm(instance=listing)
        details_form = HomeGoodsDetailsForm(instance=listing.home_goods_details)
    return render(
        request,
        "listings/home_goods_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Edit Home & Garden draft",
            "draft_kind": "Home & Garden",
        },
    )


@login_required
def home_garden_draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/home_goods_draft_detail.html",
        {
            "listing": listing,
            "details": listing.home_goods_details,
            "draft_kind": "Home & Garden",
            "edit_url_name": "listings:edit_listing",
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


@login_required
def create_appliances_draft(request: HttpRequest) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    if request.method == "POST":
        listing_form = AppliancesListingForm(request.POST)
        details_form = HomeGoodsDetailsForm(request.POST)
        if listing_form.is_valid() and details_form.is_valid():
            listing = create_appliances_draft_service(
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                home_goods_values=details_form.cleaned_data,
            )
            return redirect("listings:appliances_draft_detail", listing_id=listing.id)
    else:
        listing_form = AppliancesListingForm(initial={"currency": "USD"})
        details_form = HomeGoodsDetailsForm()
    return render(
        request,
        "listings/home_goods_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Create Appliances draft",
            "draft_kind": "Appliances",
        },
    )


@login_required
def edit_appliances_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    if request.method == "POST":
        listing_form = AppliancesListingForm(request.POST, instance=listing)
        details_form = HomeGoodsDetailsForm(request.POST, instance=listing.home_goods_details)
        if listing_form.is_valid() and details_form.is_valid():
            listing = update_appliances_draft(
                listing_id=listing.id,
                seller=profile_or_response,
                listing_values=listing_form.cleaned_data,
                home_goods_values=details_form.cleaned_data,
            )
            return redirect("listings:appliances_draft_detail", listing_id=listing.id)
    else:
        listing_form = AppliancesListingForm(instance=listing)
        details_form = HomeGoodsDetailsForm(instance=listing.home_goods_details)
    return render(
        request,
        "listings/home_goods_draft_form.html",
        {
            "listing_form": listing_form,
            "details_form": details_form,
            "heading": "Edit Appliances draft",
            "draft_kind": "Appliances",
        },
    )


@login_required
def appliances_draft_detail(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/home_goods_draft_detail.html",
        {
            "listing": listing,
            "details": listing.home_goods_details,
            "draft_kind": "Appliances",
            "edit_url_name": "listings:edit_listing",
            **_media_context(listing=listing),
            **_submission_context(),
        },
    )


@login_required
def media_manage(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return render(
        request,
        "listings/media_manage.html",
        {"listing": listing, **_media_context(listing=listing)},
    )


@login_required
def upload_listing_image(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    uploaded_file = request.FILES.get("image")
    if uploaded_file is None:
        messages.error(request, "Choose an image to upload.")
        return _media_return(listing_id)
    try:
        session = begin_image_upload(
            listing_id=listing_id,
            seller=profile_or_response,
            original_filename=uploaded_file.name or "",
        )
        finalize_image_upload(
            session_id=session.id,
            seller=profile_or_response,
            uploaded_file=uploaded_file,
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return _media_return(listing_id)


@login_required
def reorder_listing_images(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    try:
        image_ids = request.POST.getlist("image_id")
        orders = [int(value) for value in request.POST.getlist("order")]
        if len(image_ids) != len(orders) or set(orders) != set(range(1, len(orders) + 1)):
            raise ValidationError("Use each image position exactly once.")
        reorder_images(
            listing_id=listing_id,
            seller=profile_or_response,
            image_ids=[
                UUID(image_id) for _order, image_id in sorted(zip(orders, image_ids, strict=True))
            ],
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    except (TypeError, ValueError):
        messages.error(request, "Use each image position exactly once.")
    return _media_return(listing_id)


@login_required
def delete_listing_image_view(
    request: HttpRequest, listing_id: UUID, image_id: UUID
) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    try:
        delete_listing_image(
            listing_id=listing_id,
            image_id=image_id,
            seller=profile_or_response,
        )
    except ListingImage.DoesNotExist as error:
        raise Http404("Image not found.") from error
    return _media_return(listing_id)


@login_required
def private_listing_image(
    request: HttpRequest, listing_id: UUID, image_id: UUID, rendition: str
) -> HttpResponseBase:
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    try:
        image = ListingImage.objects.get(
            pk=image_id,
            listing_id=listing_id,
            state=ListingImageState.READY,
        )
    except ListingImage.DoesNotExist as error:
        raise Http404("Image not found.") from error
    if rendition not in {"full", "preview"}:
        raise Http404("Image not found.")
    response = FileResponse(
        default_storage.open(
            image.rendition_key if rendition == "preview" else image.storage_key, "rb"
        ),
        content_type=image.content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response["Content-Disposition"] = "inline"
    return response


@login_required
def submit_draft(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    profile_or_response = _seller_profile_or_redirect(request)
    if isinstance(profile_or_response, HttpResponse):
        return profile_or_response
    try:
        if active_listing_documents():
            if request.POST.get("accept_listing_policies") != "yes":
                raise ValidationError("Accept each current listing policy before submitting.")
            accept_policies_and_submit_listing(listing_id=listing_id, seller=profile_or_response)
        else:
            submit_listing(listing_id=listing_id, seller=profile_or_response)
        messages.success(request, "Your listing was submitted for moderation.")
    except PermissionDenied:
        messages.error(request, "You cannot submit this listing.")
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    listing = get_owned_listing(listing_id=listing_id, seller=profile_or_response)
    return redirect(_owner_detail_url_name(listing=listing), listing_id=listing.id)


def _moderator_or_forbidden(request: HttpRequest) -> None:
    if not request.user.has_perm("listings.moderate_listing"):
        raise PermissionDenied


@login_required
def moderation_queue_view(request: HttpRequest) -> HttpResponse:
    _moderator_or_forbidden(request)
    return render(
        request,
        "listings/moderation_queue.html",
        {
            "listings": moderation_queue(),
            "reason_codes": ModerationReasonCode.objects.filter(is_active=True),
        },
    )


@login_required
def moderate_listing_view(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    _moderator_or_forbidden(request)
    try:
        outcome = ModerationActionType(request.POST["outcome"])
        revision = int(request.POST["revision"])
        reason_code = None
        if reason_id := request.POST.get("reason_code"):
            reason_code = ModerationReasonCode.objects.get(pk=reason_id)
        moderate_listing(
            listing_id=listing_id,
            actor=request.user,  # type: ignore[arg-type]
            revision=revision,
            outcome=outcome,
            reason_code=reason_code,
            internal_note=request.POST.get("internal_note", ""),
            seller_facing_note=request.POST.get("seller_facing_note", ""),
        )
        messages.success(request, "Moderation outcome recorded.")
    except (KeyError, ValueError, ModerationReasonCode.DoesNotExist, ValidationError) as error:
        messages.error(
            request, "; ".join(getattr(error, "messages", ["Invalid moderation action."]))
        )
    return redirect("listings:moderation_queue")
