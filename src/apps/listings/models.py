from __future__ import annotations

import json
import re
import uuid
from decimal import Decimal
from typing import Any

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from apps.accounts.models import SellerProfile
from apps.catalog.models import (
    Category,
    ListingKind,
    PostingFieldType,
    PostingFieldVisibility,
    Vertical,
)
from apps.locations.models import County, State

MAX_GENERIC_ATTRIBUTE_COUNT = 16
MAX_GENERIC_ATTRIBUTE_BYTES = 8 * 1024
MAX_GENERIC_ATTRIBUTE_TEXT_LENGTH = 240
BROKER_ATTRIBUTION_VERTICAL_SLUGS = frozenset({"real-estate", "rentals", "farm-ranch"})
MAX_SELLER_TAGS = 10
MAX_CUSTOM_FIELDS = 8
TAG_MAX_LENGTH = 40
CUSTOM_FIELD_LABEL_MAX_LENGTH = 60
CUSTOM_FIELD_VALUE_MAX_LENGTH = 500
_HTML_PATTERN = re.compile(r"<[^>]+>")
_URL_PATTERN = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"(?:\+?\d[\d(). -]{7,}\d)")
_COORDINATE_PATTERN = re.compile(r"\b-?\d{1,3}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}\b")
_ADDRESS_PATTERN = re.compile(
    r"\b\d{1,6}\s+[\w .'-]+\s(?:street|st\.?|avenue|ave\.?|road|rd\.?|lane|ln\.?|drive|dr\.?|"
    r"boulevard|blvd\.?|highway|hwy\.?|court|ct\.?|place|pl\.?)\b",
    re.IGNORECASE,
)
_SENSITIVE_PATTERN = re.compile(
    r"\b(?:password|passcode|secret|api key|token|routing number|bank account|credit card|"
    r"social security|ssn|insurance policy|wallet address)\b",
    re.IGNORECASE,
)
_RESERVED_TAG_PATTERN = re.compile(
    r"\b(?:admin|moderator|official|verified|staff|support|thecountypost)\b",
    re.IGNORECASE,
)
_POLICY_UNSAFE_PATTERN = re.compile(
    r"\b(?:firearm|gun|rifle|pistol|weapon|cocaine|heroin|methamphetamine|fentanyl|"
    r"escort service|adult services|crypto investment|wire transfer|counterfeit|"
    r"human trafficking)\b",
    re.IGNORECASE,
)


def broker_attribution_is_eligible(*, vertical: Vertical, category: Category) -> bool:
    """Broker attribution is limited to the approved property and rural verticals."""
    return (
        category.vertical_id == vertical.id and vertical.slug in BROKER_ATTRIBUTION_VERTICAL_SLUGS
    )


def normalize_broker_name(value: str) -> str:
    """Keep the optional public attribution to one bounded plain-text name."""
    normalized = " ".join(value.split())
    if "@" in normalized or "://" in normalized or normalized.lower().startswith("www."):
        raise ValidationError("Enter a broker or brokerage name only, without contact details.")
    return normalized


def normalize_user_defined_text(value: str) -> str:
    """Normalize bounded plain text without interpreting seller input as markup."""
    return " ".join(value.split())


def validate_user_defined_text(value: str, *, label: bool = False) -> str:
    """Reject contact, location, markup, and sensitive content in free-form facts."""
    normalized = normalize_user_defined_text(value)
    if not normalized:
        raise ValidationError("Enter a value.")
    if (
        _HTML_PATTERN.search(normalized)
        or _URL_PATTERN.search(normalized)
        or _EMAIL_PATTERN.search(normalized)
        or _PHONE_PATTERN.search(normalized)
        or _COORDINATE_PATTERN.search(normalized)
        or _ADDRESS_PATTERN.search(normalized)
        or _SENSITIVE_PATTERN.search(normalized)
    ):
        raise ValidationError(
            "Do not include HTML, contact, exact-address, coordinate, or sensitive data."
        )
    if label and (
        _RESERVED_TAG_PATTERN.search(normalized) or _POLICY_UNSAFE_PATTERN.search(normalized)
    ):
        raise ValidationError("This label is reserved or unsafe.")
    return normalized


class ListingStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    AWAITING_PAYMENT = "awaiting_payment", "Awaiting payment"
    IN_REVIEW = "in_review", "In review"
    PUBLISHED = "published", "Published"
    CHANGES_REQUESTED = "changes_requested", "Changes requested"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"
    SOLD = "sold", "Sold"
    EXPIRED = "expired", "Expired"
    ARCHIVED = "archived", "Archived"


class ListingIntent(models.TextChoices):
    OFFER = "offer", "For sale"
    WANTED = "wanted", "Wanted"


