from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, TypeGuard, cast

from apps.catalog.models import PostingFieldVisibility

from .models import (
    AgEquipmentDetails,
    AutoDetails,
    HomeDetails,
    HomeGoodsDetails,
    Listing,
    ListingStatus,
    LivestockDetails,
    PastureDetails,
    RentalDetails,
    broker_attribution_is_eligible,
)


@dataclass(frozen=True)
class PublicListingPresentation:
    """Safe, template-ready public fields for a typed listing."""

    summary: str
    facts: tuple[tuple[str, str], ...]
    location: str
    address: str | None = None
    map_query: str = ""
    has_exact_public_address: bool = False
    tags: tuple[str, ...] = ()
    additional_details: tuple[tuple[str, str], ...] = ()


class ListingWithAutoDetails(Protocol):
    auto_details: AutoDetails


class ListingWithHomeDetails(Protocol):
    home_details: HomeDetails


class ListingWithRentalDetails(Protocol):
    rental_details: RentalDetails


class ListingWithAgEquipmentDetails(Protocol):
    ag_equipment_details: AgEquipmentDetails


class ListingWithPastureDetails(Protocol):
    pasture_details: PastureDetails


class ListingWithLivestockDetails(Protocol):
    livestock_details: LivestockDetails


class ListingWithHomeGoodsDetails(Protocol):
    home_goods_details: HomeGoodsDetails


def has_ag_equipment_details(listing: Listing) -> TypeGuard[ListingWithAgEquipmentDetails]:
    """Return whether a Farm & Ranch listing has equipment rather than pasture details."""
    return hasattr(listing, "ag_equipment_details")


def _public_location_query(*, listing: Listing, exact_address: str | None = None) -> str:
    """Compose the only location data that may be sent to an external map."""
    location = f"{listing.city}, {listing.county.name}, {listing.state.usps_code}"
    return f"{exact_address}, {location}" if exact_address else location


