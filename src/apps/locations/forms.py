from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar, cast

from django import forms
from django.db.models import Q, QuerySet

from apps.catalog.models import Category, Vertical
from apps.listings.models import (
    AgEquipmentDetails,
    HomeDetails,
    HomeGoodsDetails,
    Listing,
    LivestockDetails,
    RentalDetails,
)
from apps.listings.search import apply_text_search, postgres_search_available
from apps.locations.models import County

from .models import State


class ScopeChoiceField(forms.ChoiceField):
    """Accept legacy/invalid scope values so clean_scope can normalize safely."""

    def valid_value(self, _value: object) -> bool:
        return True


class AutosBrowseForm(forms.Form):
    SORT_CHOICES: ClassVar[tuple[tuple[str, str], ...]] = (
        ("newest", "Newest"),
        ("price_asc", "Price: low to high"),
        ("price_desc", "Price: high to low"),
        ("mileage_asc", "Mileage: low to high"),
        ("year_desc", "Year: newest first"),
    )
    q = forms.CharField(required=False, max_length=120, label="Search Autos")
    county = forms.ModelChoiceField(queryset=County.objects.none(), required=False)
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)
    min_price = forms.CharField(required=False, label="Minimum price (USD)")
    max_price = forms.CharField(required=False, label="Maximum price (USD)")
    min_year = forms.IntegerField(required=False, min_value=1886)
    max_year = forms.IntegerField(required=False, min_value=1886)
    make = forms.CharField(required=False, max_length=80)
    model = forms.CharField(required=False, max_length=80)
    min_mileage = forms.IntegerField(required=False, min_value=0)
    max_mileage = forms.IntegerField(required=False, min_value=0)
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES, initial="newest")

    def __init__(
        self, *args: Any, state: State, fixed_county: County | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fixed_county = fixed_county
        county_field = cast(forms.ModelChoiceField, self.fields["county"])  # type: ignore[type-arg]
        category_field = cast(forms.ModelChoiceField, self.fields["category"])  # type: ignore[type-arg]
        county_field.queryset = County.objects.filter(
            state=state, is_active=True, is_network_enabled=True
        ).order_by("name")
        category_field.queryset = Category.objects.filter(
            vertical__slug="autos", vertical__is_active=True, is_active=True
        ).order_by("name")
        if fixed_county is not None:
            self.fields.pop("county")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        for lower, upper in (
            ("min_year", "max_year"),
            ("min_mileage", "max_mileage"),
        ):
            if (
                cleaned.get(lower) is not None
                and cleaned.get(upper) is not None
                and cleaned[lower] > cleaned[upper]
            ):
                self.add_error(upper, "Must be greater than or equal to the minimum.")
        for field_name in ("min_price", "max_price"):
            value = cleaned.get(field_name)
            if not value:
                continue
            try:
                amount = Decimal(str(value))
            except InvalidOperation:
                self.add_error(field_name, "Enter a whole-dollar USD amount.")
                continue
            if amount < 0 or amount != amount.to_integral_value():
                self.add_error(field_name, "Enter a non-negative whole-dollar USD amount.")
                continue
            cleaned[field_name] = int(amount) * 100
        if (
            isinstance(cleaned.get("min_price"), int)
            and isinstance(cleaned.get("max_price"), int)
            and cleaned["min_price"] > cleaned["max_price"]
        ):
            self.add_error("max_price", "Must be greater than or equal to the minimum.")
        return cleaned


def apply_autos_filters(queryset: QuerySet[Listing], form: AutosBrowseForm) -> QuerySet[Listing]:
    values = form.cleaned_data
    if values.get("county"):
        queryset = queryset.filter(county=values["county"])
    if values.get("category"):
        queryset = queryset.filter(category=values["category"])
    if values.get("q"):
        query = values["q"]
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(auto_details__make__icontains=query)
            | Q(auto_details__model__icontains=query)
        )
    for param, lookup in (
        ("min_price", "price_minor__gte"),
        ("max_price", "price_minor__lte"),
        ("min_year", "auto_details__year__gte"),
        ("max_year", "auto_details__year__lte"),
        ("make", "auto_details__make__iexact"),
        ("model", "auto_details__model__iexact"),
        ("min_mileage", "auto_details__mileage__gte"),
        ("max_mileage", "auto_details__mileage__lte"),
    ):
        if values.get(param) not in (None, ""):
            queryset = queryset.filter(**{lookup: values[param]})
    ordering = {
        "newest": ("-published_at",),
        "price_asc": ("price_minor", "-published_at"),
        "price_desc": ("-price_minor", "-published_at"),
        "mileage_asc": ("auto_details__mileage", "-published_at"),
        "year_desc": ("-auto_details__year", "-published_at"),
    }
    return queryset.order_by(*ordering[values.get("sort") or "newest"])