class Listing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(SellerProfile, on_delete=models.PROTECT, related_name="listings")
    intent = models.CharField(
        max_length=16, choices=ListingIntent.choices, default=ListingIntent.OFFER
    )
    vertical = models.ForeignKey(Vertical, on_delete=models.PROTECT, related_name="listings")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="listings")
    listing_kind = models.ForeignKey(
        ListingKind,
        on_delete=models.PROTECT,
        related_name="listings",
        null=True,
        blank=True,
    )
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="listings")
    county = models.ForeignKey(County, on_delete=models.PROTECT, related_name="listings")
    city = models.CharField(max_length=100)
    title = models.CharField(max_length=120)
    description = models.TextField()
    broker_name = models.CharField(max_length=120, blank=True)
    available_for_pickup = models.BooleanField(default=False)
    delivery_available = models.BooleanField(default=False)
    shipping_available = models.BooleanField(default=False)
    price_minor = models.PositiveBigIntegerField(null=True, blank=True)
    currency = models.CharField(
        max_length=3, blank=True, validators=[RegexValidator(r"^[A-Z]{3}$")]
    )
    status = models.CharField(
        max_length=32, choices=ListingStatus.choices, default=ListingStatus.DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    first_published_at = models.DateTimeField(null=True, blank=True)
    sold_at = models.DateTimeField(null=True, blank=True)
    sold_public_until = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_material_edit_at = models.DateTimeField(null=True, blank=True)
    lifecycle_revision = models.PositiveIntegerField(default=0)
    # This is a deliberately curated public-only document.  It is populated by
    # listings.search on PostgreSQL and remains NULL in SQLite test/development
    # paths, where browse uses the bounded fallback.
    search_document = SearchVectorField(null=True, editable=False)
    assigned_moderator = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_listing_reviews",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=ListingStatus.values),
                name="listings_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=(
                            ListingStatus.DRAFT,
                            ListingStatus.SUBMITTED,
                            ListingStatus.AWAITING_PAYMENT,
                            ListingStatus.IN_REVIEW,
                            ListingStatus.CHANGES_REQUESTED,
                            ListingStatus.REJECTED,
                            ListingStatus.SUSPENDED,
                            ListingStatus.SOLD,
                            ListingStatus.EXPIRED,
                            ListingStatus.ARCHIVED,
                        ),
                        published_at__isnull=True,
                    )
                    | models.Q(status=ListingStatus.PUBLISHED, published_at__isnull=False)
                ),
                name="listings_status_published_at_pair",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(price_minor__isnull=True, currency="")
                    | models.Q(price_minor__isnull=False, currency__regex=r"^[A-Z]{3}$")
                ),
                name="listings_price_currency_pair",
            ),
            models.CheckConstraint(
                condition=models.Q(intent__in=ListingIntent.values),
                name="listings_intent_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("seller", "status"), name="listings_seller_status_idx"),
            models.Index(
                fields=("seller", "status", "sold_public_until"),
                name="listings_seller_sold_feed_idx",
            ),
            models.Index(
                fields=("status", "state", "county", "category", "-published_at"),
                name="listings_public_scope_idx",
            ),
            models.Index(
                fields=("status", "vertical", "category"), name="listings_public_catalog_idx"
            ),
            models.Index(fields=("status", "created_at"), name="listings_review_queue_idx"),
            models.Index(fields=("status", "expires_at"), name="listings_expiry_safety_idx"),
            models.Index(
                fields=("status", "intent", "state", "-published_at"),
                name="listings_public_intent_idx",
            ),
            GinIndex(fields=("search_document",), name="listings_search_document_gin"),
        ]
        ordering = ("-updated_at",)
        permissions = [
            ("moderate_listing", "Can moderate listings"),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args: object, **kwargs: Any) -> None:
        """Persist the first publication timestamp for every publication writer."""
        if self.status == ListingStatus.PUBLISHED and self.first_published_at is None:
            self.first_published_at = self.published_at or timezone.now()
            if update_fields := kwargs.get("update_fields"):
                kwargs["update_fields"] = tuple({*update_fields, "first_published_at"})
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        self.currency = self.currency.upper()
        self.city = self.city.strip()
        self.broker_name = normalize_broker_name(self.broker_name)
        if self.vertical_id and self.category.vertical_id != self.vertical_id:
            raise ValidationError(
                {"category": "The category must belong to the selected vertical."}
            )
        if self.intent == ListingIntent.WANTED and self.listing_kind_id is not None:
            raise ValidationError(
                {"listing_kind": "Wanted listings cannot use a sale listing kind."}
            )
        if (
            self.listing_kind_id
            and self.listing_kind is not None
            and self.listing_kind.vertical_id != self.vertical_id
        ):
            raise ValidationError(
                {"listing_kind": "The listing kind must belong to the selected vertical."}
            )
        if self.county_id and (not self.state_id or self.county.state_id != self.state_id):
            raise ValidationError({"county": "The county must belong to the selected state."})
        if self.category_id and (
            (self.vertical_id and not self.vertical.is_active) or not self.category.is_active
        ):
            raise ValidationError("Listings require an active vertical and category.")
        if (
            self.broker_name
            and self.vertical_id
            and self.category_id
            and not broker_attribution_is_eligible(vertical=self.vertical, category=self.category)
        ):
            raise ValidationError(
                {
                    "broker_name": (
                        "Broker attribution is available only for Homes, Rentals, and Farm & Ranch."
                    )
                }
            )
        if (
            self.state_id
            and self.county_id
            and (not self.state.is_active or not self.county.is_active)
        ):
            raise ValidationError("Listings require an active state and county.")
        if self.status == ListingStatus.PUBLISHED and self.published_at is None:
            raise ValidationError(
                {"published_at": "Published listings require a publication timestamp."}
            )
        if self.status != ListingStatus.PUBLISHED and self.published_at is not None:
            raise ValidationError(
                {"published_at": "Only published listings can have a publication timestamp."}
            )