def _public_facts(*, listing: Listing, facts: list[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    """Append approved attribution only to a public eligible listing presentation."""
    if (
        listing.status == ListingStatus.PUBLISHED
        and listing.broker_name
        and broker_attribution_is_eligible(vertical=listing.vertical, category=listing.category)
    ):
        facts.append(("Broker or brokerage", listing.broker_name))
    return tuple(facts)


def _present_public_listing(*, listing: Listing) -> PublicListingPresentation:  # noqa: PLR0911, PLR0912
    """Build public display data without exposing owner or moderation fields."""
    base_location = f"{listing.city}, {listing.county.name}, {listing.state.usps_code}"
    if hasattr(listing, "generic_details"):
        try:
            profile = listing.category.posting_profile
        except AttributeError:
            profile = None
        facts = [("Price", listing.generic_details.get_price_mode_display())]
        if profile is not None:
            labels = {
                field.key: field.label
                for field in profile.fields.all()
                if field.visibility == PostingFieldVisibility.PUBLIC
            }
            facts.extend(
                (labels[key], str(value))
                for key, value in listing.generic_details.attributes.items()
                if key in labels and isinstance(value, (str, int, bool))
            )
        return PublicListingPresentation(
            summary=listing.vertical.name
            if listing.vertical.slug == "others"
            else listing.category.name,
            facts=_public_facts(listing=listing, facts=facts),
            location=base_location,
            map_query=_public_location_query(listing=listing),
        )
    match listing.vertical.slug:
        case "autos":
            auto_details = cast(ListingWithAutoDetails, listing).auto_details
            return PublicListingPresentation(
                summary=f"{auto_details.year} {auto_details.make} {auto_details.model}".strip(),
                facts=_public_facts(
                    listing=listing,
                    facts=[
                        ("Mileage", f"{auto_details.mileage:,} miles"),
                        ("Title", auto_details.get_title_status_display()),
                    ],
                ),
                location=base_location,
                map_query=_public_location_query(listing=listing),
            )
        case "real-estate":
            home_details = cast(ListingWithHomeDetails, listing).home_details
            facts = [("Type", home_details.get_property_type_display())]
            if home_details.beds is not None:
                facts.append(("Beds", str(home_details.beds)))
            if home_details.baths is not None:
                facts.append(("Baths", str(home_details.baths)))
            if home_details.square_feet is not None:
                facts.append(("Size", f"{home_details.square_feet:,} sq ft"))
            address = home_details.general_area
            if home_details.exact_address_public:
                address = ", ".join(
                    value
                    for value in (
                        home_details.street_address,
                        home_details.address_line_2,
                        home_details.postal_code,
                    )
                    if value
                )
            return PublicListingPresentation(
                summary=home_details.get_property_type_display(),
                facts=_public_facts(listing=listing, facts=facts),
                location=base_location,
                address=address,
                map_query=_public_location_query(
                    listing=listing,
                    exact_address=address if home_details.exact_address_public else None,
                ),
                has_exact_public_address=home_details.exact_address_public,
            )
        case "rentals":
            rental_details = cast(ListingWithRentalDetails, listing).rental_details
            facts = [
                ("Type", rental_details.get_rental_type_display()),
                ("Rent", f"${rental_details.monthly_rent_minor / 100:,.2f} / month"),
                ("Pets", rental_details.get_pets_policy_display()),
            ]
            address = rental_details.general_area
            if rental_details.exact_address_public:
                address = ", ".join(
                    value
                    for value in (
                        rental_details.street_address,
                        rental_details.address_line_2,
                        rental_details.postal_code,
                    )
                    if value
                )
            return PublicListingPresentation(
                summary=rental_details.get_rental_type_display(),
                facts=_public_facts(listing=listing, facts=facts),
                location=base_location,
                address=address,
                map_query=_public_location_query(
                    listing=listing,
                    exact_address=address if rental_details.exact_address_public else None,
                ),
                has_exact_public_address=rental_details.exact_address_public,
            )
        case "farm-ranch":
            if has_ag_equipment_details(listing):
                equipment_details = listing.ag_equipment_details
                return PublicListingPresentation(
                    summary=equipment_details.get_equipment_type_display(),
                    facts=_public_facts(
                        listing=listing,
                        facts=[
                            ("Condition", equipment_details.get_condition_display()),
                            (
                                "Year",
                                str(equipment_details.year)
                                if equipment_details.year
                                else "Not specified",
                            ),
                        ],
                    ),
                    location=base_location,
                    map_query=_public_location_query(listing=listing),
                )
            pasture_details = cast(ListingWithPastureDetails, listing).pasture_details
            return PublicListingPresentation(
                summary="Pasture lease",
                facts=_public_facts(
                    listing=listing,
                    facts=[
                        ("Acreage", f"{pasture_details.acreage} acres"),
                        ("Water", "Available" if pasture_details.water_available else "Not listed"),
                    ],
                ),
                location=base_location,
                map_query=_public_location_query(listing=listing),
            )
        case "livestock-animals":
            livestock_details = cast(ListingWithLivestockDetails, listing).livestock_details
            return PublicListingPresentation(
                summary=livestock_details.get_species_display(),
                facts=_public_facts(
                    listing=listing,
                    facts=[
                        ("Count", str(livestock_details.head_count)),
                        ("Sale unit", livestock_details.get_sale_unit_display()),
                    ],
                ),
                location=base_location,
                map_query=_public_location_query(listing=listing),
            )
        case "home-garden" | "appliances":
            home_goods_details = cast(ListingWithHomeGoodsDetails, listing).home_goods_details
            return PublicListingPresentation(
                summary=home_goods_details.item_type,
                facts=_public_facts(
                    listing=listing,
                    facts=[
                        ("Condition", home_goods_details.get_condition_display()),
                        ("Status", home_goods_details.get_working_status_display()),
                    ],
                ),
                location=base_location,
                map_query=_public_location_query(listing=listing),
            )
    return PublicListingPresentation(
        summary=listing.category.name,
        facts=_public_facts(listing=listing, facts=[]),
        location=base_location,
        map_query=_public_location_query(listing=listing),
    )


def present_public_listing(*, listing: Listing) -> PublicListingPresentation:
    """Add only published seller taxonomy/facts to the otherwise typed presenter."""
    presentation = _present_public_listing(listing=listing)
    if listing.status != ListingStatus.PUBLISHED:
        return presentation
    controlled_tags = tuple(
        tag.category.name
        for tag in listing.controlled_tags.all()
        if tag.category_id != listing.category_id
    )
    seller_tags = tuple(tag.value for tag in listing.seller_tags.all())
    additional_details = tuple((field.label, field.value) for field in listing.custom_fields.all())
    return replace(
        presentation,
        tags=controlled_tags + seller_tags,
        additional_details=additional_details,
    )
