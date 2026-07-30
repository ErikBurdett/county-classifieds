from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class Vertical(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    vertical = models.ForeignKey(Vertical, on_delete=models.PROTECT, related_name="categories")
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="children", blank=True, null=True
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("vertical", "slug"), name="catalog_category_vertical_slug_unique"
            )
        ]
        ordering = ("vertical__display_order", "display_order", "name")

    def __str__(self) -> str:
        return f"{self.vertical}: {self.name}"

    def clean(self) -> None:
        super().clean()
        self.slug = self.slug.lower()
        if self.parent and self.parent.vertical_id != self.vertical_id:
            raise ValidationError({"parent": "A category parent must use the same vertical."})


class PostingFieldType(models.TextChoices):
    TEXT = "text", "Text"
    INTEGER = "integer", "Whole number"
    BOOLEAN = "boolean", "Yes or no"
    CHOICE = "choice", "Choice"


class PostingFieldVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    OWNER_ONLY = "owner_only", "Owner only"
    STAFF_ONLY = "staff_only", "Staff only"


class CatalogPostingProfile(models.Model):
    """Seed-owned bounded supplemental facts for a postable catalog leaf."""

    category = models.OneToOneField(
        Category, on_delete=models.PROTECT, related_name="posting_profile"
    )
    version = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.category}: profile v{self.version}"


class CatalogPostingField(models.Model):
    profile = models.ForeignKey(
        CatalogPostingProfile, on_delete=models.PROTECT, related_name="fields"
    )
    key = models.SlugField(max_length=40)
    label = models.CharField(max_length=80)
    field_type = models.CharField(max_length=16, choices=PostingFieldType.choices)
    required = models.BooleanField(default=False)
    choices = models.JSONField(default=list, blank=True)
    visibility = models.CharField(
        max_length=16, choices=PostingFieldVisibility.choices, default=PostingFieldVisibility.PUBLIC
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    maximum = models.PositiveSmallIntegerField(null=True, blank=True)
    is_material = models.BooleanField(default=True)
    allow_public_search = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("profile", "key"), name="catalog_posting_field_profile_key_unique"
            )
        ]
        ordering = ("display_order", "key")

    def __str__(self) -> str:
        return f"{self.profile}: {self.key}"

    def clean(self) -> None:
        super().clean()
        self.key = self.key.lower()
        if self.field_type == PostingFieldType.CHOICE and not self.choices:
            raise ValidationError({"choices": "Choice fields require controlled choices."})
        if self.field_type != PostingFieldType.CHOICE and self.choices:
            raise ValidationError({"choices": "Only choice fields may define choices."})
        if self.allow_public_search and self.visibility != PostingFieldVisibility.PUBLIC:
            raise ValidationError(
                {"allow_public_search": "Only public fields may contribute to public search."}
            )


class ListingPriceMode(models.TextChoices):
    FIXED = "fixed", "Fixed price"
    NEGOTIABLE = "negotiable", "Negotiable"
    CONTACT = "contact", "Contact for price"
    FREE = "free", "Free"


class ListingProductUseCase(models.TextChoices):
    NEW_LISTING = "new_listing", "New listing"
    RENEWAL = "renewal", "Renewal"


class ListingKind(models.Model):
    vertical = models.ForeignKey(Vertical, on_delete=models.PROTECT, related_name="listing_kinds")
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("vertical", "name"),
                name="catalog_listing_kind_vertical_name_unique",
            )
        ]
        ordering = ("vertical__display_order", "name")

    def __str__(self) -> str:
        return f"{self.vertical}: {self.name}"

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        if self.is_active and self.vertical_id and not self.vertical.is_active:
            raise ValidationError(
                {"vertical": "An active listing kind requires an active vertical."}
            )