class ListingCategoryTag(models.Model):
    """A controlled catalog leaf tag attached in addition to Listing.category."""

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="controlled_tags")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="listing_tags")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "category"), name="listings_controlled_tag_unique"
            )
        ]
        indexes = [models.Index(fields=("category", "listing"), name="listings_controlled_tag_idx")]

    def __str__(self) -> str:
        return f"{self.listing_id}: {self.category}"

    def clean(self) -> None:
        super().clean()
        if self.listing_id and self.category_id:
            if self.category.vertical_id != self.listing.vertical_id:
                raise ValidationError(
                    {"category": "Controlled tags must use the listing vertical."}
                )
            if (
                not self.category.is_active
                or self.category.children.filter(is_active=True).exists()
            ):
                raise ValidationError({"category": "Choose an active postable subcategory."})


class ListingSellerTag(models.Model):
    """Bounded seller text tag; public only through the listing visibility selector."""

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="seller_tags")
    value = models.CharField(max_length=TAG_MAX_LENGTH)
    normalized_value = models.CharField(max_length=TAG_MAX_LENGTH, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "normalized_value"), name="listings_seller_tag_unique"
            )
        ]
        indexes = [
            models.Index(
                fields=("normalized_value", "listing"), name="listings_seller_tag_search_idx"
            )
        ]
        ordering = ("normalized_value",)

    def __str__(self) -> str:
        return self.value

    def clean(self) -> None:
        super().clean()
        self.value = validate_user_defined_text(self.value, label=True)
        if not 1 <= len(self.value) <= TAG_MAX_LENGTH:
            raise ValidationError({"value": "Tags must be between 1 and 40 characters."})
        self.normalized_value = self.value.casefold()


class ListingCustomField(models.Model):
    """The ADR-approved, bounded one-row seller-defined public fact."""

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="custom_fields")
    label = models.CharField(max_length=CUSTOM_FIELD_LABEL_MAX_LENGTH)
    normalized_label = models.CharField(max_length=CUSTOM_FIELD_LABEL_MAX_LENGTH, blank=True)
    value = models.CharField(max_length=CUSTOM_FIELD_VALUE_MAX_LENGTH)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "normalized_label"), name="listings_custom_field_label_unique"
            )
        ]
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.label}: {self.value}"

    def clean(self) -> None:
        super().clean()
        self.label = validate_user_defined_text(self.label, label=True)
        self.value = validate_user_defined_text(self.value)
        if not 1 <= len(self.label) <= CUSTOM_FIELD_LABEL_MAX_LENGTH:
            raise ValidationError({"label": "Labels must be between 1 and 60 characters."})
        if not 1 <= len(self.value) <= CUSTOM_FIELD_VALUE_MAX_LENGTH:
            raise ValidationError({"value": "Values must be between 1 and 500 characters."})
        self.normalized_label = self.label.casefold()