class PublicMarketFinderForm(forms.Form):
    """Search the active nationwide directory without exposing staff flags."""

    q = forms.CharField(
        required=False,
        max_length=120,
        label="Search state or county",
        widget=forms.TextInput(
            attrs={
                "id": "market-search-q",
                "placeholder": "Search by state, county, or postal abbreviation",
                "autocomplete": "off",
            }
        ),
    )


class PublicBrowseForm(forms.Form):
    """Allowlisted public filters; never maps request keys to ORM lookups."""

    SORT_CHOICES: ClassVar[tuple[tuple[str, str], ...]] = (
        ("newest", "Newest"),
        ("price_asc", "Price: low to high"),
        ("price_desc", "Price: high to low"),
        ("mileage_asc", "Mileage: low to high (Autos)"),
        ("year_desc", "Year: newest first (Autos)"),
    )
    q = forms.CharField(
        required=False,
        max_length=120,
        label="Search listings",
        widget=forms.TextInput(attrs={"id": "listing-search-q"}),
    )
    scope = ScopeChoiceField(
        required=False,
        choices=(("state", "Statewide"), ("county", "This county")),
        initial="state",
        label="Browse scope",
    )
    vertical = forms.ModelChoiceField(queryset=Vertical.objects.none(), required=False)
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)
    county = forms.ModelChoiceField(queryset=County.objects.none(), required=False)
    min_price = forms.CharField(required=False, label="Minimum price (USD)")
    max_price = forms.CharField(required=False, label="Maximum price (USD)")
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES, initial="newest")
    min_year = forms.IntegerField(required=False, min_value=1886)
    max_year = forms.IntegerField(required=False, min_value=1886)
    make = forms.CharField(required=False, max_length=80)
    model = forms.CharField(required=False, max_length=80)
    min_mileage = forms.IntegerField(required=False, min_value=0)
    max_mileage = forms.IntegerField(required=False, min_value=0)
    nearby_radius = forms.IntegerField(
        required=False,
        min_value=10,
        max_value=250,
        initial=50,
        label="Nearby county distance",
        widget=forms.NumberInput(
            attrs={
                "type": "range",
                "min": 10,
                "max": 250,
                "step": 10,
                "value": 50,
                "data-nearby-radius": "",
            }
        ),
    )

    TYPED_FILTER_FIELDS: ClassVar[dict[str, tuple[str, ...]]] = {
        "autos": (
            "min_year",
            "max_year",
            "make",
            "model",
            "min_mileage",
            "max_mileage",
        ),
        "real-estate": (
            "home_property_type",
            "home_min_beds",
            "home_min_baths",
            "home_min_square_feet",
        ),
        "rentals": ("rental_type", "rental_min_beds", "rental_pets_policy"),
        "farm-ranch": (
            "equipment_type",
            "equipment_make",
            "equipment_min_year",
            "equipment_max_hours",
            "equipment_condition",
            "pasture_min_acreage",
            "pasture_water_available",
            "pasture_fenced",
            "pasture_lease_term",
        ),
        "livestock-animals": (
            "livestock_species",
            "livestock_breed",
            "livestock_sale_unit",
            "livestock_min_head_count",
        ),
        "home-garden": (
            "goods_item_type",
            "goods_brand",
            "goods_condition",
            "goods_working_status",
        ),
        "appliances": (
            "goods_item_type",
            "goods_brand",
            "goods_condition",
            "goods_working_status",
        ),
    }

    def query_parameters(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        retain_nearby_radius: bool = True,
    ) -> list[tuple[str, str]]:
        """Return a safe, canonical subset of successfully validated filters."""

        parameters: list[tuple[str, str]] = []
        for name in self.fields:
            if name in exclude or (name == "nearby_radius" and not retain_nearby_radius):
                continue
            value = self.cleaned_data.get(name)
            if value in (None, ""):
                continue
            if name in {"min_price", "max_price"}:
                price_minor = cast(int, value)
                parameters.append((name, str(price_minor // 100)))
            elif name in {"vertical", "category", "county"}:
                selected_model = cast(Any, value)
                parameters.append((name, str(selected_model.pk)))
            elif name == "scope":
                if value == "county":
                    parameters.append((name, value))
            elif name == "sort":
                if value != "newest" or self.data.get(name):
                    parameters.append((name, str(value)))
            else:
                parameters.append((name, str(value)))
        return parameters

    @property
    def visible_filter_groups(self) -> list[tuple[str, list[forms.BoundField]]]:
        """Return compact, vertical-scoped groups for the browse template."""

        common_names = (
            "q",
            "scope",
            "vertical",
            "category",
            "county",
            "min_price",
            "max_price",
            "sort",
            "nearby_radius",
        )
        groups = [
            ("Browse", [self[name] for name in common_names if name in self.fields]),
        ]
        typed_names = [name for name in self.fields if name not in common_names]
        if typed_names:
            groups.append(("Listing details", [self[name] for name in typed_names]))
        return groups

    def active_filter_labels(self) -> list[tuple[str, str]]:
        """Describe active, validated filters without reflecting arbitrary query keys."""

        labels: list[tuple[str, str]] = []
        for name, value in self.query_parameters():
            if name == "q":
                labels.append((name, f"Search: {value}"))
            elif name == "vertical":
                labels.append((name, f"Vertical: {self.cleaned_data[name].name}"))
            elif name == "category":
                labels.append((name, f"Category: {self.cleaned_data[name].name}"))
            elif name == "county":
                labels.append((name, f"County: {self.cleaned_data[name].name}"))
            elif name == "min_price":
                labels.append((name, f"Minimum price: ${int(value):,}"))
            elif name == "max_price":
                labels.append((name, f"Maximum price: ${int(value):,}"))
            elif name == "nearby_radius":
                labels.append((name, f"Nearby counties: {value} miles"))
            elif name == "scope":
                labels.append((name, "Scope: This county"))
            elif name == "sort" and value != "newest":
                choices = cast(
                    list[tuple[str, str]],
                    cast(forms.ChoiceField, self.fields[name]).choices,
                )
                sort_label = next(
                    (
                        choice_label
                        for choice_value, choice_label in choices
                        if choice_value == value
                    ),
                    str(value),
                )
                labels.append((name, f"Sort: {sort_label}"))
            elif name == "sort":
                continue
            else:
                labels.append((name, f"{self.fields[name].label}: {value}"))
        return labels

    def __init__(
        self, *args: Any, state: State, fixed_county: County | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        vertical_field = cast(forms.ModelChoiceField, self.fields["vertical"])  # type: ignore[type-arg]
        category_field = cast(forms.ModelChoiceField, self.fields["category"])  # type: ignore[type-arg]
        county_field = cast(forms.ModelChoiceField, self.fields["county"])  # type: ignore[type-arg]
        vertical_field.queryset = Vertical.objects.filter(is_active=True).order_by(
            "display_order", "name"
        )
        category_field.queryset = Category.objects.filter(
            is_active=True, vertical__is_active=True
        ).order_by("vertical__display_order", "display_order", "name")
        county_field.queryset = County.objects.filter(
            state=state, is_active=True, is_network_enabled=True
        ).order_by("name")
        selected_vertical_slug = self.data.get("vertical") if self.is_bound else None
        if selected_vertical_slug:
            category_field.queryset = category_field.queryset.filter(
                vertical_id=selected_vertical_slug
            )
        selected_vertical = (
            vertical_field.queryset.filter(pk=selected_vertical_slug).only("slug").first()
            if selected_vertical_slug
            else None
        )
        self._add_typed_filter_fields(
            vertical_slug=selected_vertical.slug if selected_vertical else None
        )
        if fixed_county is not None:
            self.fields.pop("county")
        else:
            self.fields.pop("nearby_radius")
            self.fields.pop("scope")

    def _add_typed_filter_fields(self, *, vertical_slug: str | None) -> None:
        """Install only the fixed typed filters meaningful to the selected vertical."""

        allowed = set(self.TYPED_FILTER_FIELDS.get(vertical_slug or "", ()))
        for field_name in (
            "min_year",
            "max_year",
            "make",
            "model",
            "min_mileage",
            "max_mileage",
        ):
            if field_name not in allowed:
                self.fields.pop(field_name)
        typed_fields: dict[str, forms.Field] = {
            "home_property_type": forms.ChoiceField(
                required=False,
                choices=(("", "Any property type"), *HomeDetails.PropertyType.choices),
                label="Property type",
            ),
            "home_min_beds": forms.IntegerField(
                required=False, min_value=0, max_value=99, label="Minimum beds"
            ),
            "home_min_baths": forms.DecimalField(
                required=False,
                min_value=Decimal("0"),
                max_value=Decimal("99.9"),
                decimal_places=1,
                label="Minimum baths",
            ),
            "home_min_square_feet": forms.IntegerField(
                required=False, min_value=0, max_value=9_999_999, label="Minimum square feet"
            ),
            "rental_type": forms.ChoiceField(
                required=False,
                choices=(("", "Any rental type"), *RentalDetails.RentalType.choices),
                label="Rental type",
            ),
            "rental_min_beds": forms.IntegerField(
                required=False, min_value=0, max_value=99, label="Minimum beds"
            ),
            "rental_pets_policy": forms.ChoiceField(
                required=False,
                choices=(("", "Any pets policy"), *RentalDetails.PetsPolicy.choices),
                label="Pets policy",
            ),
            "equipment_type": forms.ChoiceField(
                required=False,
                choices=(("", "Any equipment type"), *AgEquipmentDetails.EquipmentType.choices),
                label="Equipment type",
            ),
            "equipment_make": forms.CharField(
                required=False, max_length=80, label="Equipment make"
            ),
            "equipment_min_year": forms.IntegerField(
                required=False, min_value=1, max_value=9999, label="Minimum year"
            ),
            "equipment_max_hours": forms.IntegerField(
                required=False, min_value=0, max_value=9_999_999, label="Maximum hours"
            ),
            "equipment_condition": forms.ChoiceField(
                required=False,
                choices=(("", "Any condition"), *AgEquipmentDetails.Condition.choices),
                label="Equipment condition",
            ),
            "pasture_min_acreage": forms.DecimalField(
                required=False,
                min_value=Decimal("0.01"),
                max_value=Decimal("9999999999.99"),
                max_digits=12,
                decimal_places=2,
                label="Minimum acreage",
            ),
            "pasture_water_available": forms.ChoiceField(
                required=False,
                choices=(("", "Any water availability"), ("yes", "Water available")),
                label="Water availability",
            ),
            "pasture_fenced": forms.ChoiceField(
                required=False, choices=(("", "Any fencing"), ("yes", "Fenced")), label="Fencing"
            ),
            "pasture_lease_term": forms.CharField(
                required=False, max_length=100, label="Lease term"
            ),
            "livestock_species": forms.ChoiceField(
                required=False,
                choices=(("", "Any species"), *LivestockDetails.Species.choices),
                label="Species",
            ),
            "livestock_breed": forms.CharField(required=False, max_length=100, label="Breed"),
            "livestock_sale_unit": forms.ChoiceField(
                required=False,
                choices=(("", "Any sale unit"), *LivestockDetails.SaleUnit.choices),
                label="Sale unit",
            ),
            "livestock_min_head_count": forms.IntegerField(
                required=False, min_value=1, max_value=9_999_999, label="Minimum head count"
            ),
            "goods_item_type": forms.CharField(required=False, max_length=100, label="Item type"),
            "goods_brand": forms.CharField(required=False, max_length=80, label="Brand"),
            "goods_condition": forms.ChoiceField(
                required=False,
                choices=(("", "Any condition"), *HomeGoodsDetails.Condition.choices),
                label="Condition",
            ),
            "goods_working_status": forms.ChoiceField(
                required=False,
                choices=(("", "Any working status"), *HomeGoodsDetails.WorkingStatus.choices),
                label="Working status",
            ),
        }
        for name in allowed:
            if name in typed_fields:
                self.fields[name] = typed_fields[name]

    def clean_scope(self) -> str:
        """Invalid scope is intentionally a safe state default, not a form error."""

        return "county" if self.data.get("scope") == "county" else "state"

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        vertical = cleaned.get("vertical")
        category = cleaned.get("category")
        if category is not None and vertical is not None and category.vertical_id != vertical.id:
            self.add_error("category", "Choose a category from the selected vertical.")
        nearby_radius = cleaned.get("nearby_radius")
        if nearby_radius is not None and nearby_radius % 10:
            self.add_error("nearby_radius", "Choose a distance in 10-mile increments.")
        for field_name in ("min_price", "max_price"):
            value = cleaned.get(field_name)
            if not value:
                continue
            try:
                amount = Decimal(str(value))
            except InvalidOperation:
                self.add_error(field_name, "Enter a whole-dollar USD amount.")
                continue
            if amount < 0 or amount != amount.to_integral_value():
                self.add_error(field_name, "Enter a non-negative whole-dollar USD amount.")
                continue
            cleaned[field_name] = int(amount) * 100
        for lower, upper in (
            ("min_price", "max_price"),
            ("min_year", "max_year"),
            ("min_mileage", "max_mileage"),
        ):
            if (
                isinstance(cleaned.get(lower), int)
                and isinstance(cleaned.get(upper), int)
                and cleaned[lower] > cleaned[upper]
            ):
                self.add_error(upper, "Must be greater than or equal to the minimum.")
        return cleaned


def _apply_vertical_filters(
    queryset: QuerySet[Listing], *, values: dict[str, Any], vertical_slug: str
) -> QuerySet[Listing]:
    """Apply fixed detail lookups for a validated vertical only."""

    typed_lookups = {
        "autos": (
            ("min_year", "auto_details__year__gte"),
            ("max_year", "auto_details__year__lte"),
            ("make", "auto_details__make__iexact"),
            ("model", "auto_details__model__iexact"),
            ("min_mileage", "auto_details__mileage__gte"),
            ("max_mileage", "auto_details__mileage__lte"),
        ),
        "real-estate": (
            ("home_property_type", "home_details__property_type"),
            ("home_min_beds", "home_details__beds__gte"),
            ("home_min_baths", "home_details__baths__gte"),
            ("home_min_square_feet", "home_details__square_feet__gte"),
        ),
        "rentals": (
            ("rental_type", "rental_details__rental_type"),
            ("rental_min_beds", "rental_details__beds__gte"),
            ("rental_pets_policy", "rental_details__pets_policy"),
        ),
        "farm-ranch": (
            ("equipment_type", "ag_equipment_details__equipment_type"),
            ("equipment_make", "ag_equipment_details__make__iexact"),
            ("equipment_min_year", "ag_equipment_details__year__gte"),
            ("equipment_max_hours", "ag_equipment_details__hours__lte"),
            ("equipment_condition", "ag_equipment_details__condition"),
            ("pasture_min_acreage", "pasture_details__acreage__gte"),
            ("pasture_lease_term", "pasture_details__lease_term__iexact"),
        ),
        "livestock-animals": (
            ("livestock_species", "livestock_details__species"),
            ("livestock_breed", "livestock_details__breed__iexact"),
            ("livestock_sale_unit", "livestock_details__sale_unit"),
            ("livestock_min_head_count", "livestock_details__head_count__gte"),
        ),
        "home-garden": (
            ("goods_item_type", "home_goods_details__item_type__iexact"),
            ("goods_brand", "home_goods_details__brand__iexact"),
            ("goods_condition", "home_goods_details__condition"),
            ("goods_working_status", "home_goods_details__working_status"),
        ),
        "appliances": (
            ("goods_item_type", "home_goods_details__item_type__iexact"),
            ("goods_brand", "home_goods_details__brand__iexact"),
            ("goods_condition", "home_goods_details__condition"),
            ("goods_working_status", "home_goods_details__working_status"),
        ),
    }
    for parameter, lookup in typed_lookups.get(vertical_slug, ()):
        if values.get(parameter) not in (None, ""):
            queryset = queryset.filter(**{lookup: values[parameter]})
    if vertical_slug == "farm-ranch" and values.get("pasture_water_available") == "yes":
        queryset = queryset.filter(pasture_details__water_available=True)
    if vertical_slug == "farm-ranch" and values.get("pasture_fenced") == "yes":
        queryset = queryset.filter(pasture_details__fenced=True)
    return queryset


def apply_public_filters(queryset: QuerySet[Listing], form: PublicBrowseForm) -> QuerySet[Listing]:
    values = form.cleaned_data
    for field_name in ("county", "vertical", "category"):
        if values.get(field_name):
            queryset = queryset.filter(**{field_name: values[field_name]})
    if values.get("q"):
        queryset = apply_text_search(queryset, values["q"])
    for parameter, lookup in (("min_price", "price_minor__gte"), ("max_price", "price_minor__lte")):
        if values.get(parameter) not in (None, ""):
            queryset = queryset.filter(**{lookup: values[parameter]})
    vertical = values.get("vertical")
    if vertical:
        queryset = _apply_vertical_filters(
            queryset, values=values, vertical_slug=cast(Vertical, vertical).slug
        )
    ordering = {
        "newest": ("-published_at", "-id"),
        "price_asc": ("price_minor", "-published_at", "-id"),
        "price_desc": ("-price_minor", "-published_at", "-id"),
    }
    if values.get("sort") in {"mileage_asc", "year_desc"}:
        queryset = queryset.filter(vertical__slug="autos")
        ordering["mileage_asc"] = ("auto_details__mileage", "-published_at", "-id")
        ordering["year_desc"] = ("-auto_details__year", "-published_at", "-id")
    requested_ordering = ordering[values.get("sort") or "newest"]
    if values.get("q") and postgres_search_available():
        return queryset.order_by("-search_rank", *requested_ordering)
    return queryset.order_by(*requested_ordering)
