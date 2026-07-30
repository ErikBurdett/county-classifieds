from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, ClassVar, cast

from django import forms
from django.core.exceptions import ValidationError

from apps.catalog.models import (
    CatalogPostingProfile,
    Category,
    PostingFieldType,
    PostingFieldVisibility,
    Vertical,
)
from apps.catalog.selectors import (
    active_postable_categories,
    automatic_primary_category,
    category_hierarchy_label,
)
from apps.locations.models import County, State
from apps.locations.zip_county import zip_county_candidates

from .models import (
    MAX_CUSTOM_FIELDS,
    MAX_SELLER_TAGS,
    AgEquipmentDetails,
    AutoDetails,
    HomeDetails,
    HomeGoodsDetails,
    Listing,
    ListingCustomField,
    ListingSellerTag,
    LivestockDetails,
    PastureDetails,
    RentalDetails,
    broker_attribution_is_eligible,
)

MAX_PROFILE_ATTRIBUTES = 16
MAX_PROFILE_ATTRIBUTE_BYTES = 8 * 1024
BROKER_NAME_HELP_TEXT = (
    "Optional public broker or brokerage name only. "
    "Do not include contact details or license information."
)


def _broker_name_field() -> forms.CharField:
    return forms.CharField(
        required=False,
        max_length=120,
        label="Broker or brokerage",
        help_text=BROKER_NAME_HELP_TEXT,
    )


def _submitted_broker_name(form: Any) -> str:
    return str(form.data.get("broker_name", "")).strip() if form.is_bound else ""


def _reject_ineligible_broker_submission(*, form: Any, eligible: bool) -> None:
    if _submitted_broker_name(form) and not eligible:
        form.add_error(
            None,
            "Broker attribution is available only for Homes, Rentals, and Farm & Ranch.",
        )


class LeafCategoryChoiceField(forms.ModelChoiceField):  # type: ignore[type-arg]
    """Render catalog leaves with enough context to disambiguate them."""

    def label_from_instance(self, category: Category) -> str:
        return category_hierarchy_label(category=category)