class GenericListingDetails(models.Model):
    """Bounded generic listing data; the street address is seller/staff private."""

    listing = models.OneToOneField(
        Listing, on_delete=models.CASCADE, related_name="generic_details"
    )
    price_mode = models.CharField(
        max_length=16,
        choices=(
            ("fixed", "Fixed price"),
            ("negotiable", "Negotiable"),
            ("contact", "Contact for price"),
            ("free", "Free"),
        ),
    )
    postal_code = models.CharField(max_length=5, validators=[RegexValidator(r"^\d{5}$")])
    street_address = models.CharField(max_length=160, blank=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    attributes = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"Generic details for {self.listing_id}"

    def clean(self) -> None:  # noqa: PLR0912
        super().clean()
        self.postal_code = self.postal_code.strip()
        self.street_address = self.street_address.strip()
        if self.listing_id and self.listing.listing_kind_id is not None:
            raise ValidationError("Generic listings cannot use a typed listing kind.")
        if self.price_mode in {"fixed", "negotiable"} and self.listing.price_minor is None:
            raise ValidationError({"price_mode": "Enter an asking price for this price mode."})
        if self.price_mode in {"contact", "free"} and self.listing.price_minor is not None:
            raise ValidationError({"price_mode": "This price mode cannot include an asking price."})
        if (
            not isinstance(self.attributes, dict)
            or len(self.attributes) > MAX_GENERIC_ATTRIBUTE_COUNT
        ):
            raise ValidationError({"attributes": "Supplemental facts must be a bounded object."})
        if (
            len(json.dumps(self.attributes, separators=(",", ":")).encode())
            > MAX_GENERIC_ATTRIBUTE_BYTES
        ):
            raise ValidationError({"attributes": "Supplemental facts are too large."})
        if any(
            not isinstance(value, (str, int, bool))
            or (isinstance(value, str) and len(value) > MAX_GENERIC_ATTRIBUTE_TEXT_LENGTH)
            for value in self.attributes.values()
        ):
            raise ValidationError({"attributes": "Supplemental facts include an invalid value."})
        if self.listing_id:
            try:
                profile = self.listing.category.posting_profile
            except AttributeError as error:
                if self.attributes:
                    raise ValidationError(
                        {"attributes": "This category has no active posting profile."}
                    ) from error
                return
            fields = {field.key: field for field in profile.fields.all()}
            unknown = set(self.attributes).difference(fields)
            if unknown:
                raise ValidationError(
                    {"attributes": "Supplemental facts contain unsupported fields."}
                )
            missing = {key for key, field in fields.items() if field.required}.difference(
                self.attributes
            )
            if missing:
                raise ValidationError({"attributes": "Required supplemental facts are missing."})
            for key, value in self.attributes.items():
                field = fields[key]
                if field.visibility == PostingFieldVisibility.STAFF_ONLY:
                    raise ValidationError(
                        {"attributes": "Staff-only facts cannot be seller submitted."}
                    )
                if field.field_type == PostingFieldType.TEXT and not isinstance(value, str):
                    raise ValidationError({"attributes": f"{key} must be text."})
                if field.field_type == PostingFieldType.INTEGER and (
                    not isinstance(value, int) or isinstance(value, bool)
                ):
                    raise ValidationError({"attributes": f"{key} must be a whole number."})
                if field.field_type == PostingFieldType.BOOLEAN and not isinstance(value, bool):
                    raise ValidationError({"attributes": f"{key} must be true or false."})
                if field.field_type == PostingFieldType.CHOICE and value not in field.choices:
                    raise ValidationError({"attributes": f"{key} is not an allowed choice."})


class ListingCountyPlacement(models.Model):
    """An additional public county scope; Listing.county remains canonical primary."""

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="additional_counties"
    )
    county = models.ForeignKey(County, on_delete=models.PROTECT, related_name="additional_listings")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "county"), name="listings_additional_county_unique"
            )
        ]
        indexes = [models.Index(fields=("county",), name="listings_placement_county_idx")]

    def __str__(self) -> str:
        return f"{self.listing_id} in {self.county_id}"

    def clean(self) -> None:
        super().clean()
        if self.listing_id and self.county_id:
            if self.county_id == self.listing.county_id:
                raise ValidationError({"county": "The primary county cannot be added twice."})
            if self.county.state_id != self.listing.state_id:
                raise ValidationError({"county": "Additional counties must use the listing state."})


class AutoDetails(models.Model):
    class VehicleType(models.TextChoices):
        CAR = "car", "Car"
        TRUCK = "truck", "Truck"
        SUV = "suv", "SUV"
        VAN = "van", "Van"
        MOTORCYCLE = "motorcycle", "Motorcycle"
        OTHER = "other", "Other"

    class TitleStatus(models.TextChoices):
        CLEAN = "clean", "Clean"
        SALVAGE = "salvage", "Salvage"
        REBUILT = "rebuilt", "Rebuilt"
        OTHER = "other", "Other"

    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name="auto_details")
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)
    year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1886), MaxValueValidator(9999)]
    )
    make = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    trim = models.CharField(max_length=80, blank=True)
    mileage = models.PositiveIntegerField()
    title_status = models.CharField(max_length=20, choices=TitleStatus.choices)
    vin = models.CharField(
        max_length=17, blank=True, validators=[RegexValidator(r"^[A-HJ-NPR-Z0-9]{17}$")]
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(mileage__gte=0), name="listings_auto_mileage_nonnegative"
            )
        ]

    def __str__(self) -> str:
        return f"{self.year} {self.make} {self.model}"

    def clean(self) -> None:
        super().clean()
        self.make = self.make.strip()
        self.model = self.model.strip()
        self.trim = self.trim.strip()
        self.vin = self.vin.strip().upper()
        if self.listing_id and self.listing.vertical.slug != "autos":
            raise ValidationError({"listing": "Auto details require the Autos vertical."})


