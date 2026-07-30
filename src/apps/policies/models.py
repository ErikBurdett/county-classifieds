from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PolicyDocumentKind(models.TextChoices):
    TERMS = "terms", "Terms"
    PRIVACY = "privacy", "Privacy"
    REFUNDS = "refunds", "Refunds"
    PROHIBITED_ITEMS = "prohibited_items", "Prohibited items"
    CONTENT_RIGHTS = "content_rights", "Content rights"
    COMMUNICATIONS = "communications", "Communications"


class PolicyDocumentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    RETIRED = "retired", "Retired"


class PolicyDocument(models.Model):
    """Versioned owner-authored policy source; draft content is never presented as binding."""

    kind = models.CharField(max_length=32, choices=PolicyDocumentKind.choices)
    version = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=160)
    body = models.TextField()
    status = models.CharField(
        max_length=16, choices=PolicyDocumentStatus.choices, default=PolicyDocumentStatus.DRAFT
    )
    requires_listing_acceptance = models.BooleanField(default=True)
    legal_entity_name = models.CharField(max_length=200, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("kind", "version"), name="policies_kind_version_unique"
            ),
            models.UniqueConstraint(
                fields=("kind",),
                condition=models.Q(status=PolicyDocumentStatus.ACTIVE),
                name="policies_one_active_per_kind",
            ),
            models.CheckConstraint(
                condition=~models.Q(status=PolicyDocumentStatus.ACTIVE, legal_entity_name=""),
                name="policies_active_entity_required",
            ),
        ]
        ordering = ("kind", "-version")

    def __str__(self) -> str:
        return f"{self.get_kind_display()} v{self.version}"

    def clean(self) -> None:
        super().clean()
        if self.status == PolicyDocumentStatus.ACTIVE and not self.legal_entity_name.strip():
            raise ValidationError(
                {"legal_entity_name": "A named legal entity is required before activation."}
            )


class PolicyAcceptance(models.Model):
    document = models.ForeignKey(
        PolicyDocument, on_delete=models.PROTECT, related_name="acceptances"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="policy_acceptances"
    )
    listing = models.ForeignKey(
        "listings.Listing",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="policy_acceptances",
    )
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("document", "user", "listing"), name="policies_acceptance_unique"
            )
        ]
        indexes = [models.Index(fields=("user", "document"), name="policies_acceptance_user_idx")]

    def __str__(self) -> str:
        return f"{self.user_id} accepted {self.document}"