class ListingKindPriceMode(models.Model):
    listing_kind = models.ForeignKey(
        ListingKind,
        on_delete=models.PROTECT,
        related_name="supported_price_modes",
    )
    price_mode = models.CharField(max_length=16, choices=ListingPriceMode.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("listing_kind", "price_mode"),
                name="catalog_listing_kind_price_mode_unique",
            )
        ]
        ordering = ("listing_kind", "price_mode")

    def __str__(self) -> str:
        return f"{self.listing_kind}: {self.get_price_mode_display()}"


class ListingProduct(models.Model):
    listing_kind = models.ForeignKey(
        ListingKind,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )
    product_code = models.CharField(
        max_length=64,
        unique=True,
        validators=[RegexValidator(r"^[A-Z0-9][A-Z0-9_-]*$")],
    )
    use_case = models.CharField(max_length=16, choices=ListingProductUseCase.choices)
    price_mode = models.CharField(max_length=16, choices=ListingPriceMode.choices)
    is_free = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_generic_distribution = models.BooleanField(default=False)
    duration_days = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("listing_kind", "use_case", "price_mode"),
                name="catalog_product_kind_use_case_mode_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(listing_kind__isnull=False, is_generic_distribution=False)
                    | models.Q(listing_kind__isnull=True, is_generic_distribution=True)
                ),
                name="catalog_product_generic_target",
            ),
        ]
        ordering = ("listing_kind", "use_case", "price_mode", "product_code")

    def __str__(self) -> str:
        return self.product_code

    def clean(self) -> None:
        super().clean()
        self.product_code = self.product_code.upper()
        if self.is_generic_distribution:
            if self.listing_kind_id:
                raise ValidationError("Generic distribution products cannot use a listing kind.")
            return
        if not self.listing_kind_id:
            raise ValidationError({"listing_kind": "Products require a listing kind."})
        listing_kind = self.listing_kind
        assert listing_kind is not None
        if not listing_kind.is_active:
            raise ValidationError({"listing_kind": "Products require an active listing kind."})
        if not ListingKindPriceMode.objects.filter(
            listing_kind=listing_kind,
            price_mode=self.price_mode,
        ).exists():
            raise ValidationError(
                {"price_mode": "The product price mode is not supported by its kind."}
            )
        if self.is_free and listing_kind.vertical.slug == "autos":
            raise ValidationError({"is_free": "Autos products cannot be free."})


class ProductPrice(models.Model):
    product = models.ForeignKey(ListingProduct, on_delete=models.PROTECT, related_name="prices")
    currency = models.CharField(
        max_length=3,
        validators=[RegexValidator(r"^[A-Z]{3}$")],
    )
    amount_minor = models.PositiveBigIntegerField()
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_minor__gte=0),
                name="catalog_product_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(currency__regex=r"^[A-Z]{3}$"),
                name="catalog_product_price_currency_iso",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(effective_until__isnull=True)
                    | models.Q(effective_until__gt=models.F("effective_from"))
                ),
                name="catalog_product_price_valid_window",
            ),
        ]
        indexes = [
            models.Index(
                fields=("product", "currency", "effective_from"),
                name="catalog_price_lookup_idx",
            )
        ]
        ordering = ("product", "currency", "-effective_from")

    def __str__(self) -> str:
        return f"{self.product}: {self.amount_minor} {self.currency}"

    def clean(self) -> None:
        super().clean()
        self.currency = self.currency.upper()
        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValidationError({"effective_until": "The end must be after the effective start."})
        if not self.product_id:
            return
        if self.product.is_free and self.amount_minor != 0:
            raise ValidationError({"amount_minor": "Free products must have a zero price."})
        if not self.product.is_free and self.amount_minor == 0:
            raise ValidationError({"amount_minor": "Only free products may have a zero price."})
        listing_kind = self.product.listing_kind
        if (
            listing_kind is not None
            and listing_kind.vertical.slug == "autos"
            and self.amount_minor == 0
        ):
            raise ValidationError({"amount_minor": "Autos products cannot have a zero price."})