class PropertyAddressMixin(models.Model):
    street_address = models.CharField(max_length=160, blank=True)
    address_line_2 = models.CharField(max_length=160, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    general_area = models.CharField(max_length=160)
    exact_address_public = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def clean_address(self) -> None:
        self.street_address = self.street_address.strip()
        self.address_line_2 = self.address_line_2.strip()
        self.postal_code = self.postal_code.strip()
        self.general_area = self.general_area.strip()
        if self.exact_address_public and not self.street_address:
            raise ValidationError(
                {"street_address": "A street address is required to allow public address display."}
            )


class HomeDetails(PropertyAddressMixin):
    class PropertyType(models.TextChoices):
        HOUSE = "house", "House"
        CONDO = "condo", "Condo"
        TOWNHOUSE = "townhouse", "Townhouse"
        MANUFACTURED_HOME = "manufactured_home", "Manufactured home"
        LAND = "land", "Land"
        MULTIFAMILY = "multifamily", "Multifamily"
        COMMERCIAL = "commercial", "Commercial"
        OTHER = "other", "Other"

    class LotSizeUnit(models.TextChoices):
        ACRES = "acres", "Acres"
        SQUARE_FEET = "square_feet", "Square feet"

    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name="home_details")
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    beds = models.PositiveSmallIntegerField(null=True, blank=True)
    baths = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    square_feet = models.PositiveIntegerField(null=True, blank=True)
    year_built = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(9999)]
    )
    lot_size = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    lot_size_unit = models.CharField(max_length=20, choices=LotSizeUnit.choices, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(beds__gte=0) | models.Q(beds__isnull=True),
                name="listings_home_beds_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(baths__gte=0) | models.Q(baths__isnull=True),
                name="listings_home_baths_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(square_feet__gte=0) | models.Q(square_feet__isnull=True),
                name="listings_home_sqft_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(lot_size__gte=0) | models.Q(lot_size__isnull=True),
                name="listings_home_lot_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(lot_size__isnull=True, lot_size_unit="")
                    | models.Q(lot_size__isnull=False, lot_size_unit__in=("acres", "square_feet"))
                ),
                name="listings_home_lot_unit_pair",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_property_type_display()} details"

    def clean(self) -> None:
        super().clean()
        self.clean_address()
        if self.listing_id and self.listing.vertical.slug != "real-estate":
            raise ValidationError({"listing": "Home details require the Real Estate vertical."})
        if self.property_type in {
            self.PropertyType.LAND,
            self.PropertyType.COMMERCIAL,
            self.PropertyType.OTHER,
        }:
            return
        missing = [
            field for field in ("beds", "baths", "square_feet") if getattr(self, field) is None
        ]
        if missing:
            raise ValidationError(
                {field: "This field is required for this property type." for field in missing}
            )


class RentalDetails(PropertyAddressMixin):
    class RentalType(models.TextChoices):
        APARTMENT = "apartment", "Apartment"
        HOUSE = "house", "House"
        TOWNHOUSE = "townhouse", "Townhouse"
        ROOM = "room", "Room"
        MANUFACTURED_HOME = "manufactured_home", "Manufactured home"
        VACATION = "vacation", "Vacation"
        COMMERCIAL = "commercial", "Commercial"
        STORAGE = "storage", "Storage"
        OTHER = "other", "Other"

    class PetsPolicy(models.TextChoices):
        ALLOWED = "allowed", "Pets allowed"
        NOT_ALLOWED = "not_allowed", "No pets"
        CASE_BY_CASE = "case_by_case", "Case by case"

    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name="rental_details")
    rental_type = models.CharField(max_length=20, choices=RentalType.choices)
    monthly_rent_minor = models.PositiveBigIntegerField()
    security_deposit_minor = models.PositiveBigIntegerField(default=0)
    beds = models.PositiveSmallIntegerField(null=True, blank=True)
    baths = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    available_date = models.DateField()
    pets_policy = models.CharField(max_length=20, choices=PetsPolicy.choices)
    lease_term_months = models.PositiveSmallIntegerField(null=True, blank=True)
    flexible_term = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monthly_rent_minor__gte=0),
                name="listings_rental_rent_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(security_deposit_minor__gte=0),
                name="listings_rental_deposit_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(beds__gte=0) | models.Q(beds__isnull=True),
                name="listings_rental_beds_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(baths__gte=0) | models.Q(baths__isnull=True),
                name="listings_rental_baths_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(flexible_term=True, lease_term_months__isnull=True)
                    | models.Q(flexible_term=False, lease_term_months__gte=1)
                ),
                name="listings_rental_lease_term",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_rental_type_display()} rental details"

    def clean(self) -> None:
        super().clean()
        self.clean_address()
        if self.listing_id and self.listing.vertical.slug != "rentals":
            raise ValidationError({"listing": "Rental details require the Rentals vertical."})
        if self.flexible_term and self.lease_term_months is not None:
            raise ValidationError(
                {"lease_term_months": "Flexible rentals cannot have a fixed lease term."}
            )
        if not self.flexible_term and self.lease_term_months is None:
            raise ValidationError(
                {"lease_term_months": "Enter a lease term or select flexible term."}
            )
        if self.rental_type in {
            self.RentalType.VACATION,
            self.RentalType.COMMERCIAL,
            self.RentalType.STORAGE,
            self.RentalType.OTHER,
        }:
            return
        missing = [field for field in ("beds", "baths") if getattr(self, field) is None]
        if missing:
            raise ValidationError(
                {field: "This field is required for this rental type." for field in missing}
            )