class ListingCategoryForm(forms.Form):
    vertical = forms.ModelChoiceField(queryset=Vertical.objects.none(), required=True)
    category = LeafCategoryChoiceField(
        queryset=Category.objects.none(),
        required=True,
        error_messages={
            "invalid_choice": "Choose a postable subcategory, not a category group.",
        },
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        vertical_field = cast(forms.ModelChoiceField, self.fields["vertical"])  # type: ignore[type-arg]
        category_field = cast(forms.ModelChoiceField, self.fields["category"])  # type: ignore[type-arg]
        vertical_field.queryset = Vertical.objects.filter(is_active=True).order_by(
            "display_order", "name"
        )
        category_field.queryset = active_postable_categories()
        selected_vertical_id = (
            self.data.get("vertical") if self.is_bound else self.initial.get("vertical")
        )
        selected_vertical = (
            Vertical.objects.filter(pk=selected_vertical_id, is_active=True).first()
            if selected_vertical_id and str(selected_vertical_id).isdigit()
            else None
        )
        if selected_vertical is not None:
            category_field.queryset = category_field.queryset.filter(
                vertical_id=selected_vertical.id
            )
            automatic_category = automatic_primary_category(vertical=selected_vertical)
            if automatic_category is not None:
                category_field.required = False
                category_field.queryset = category_field.queryset.filter(pk=automatic_category.id)
        else:
            category_field.queryset = Category.objects.none()

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        vertical = cleaned.get("vertical")
        category = cleaned.get("category")
        if vertical is not None:
            automatic_category = automatic_primary_category(vertical=vertical)
            if automatic_category is not None:
                cleaned["category"] = automatic_category
                category = automatic_category
        if vertical is not None and category is not None and category.vertical_id != vertical.id:
            self.add_error("category", "Choose a category from the selected vertical.")
        return cleaned


class ListingTaxonomyAndFactsForm(forms.Form):
    """Server-authoritative controlled tags plus bounded seller-defined facts."""

    controlled_tags = forms.ModelMultipleChoiceField(
        queryset=Category.objects.none(),
        required=False,
        label="Additional subcategories",
        help_text="Optional controlled subcategories in the selected vertical.",
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(
        self,
        *args: Any,
        vertical: Vertical,
        primary_category: Category,
        enforce_seller_tag: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.vertical = vertical
        self.primary_category = primary_category
        controlled_field = cast(
            "forms.ModelMultipleChoiceField[Category]", self.fields["controlled_tags"]
        )
        controlled_field.queryset = active_postable_categories(vertical_id=vertical.id).exclude(
            pk=primary_category.id
        )
        for index in range(MAX_SELLER_TAGS):
            self.fields[f"seller_tag_{index}"] = forms.CharField(
                required=vertical.slug == "others" and index == 0 and enforce_seller_tag,
                max_length=40,
                label=f"Seller tag {index + 1}",
            )
        for index in range(MAX_CUSTOM_FIELDS):
            self.fields[f"custom_field_label_{index}"] = forms.CharField(
                required=False, max_length=60, label="Label"
            )
            self.fields[f"custom_field_value_{index}"] = forms.CharField(
                required=False, max_length=500, label="Value"
            )

    @property
    def seller_tag_fields(self) -> list[forms.BoundField]:
        return [self[f"seller_tag_{index}"] for index in range(MAX_SELLER_TAGS)]

    @property
    def requires_seller_tag(self) -> bool:
        return self.vertical.slug == "others"

    @property
    def custom_field_pairs(self) -> list[tuple[forms.BoundField, forms.BoundField]]:
        return [
            (self[f"custom_field_label_{index}"], self[f"custom_field_value_{index}"])
            for index in range(MAX_CUSTOM_FIELDS)
        ]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        controlled_tags = list(cleaned.get("controlled_tags") or [])
        if any(tag.vertical_id != self.vertical.id for tag in controlled_tags):
            self.add_error("controlled_tags", "Choose subcategories from the selected vertical.")

        seller_tags: list[str] = []
        seen_tags = {self.primary_category.name.casefold()} | {
            tag.name.casefold() for tag in controlled_tags
        }
        for index in range(MAX_SELLER_TAGS):
            raw_tag = cleaned.get(f"seller_tag_{index}", "")
            if not raw_tag:
                continue
            seller_tag_candidate = ListingSellerTag(value=raw_tag)
            try:
                seller_tag_candidate.full_clean(exclude={"listing", "normalized_value"})
            except ValidationError as error:
                self.add_error(None, error)
                continue
            if seller_tag_candidate.normalized_value in seen_tags:
                self.add_error(
                    None, "Tags must be unique and cannot duplicate a controlled subcategory."
                )
                continue
            seen_tags.add(seller_tag_candidate.normalized_value)
            seller_tags.append(seller_tag_candidate.value)
        if len(seller_tags) > MAX_SELLER_TAGS:
            self.add_error(None, "Add at most 10 seller tags.")

        custom_fields: list[dict[str, str]] = []
        seen_labels: set[str] = set()
        for index in range(MAX_CUSTOM_FIELDS):
            label = cleaned.get(f"custom_field_label_{index}", "")
            value = cleaned.get(f"custom_field_value_{index}", "")
            if not label and not value:
                continue
            if not label or not value:
                self.add_error(None, "Additional detail labels and values must be paired.")
                continue
            custom_field_candidate = ListingCustomField(label=label, value=value)
            try:
                custom_field_candidate.full_clean(exclude={"listing", "normalized_label"})
            except ValidationError as error:
                self.add_error(None, error)
                continue
            if custom_field_candidate.normalized_label in seen_labels:
                self.add_error(None, "Additional detail labels must be unique.")
                continue
            seen_labels.add(custom_field_candidate.normalized_label)
            custom_fields.append(
                {"label": custom_field_candidate.label, "value": custom_field_candidate.value}
            )
        if len(custom_fields) > MAX_CUSTOM_FIELDS:
            self.add_error(None, "Add at most 8 additional details.")
        cleaned["seller_tags"] = seller_tags
        cleaned["custom_fields"] = custom_fields
        return cleaned


class ProfileAttributesForm(forms.Form):
    """Build server-validated controls from a catalog-owned profile only."""

    def __init__(self, *args: Any, profile: CatalogPostingProfile, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.profile = profile
        for field in profile.fields.order_by("display_order", "key"):
            if field.visibility == PostingFieldVisibility.STAFF_ONLY:
                continue
            field_kwargs: dict[str, Any] = {
                "label": field.label,
                "required": field.required,
                "help_text": "",
            }
            if field.field_type == PostingFieldType.TEXT:
                field_kwargs["max_length"] = field.maximum or 240
                self.fields[field.key] = forms.CharField(**field_kwargs)
            elif field.field_type == PostingFieldType.INTEGER:
                field_kwargs["min_value"] = 0
                field_kwargs["max_value"] = field.maximum or 999_999
                self.fields[field.key] = forms.IntegerField(**field_kwargs)
            elif field.field_type == PostingFieldType.BOOLEAN:
                self.fields[field.key] = forms.BooleanField(**field_kwargs)
            else:
                self.fields[field.key] = forms.ChoiceField(
                    choices=[(choice, choice) for choice in field.choices], **field_kwargs
                )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        supplied = {key for key in self.data if key in self.fields}
        unknown = {
            key
            for key in self.data
            if key.startswith("attribute_") and key.removeprefix("attribute_") not in self.fields
        }
        if unknown:
            raise forms.ValidationError(
                "The selected listing profile is no longer current. Reload and retry."
            )
        if len(supplied) > MAX_PROFILE_ATTRIBUTES:
            raise forms.ValidationError("Too many supplemental fields were submitted.")
        if len(json.dumps(cleaned, separators=(",", ":")).encode()) > MAX_PROFILE_ATTRIBUTE_BYTES:
            raise forms.ValidationError("Supplemental listing facts are too large.")
        return cleaned


class GenericListingForm(forms.ModelForm):  # type: ignore[type-arg]
    vertical = forms.ModelChoiceField(queryset=Vertical.objects.none(), required=True)
    category = LeafCategoryChoiceField(
        queryset=Category.objects.none(),
        required=True,
        error_messages={
            "invalid_choice": "Choose a postable subcategory, not a category group.",
        },
    )
    price_mode = forms.ChoiceField(
        choices=(
            ("fixed", "Fixed price"),
            ("negotiable", "Negotiable"),
            ("contact", "Contact for price"),
            ("free", "Free"),
        )
    )
    postal_code = forms.CharField(max_length=5, label="Postal / ZIP code")
    asking_price = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=16,
        decimal_places=2,
        label="Asking price (USD)",
        help_text="Enter dollars and cents, for example 1250 or 1250.00.",
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "inputmode": "decimal"}),
    )
    currency = forms.CharField(required=False, widget=forms.HiddenInput(), initial="USD")
    street_address = forms.CharField(
        max_length=160,
        required=False,
        label="Street address (private)",
        help_text="Private to you and authorized staff. It is never shown publicly.",
    )
    additional_counties = forms.ModelMultipleChoiceField(
        queryset=County.objects.none(),
        required=False,
        label="List on Nearby Counties",
        help_text="Optional. Each selected county must be verified for the ZIP before saving.",
    )

    class Meta:
        model = Listing
        fields = (
            "category",
            "state",
            "county",
            "city",
            "title",
            "description",
            "broker_name",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "description": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        category_field = cast(forms.ModelChoiceField, self.fields["category"])  # type: ignore[type-arg]
        vertical_field = cast(forms.ModelChoiceField, self.fields["vertical"])  # type: ignore[type-arg]
        state_field = cast(forms.ModelChoiceField, self.fields["state"])  # type: ignore[type-arg]
        county_field = cast(forms.ModelChoiceField, self.fields["county"])  # type: ignore[type-arg]
        additional_counties_field = cast(
            "forms.ModelMultipleChoiceField[County]", self.fields["additional_counties"]
        )
        category_field.queryset = active_postable_categories()
        vertical_field.queryset = Vertical.objects.filter(is_active=True).order_by(
            "display_order", "name"
        )
        state_field.queryset = State.objects.filter(is_active=True)
        county_field.queryset = County.objects.none()
        additional_counties_field.queryset = County.objects.none()
        state_value = (
            self.data.get("state") if self.is_bound else getattr(self.instance, "state_id", None)
        )
        selected_vertical = (
            self.data.get("vertical") if self.is_bound else self.initial.get("vertical")
        )
        if selected_vertical and str(selected_vertical).isdigit():
            category_field.queryset = category_field.queryset.filter(
                vertical_id=int(selected_vertical)
            )
        if state_value and str(state_value).isdigit():
            county_field.queryset = County.objects.filter(
                state_id=int(state_value), is_active=True
            ).order_by("name")
            additional_counties_field.queryset = county_field.queryset
        if self.instance.pk and self.instance.price_minor is not None:
            self.initial.setdefault(
                "asking_price", Decimal(self.instance.price_minor) / Decimal(100)
            )
        selected_category_id = self.data.get("category") if self.is_bound else None
        if not selected_category_id:
            selected_category_id = self.initial.get(
                "category", getattr(self.instance, "category_id", None)
            )
        selected_category = (
            category_field.queryset.filter(pk=selected_category_id)
            .select_related("vertical")
            .first()
            if selected_category_id
            else None
        )
        if selected_category is not None and broker_attribution_is_eligible(
            vertical=selected_category.vertical, category=selected_category
        ):
            self.fields["broker_name"] = _broker_name_field()
        else:
            self.fields.pop("broker_name")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        state = cleaned.get("state")
        vertical = cleaned.get("vertical")
        category = cleaned.get("category")
        if vertical is not None and category is not None and category.vertical_id != vertical.id:
            self.add_error("category", "Choose a category from the selected vertical.")
        _reject_ineligible_broker_submission(
            form=self,
            eligible=bool(
                vertical is not None
                and category is not None
                and broker_attribution_is_eligible(vertical=vertical, category=category)
            ),
        )
        county = cleaned.get("county")
        postal_code = (cleaned.get("postal_code") or "").strip()
        if state is not None and postal_code:
            candidates = zip_county_candidates(postal_code=postal_code, state_id=state.id)
            candidate_ids = {candidate.id for candidate in candidates}
            if not candidate_ids:
                self.add_error(
                    "postal_code",
                    "No offline ZIP-to-county candidates are loaded for this ZIP and state.",
                )
            if county is not None and county.id not in candidate_ids:
                self.add_error("county", "Choose a county offered for this ZIP and state.")
            additional = cleaned.get("additional_counties") or []
            if any(candidate.id not in candidate_ids for candidate in additional):
                self.add_error(
                    "additional_counties",
                    "Choose additional counties offered for this ZIP and state.",
                )
            if county is not None and any(candidate.id == county.id for candidate in additional):
                self.add_error("additional_counties", "Do not select the primary county twice.")
        mode = cleaned.get("price_mode")
        price = cleaned.pop("asking_price", None)
        if mode in {"fixed", "negotiable"} and price is None:
            self.add_error("asking_price", "Enter an asking price for this price mode.")
        if mode in {"contact", "free"} and price is not None:
            self.add_error("asking_price", "Remove the asking price for this price mode.")
        if price is not None and mode in {"fixed", "negotiable"}:
            cleaned["price_minor"] = int(price * 100)
            cleaned["currency"] = "USD"
        else:
            cleaned["price_minor"] = None
            cleaned["currency"] = ""
        return cleaned


class AutoListingForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Listing
        fields = (
            "category",
            "state",
            "county",
            "city",
            "title",
            "description",
            "price_minor",
            "currency",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "price_minor": forms.NumberInput(attrs={"min": 0}),
        }
        help_texts: ClassVar[dict[str, str]] = {
            "price_minor": "Enter the price in minor units (for example, cents).",
            "currency": "Use a three-letter ISO currency code, such as USD.",
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        category_field = cast(forms.ModelChoiceField, self.fields["category"])  # type: ignore[type-arg]
        state_field = cast(forms.ModelChoiceField, self.fields["state"])  # type: ignore[type-arg]
        county_field = cast(forms.ModelChoiceField, self.fields["county"])  # type: ignore[type-arg]
        category_field.queryset = active_postable_categories().filter(vertical__slug="autos")
        state_field.queryset = State.objects.filter(is_active=True)
        county_field.queryset = County.objects.filter(is_active=True).select_related("state")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        _reject_ineligible_broker_submission(form=self, eligible=False)
        return cleaned


class AutoDetailsForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = AutoDetails
        fields = ("vehicle_type", "year", "make", "model", "trim", "mileage", "title_status", "vin")
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "year": forms.NumberInput(attrs={"min": 1886, "max": 9999}),
            "mileage": forms.NumberInput(attrs={"min": 0}),
        }
        help_texts: ClassVar[dict[str, str]] = {
            "vin": "Optional. It is restricted to you and authorized staff and is never public.",
        }


class PropertyListingForm(forms.ModelForm):  # type: ignore[type-arg]
    vertical_slug: ClassVar[str]

    class Meta:
        model = Listing
        fields = (
            "category",
            "state",
            "county",
            "city",
            "title",
            "description",
            "broker_name",
            "price_minor",
            "currency",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "price_minor": forms.NumberInput(attrs={"min": 0}),
        }
        help_texts: ClassVar[dict[str, str]] = {
            "price_minor": "Enter the price in minor units (for example, cents).",
            "currency": "Use a three-letter ISO currency code, such as USD.",
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        category_field = cast(forms.ModelChoiceField, self.fields["category"])  # type: ignore[type-arg]
        state_field = cast(forms.ModelChoiceField, self.fields["state"])  # type: ignore[type-arg]
        county_field = cast(forms.ModelChoiceField, self.fields["county"])  # type: ignore[type-arg]
        category_field.queryset = active_postable_categories().filter(
            vertical__slug=self.vertical_slug
        )
        state_field.queryset = State.objects.filter(is_active=True)
        county_field.queryset = County.objects.filter(is_active=True).select_related("state")
        if self.vertical_slug in {"real-estate", "rentals", "farm-ranch"}:
            self.fields["broker_name"] = _broker_name_field()
        else:
            self.fields.pop("broker_name")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        _reject_ineligible_broker_submission(
            form=self, eligible=self.vertical_slug in {"real-estate", "rentals", "farm-ranch"}
        )
        return cleaned


class HomeListingForm(PropertyListingForm):
    vertical_slug = "real-estate"


class RentalListingForm(PropertyListingForm):
    vertical_slug = "rentals"


class AgEquipmentListingForm(PropertyListingForm):
    vertical_slug = "farm-ranch"


class LivestockListingForm(PropertyListingForm):
    vertical_slug = "livestock-animals"


class PastureListingForm(PropertyListingForm):
    vertical_slug = "farm-ranch"


class HomeGardenListingForm(PropertyListingForm):
    vertical_slug = "home-garden"


class AppliancesListingForm(PropertyListingForm):
    vertical_slug = "appliances"


class HomeDetailsForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = HomeDetails
        fields = (
            "property_type",
            "beds",
            "baths",
            "square_feet",
            "year_built",
            "lot_size",
            "lot_size_unit",
            "street_address",
            "address_line_2",
            "postal_code",
            "general_area",
            "exact_address_public",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "beds": forms.NumberInput(attrs={"min": 0}),
            "baths": forms.NumberInput(attrs={"min": 0, "step": "0.1"}),
            "square_feet": forms.NumberInput(attrs={"min": 0}),
            "year_built": forms.NumberInput(attrs={"min": 1, "max": 9999}),
            "lot_size": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }
        help_texts: ClassVar[dict[str, str]] = {
            "general_area": (
                "Shown in future public property surfaces; do not enter an exact address."
            ),
            "exact_address_public": (
                "Off by default. Future public display requires a street address."
            ),
        }


class RentalDetailsForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = RentalDetails
        fields = (
            "rental_type",
            "monthly_rent_minor",
            "security_deposit_minor",
            "beds",
            "baths",
            "available_date",
            "pets_policy",
            "lease_term_months",
            "flexible_term",
            "street_address",
            "address_line_2",
            "postal_code",
            "general_area",
            "exact_address_public",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "monthly_rent_minor": forms.NumberInput(attrs={"min": 0}),
            "security_deposit_minor": forms.NumberInput(attrs={"min": 0}),
            "beds": forms.NumberInput(attrs={"min": 0}),
            "baths": forms.NumberInput(attrs={"min": 0, "step": "0.1"}),
            "available_date": forms.DateInput(attrs={"type": "date"}),
            "lease_term_months": forms.NumberInput(attrs={"min": 1}),
        }
        help_texts: ClassVar[dict[str, str]] = {
            "monthly_rent_minor": "Enter the monthly rent in minor units (for example, cents).",
            "security_deposit_minor": (
                "Enter the security deposit in minor units (for example, cents)."
            ),
            "general_area": (
                "Shown in future public property surfaces; do not enter an exact address."
            ),
            "exact_address_public": (
                "Off by default. Future public display requires a street address."
            ),
        }


class AgEquipmentDetailsForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = AgEquipmentDetails
        fields = ("equipment_type", "make", "model", "year", "hours", "powered", "condition")
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "year": forms.NumberInput(attrs={"min": 1, "max": 9999}),
            "hours": forms.NumberInput(attrs={"min": 0}),
        }


class LivestockDetailsForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = LivestockDetails
        fields = ("species", "breed", "animal_class", "head_count", "age_or_weight", "sale_unit")
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "head_count": forms.NumberInput(attrs={"min": 1}),
        }
        help_texts: ClassVar[dict[str, str]] = {
            "age_or_weight": "Optional general age or weight description only.",
        }


class PastureDetailsForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = PastureDetails
        fields = (
            "acreage",
            "water_available",
            "fenced",
            "lease_term",
            "use_restrictions",
            "available_date",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "acreage": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "available_date": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts: ClassVar[dict[str, str]] = {
            "use_restrictions": (
                "Optional general use restrictions; do not include an exact address."
            ),
        }


class HomeGoodsDetailsForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = HomeGoodsDetails
        fields = (
            "item_type",
            "brand",
            "condition",
            "working_status",
            "dimensions",
            "fulfillment_preference",
        )
        help_texts: ClassVar[dict[str, str]] = {
            "item_type": "Describe the item type or category.",
            "dimensions": "Optional. For example: 30 in W x 28 in D x 36 in H.",
        }