class AgEquipmentDetails(models.Model):
    class EquipmentType(models.TextChoices):
        TRACTOR = "tractor", "Tractor"
        HARVESTING = "harvesting", "Harvesting equipment"
        IMPLEMENT = "implement", "Implement"
        RANCH_SUPPLY = "ranch_supply", "Ranch supply"
        OTHER = "other", "Other"

    class Condition(models.TextChoices):
        NEW = "new", "New"
        USED = "used", "Used"
        FOR_PARTS = "for_parts", "For parts"

    listing = models.OneToOneField(
        Listing, on_delete=models.CASCADE, related_name="ag_equipment_details"
    )
    equipment_type = models.CharField(max_length=20, choices=EquipmentType.choices)
    make = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=80, blank=True)
    year = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(9999)]
    )
    hours = models.PositiveIntegerField(null=True, blank=True)
    powered = models.BooleanField(default=False)
    condition = models.CharField(max_length=20, choices=Condition.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hours__gte=0) | models.Q(hours__isnull=True),
                name="listings_ag_equipment_hours_nonnegative",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_equipment_type_display()} details"

    def clean(self) -> None:
        super().clean()
        self.make = self.make.strip()
        self.model = self.model.strip()
        if self.listing_id and self.listing.vertical.slug != "farm-ranch":
            raise ValidationError(
                {"listing": "Agricultural equipment requires the Farm & Ranch vertical."}
            )


class LivestockDetails(models.Model):
    class Species(models.TextChoices):
        CATTLE = "cattle", "Cattle"
        GOATS_SHEEP = "goats_sheep", "Goats & sheep"
        HORSES = "horses", "Horses"
        POULTRY = "poultry", "Poultry"
        OTHER = "other", "Other"

    class SaleUnit(models.TextChoices):
        HEAD = "head", "Per head"
        GROUP = "group", "As a group"
        POUND = "pound", "Per pound"

    listing = models.OneToOneField(
        Listing, on_delete=models.CASCADE, related_name="livestock_details"
    )
    species = models.CharField(max_length=20, choices=Species.choices)
    breed = models.CharField(max_length=100, blank=True)
    animal_class = models.CharField(max_length=100, blank=True)
    head_count = models.PositiveIntegerField()
    age_or_weight = models.CharField(max_length=120, blank=True)
    sale_unit = models.CharField(max_length=20, choices=SaleUnit.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(head_count__gte=1), name="listings_livestock_head_count_positive"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_species_display()} details"

    def clean(self) -> None:
        super().clean()
        self.breed = self.breed.strip()
        self.animal_class = self.animal_class.strip()
        self.age_or_weight = self.age_or_weight.strip()
        if self.listing_id and self.listing.vertical.slug != "livestock-animals":
            raise ValidationError(
                {"listing": "Livestock details require the Livestock & Animals vertical."}
            )


class PastureDetails(models.Model):
    listing = models.OneToOneField(
        Listing, on_delete=models.CASCADE, related_name="pasture_details"
    )
    acreage = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    water_available = models.BooleanField(default=False)
    fenced = models.BooleanField(default=False)
    lease_term = models.CharField(max_length=100)
    use_restrictions = models.CharField(max_length=300, blank=True)
    available_date = models.DateField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(acreage__gt=0), name="listings_pasture_acreage_positive"
            )
        ]

    def __str__(self) -> str:
        return "Pasture details"

    def clean(self) -> None:
        super().clean()
        self.lease_term = self.lease_term.strip()
        self.use_restrictions = self.use_restrictions.strip()
        if self.listing_id and self.listing.vertical.slug != "farm-ranch":
            raise ValidationError({"listing": "Pasture details require the Farm & Ranch vertical."})


class HomeGoodsDetails(models.Model):
    class Condition(models.TextChoices):
        NEW = "new", "New"
        LIKE_NEW = "like_new", "Like new"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        FOR_PARTS = "for_parts", "For parts"

    class WorkingStatus(models.TextChoices):
        WORKING = "working", "Working"
        NOT_WORKING = "not_working", "Not working"
        UNKNOWN = "unknown", "Unknown"

    class FulfillmentPreference(models.TextChoices):
        PICKUP = "pickup", "Pickup"
        DELIVERY = "delivery", "Delivery"
        EITHER = "either", "Pickup or delivery"

    listing = models.OneToOneField(
        Listing, on_delete=models.CASCADE, related_name="home_goods_details"
    )
    item_type = models.CharField(max_length=100)
    brand = models.CharField(max_length=80, blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices)
    working_status = models.CharField(max_length=20, choices=WorkingStatus.choices)
    dimensions = models.CharField(max_length=120, blank=True)
    fulfillment_preference = models.CharField(max_length=20, choices=FulfillmentPreference.choices)

    def __str__(self) -> str:
        return f"{self.item_type} details"

    def clean(self) -> None:
        super().clean()
        self.item_type = self.item_type.strip()
        self.brand = self.brand.strip()
        self.dimensions = self.dimensions.strip()
        if not self.item_type:
            raise ValidationError({"item_type": "Enter an item type or category."})
        if self.listing_id and self.listing.vertical.slug not in {"appliances", "home-garden"}:
            raise ValidationError(
                {"listing": "Home goods details require the Appliances or Home & Garden vertical."}
            )


class ModerationReasonCode(models.Model):
    """Versioned, stable reason taxonomy; records used by history are never deleted."""

    code = models.CharField(max_length=40, unique=True)
    category = models.CharField(max_length=80)
    seller_facing_text = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    requires_escalation = models.BooleanField(default=False)
    version = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=("is_active", "category"), name="moderation_reason_active_idx")
        ]
        ordering = ("category", "code")

    def __str__(self) -> str:
        return self.code


class ModerationActionType(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    CLAIMED = "claimed", "Claimed"
    APPROVED = "approved", "Approved"
    APPROVED_NO_PAYMENT = "approved_no_payment", "Approved without payment"
    APPROVED_SEND_PAYMENT_LINK = "approved_send_payment_link", "Approved and sent payment link"
    CHANGES_REQUESTED = "changes_requested", "Changes requested"
    REJECTED = "rejected", "Rejected"
    IMAGE_APPROVED = "image_approved", "Image approved"
    IMAGE_REJECTED = "image_rejected", "Image rejected"
    VIDEO_APPROVED = "video_approved", "Video approved"
    VIDEO_REJECTED = "video_rejected", "Video rejected"
    ESCALATED = "escalated", "Escalated"
    SUSPENDED = "suspended", "Suspended"
    POLICY_FLAGGED = "policy_flagged", "Policy flagged"
    DIRECT_APPROVAL = "direct_approval", "Direct demo approval"
    MATERIAL_EDIT = "material_edit", "Material edit submitted"
    MARKED_SOLD = "marked_sold", "Marked sold"
    ARCHIVED = "archived", "Archived"
    RESTORED_DRAFT = "restored_draft", "Restored to draft"
    RENEWED = "renewed", "Renewed"
    EXPIRED = "expired", "Expired"


class ModerationAction(models.Model):
    """Append-only moderation history. Internal notes must never be rendered to sellers."""

    listing = models.ForeignKey(
        Listing, on_delete=models.PROTECT, related_name="moderation_actions"
    )
    actor = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="moderation_actions",
    )
    action_type = models.CharField(max_length=32, choices=ModerationActionType.choices)
    from_status = models.CharField(max_length=32, choices=ListingStatus.choices)
    to_status = models.CharField(max_length=32, choices=ListingStatus.choices)
    reason_code = models.ForeignKey(
        ModerationReasonCode,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="actions",
    )
    internal_note = models.TextField(blank=True)
    seller_facing_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=("listing", "-created_at"), name="moderation_action_listing_idx"),
            models.Index(fields=("action_type", "-created_at"), name="moderation_action_type_idx"),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.listing_id}: {self.action_type}"


class Favorite(models.Model):
    """A user's private bookmark of a listing that was publicly visible when saved."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="favorites")
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "listing"), name="listings_favorite_user_listing"
            )
        ]
        indexes = [models.Index(fields=("user", "-created_at"), name="listings_favorite_user_idx")]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user_id} saved {self.listing_id}"


class ListingMediaPolicy(models.Model):
    """Configurable image requirement for a postable listing kind or category."""

    listing_kind = models.OneToOneField(
        ListingKind,
        on_delete=models.PROTECT,
        related_name="media_policy",
        null=True,
        blank=True,
    )
    category = models.OneToOneField(
        Category,
        on_delete=models.PROTECT,
        related_name="media_policy",
        null=True,
        blank=True,
    )
    required_image_count = models.PositiveSmallIntegerField(default=0)
    maximum_image_count = models.PositiveSmallIntegerField(default=12)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(listing_kind__isnull=False, category__isnull=True)
                    | models.Q(listing_kind__isnull=True, category__isnull=False)
                ),
                name="listings_media_policy_one_target",
            ),
            models.CheckConstraint(
                condition=models.Q(maximum_image_count__gte=1),
                name="listings_media_policy_max_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(required_image_count__lte=models.F("maximum_image_count")),
                name="listings_media_policy_required_within_max",
            ),
        ]

    def __str__(self) -> str:
        return f"Image policy: {self.listing_kind or self.category}"

    def clean(self) -> None:
        super().clean()
        if bool(self.listing_kind_id) == bool(self.category_id):
            raise ValidationError("Choose exactly one listing kind or category.")
        if self.required_image_count > self.maximum_image_count:
            raise ValidationError(
                {"required_image_count": "The required count cannot exceed the maximum."}
            )


class UploadSessionState(models.TextChoices):
    OPEN = "open", "Open"
    FINALIZED = "finalized", "Finalized"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"


class UploadSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="upload_sessions")
    seller = models.ForeignKey(
        SellerProfile, on_delete=models.PROTECT, related_name="upload_sessions"
    )
    state = models.CharField(
        max_length=16, choices=UploadSessionState.choices, default=UploadSessionState.OPEN
    )
    expires_at = models.DateTimeField()
    staged_key = models.CharField(max_length=300, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("state", "expires_at"), name="listings_upload_expiry_idx"),
            models.Index(fields=("listing", "seller"), name="listings_upload_owner_idx"),
        ]

    def __str__(self) -> str:
        return f"Upload session {self.id}"


class ListingImageState(models.TextChoices):
    READY = "ready", "Ready"
    DELETED = "deleted", "Deleted"


class ListingImageModerationStatus(models.TextChoices):
    PENDING = "pending", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ListingVideoState(models.TextChoices):
    READY = "ready", "Ready"
    DELETED = "deleted", "Deleted"


class ListingVideoModerationStatus(models.TextChoices):
    PENDING = "pending", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ListingImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="images")
    upload_session = models.OneToOneField(
        UploadSession,
        on_delete=models.PROTECT,
        related_name="listing_image",
    )
    ordering = models.PositiveSmallIntegerField()
    state = models.CharField(
        max_length=16, choices=ListingImageState.choices, default=ListingImageState.READY
    )
    moderation_status = models.CharField(
        max_length=16,
        choices=ListingImageModerationStatus.choices,
        default=ListingImageModerationStatus.PENDING,
    )
    moderation_reason = models.CharField(max_length=500, blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderated_listing_images",
    )
    content_type = models.CharField(max_length=32)
    byte_size = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=300, unique=True)
    rendition_key = models.CharField(max_length=300, unique=True)
    original_filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "ordering"),
                condition=models.Q(state=ListingImageState.READY),
                name="listings_ready_image_order_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(width__gte=1, height__gte=1, byte_size__gte=1),
                name="listings_image_dimensions_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=("listing", "state", "ordering"), name="listings_image_listing_idx"
            ),
        ]
        ordering = ("ordering", "created_at")

    def __str__(self) -> str:
        return f"Image {self.ordering + 1} for {self.listing}"


class ListingVideo(models.Model):
    """Supplemental private video with a separate staff moderation decision."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="videos")
    state = models.CharField(
        max_length=16, choices=ListingVideoState.choices, default=ListingVideoState.READY
    )
    moderation_status = models.CharField(
        max_length=16,
        choices=ListingVideoModerationStatus.choices,
        default=ListingVideoModerationStatus.PENDING,
    )
    moderation_reason = models.CharField(max_length=500, blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderated_listing_videos",
    )
    content_type = models.CharField(max_length=32)
    byte_size = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=300, unique=True)
    original_filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(byte_size__gte=1),
                name="listings_video_byte_size_positive",
            ),
        ]
        indexes = [
            models.Index(fields=("listing", "state"), name="listings_video_listing_idx"),
        ]
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"Video for {self.listing}"
