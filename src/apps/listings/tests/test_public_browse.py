from __future__ import annotations

from pathlib import Path

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import Client
from django.test.utils import override_settings

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import (
    Listing,
    ListingStatus,
    ModerationAction,
    ModerationActionType,
    ModerationReasonCode,
)
from apps.listings.selectors import public_autos_listings
from apps.listings.services import (
    claim_listing,
    create_auto_draft,
    moderate_listing,
    publish_auto_listing,
    submit_listing,
    validate_submission_completeness,
)
from apps.locations.models import County, State
from apps.policies.models import PolicyAcceptance, PolicyDocument, PolicyDocumentStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def public_draft() -> Listing:
    seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="public@example.test", password="not-used"),
        display_name="Public seller",
    )
    autos = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=autos, name="Cars", slug="cars")
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    county = County.objects.create(
        fips="48375",
        state=state,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )
    return create_auto_draft(
        seller=seller,
        listing_values={
            "category": category,
            "state": state,
            "county": county,
            "city": "Amarillo",
            "title": "2020 Ford Mustang",
            "description": "Clean local sports car",
            "price_minor": 3000000,
            "currency": "USD",
        },
        auto_values={
            "vehicle_type": "car",
            "year": 2020,
            "make": "Ford",
            "model": "Mustang",
            "trim": "",
            "mileage": 12000,
            "title_status": "clean",
            "vin": "1HGCM82633A004352",
        },
    )


def test_publish_requires_complete_network_enabled_autos(public_draft: Listing) -> None:
    published = publish_auto_listing(listing_id=public_draft.id)

    assert published.status == ListingStatus.PUBLISHED
    assert published.published_at is not None

    with pytest.raises(ValidationError, match="Only draft"):
        publish_auto_listing(listing_id=public_draft.id)


def test_public_selector_excludes_drafts_and_disabled_references(public_draft: Listing) -> None:
    assert not public_autos_listings().filter(pk=public_draft.pk).exists()
    publish_auto_listing(listing_id=public_draft.id)
    assert public_autos_listings().filter(pk=public_draft.pk).exists()

    public_draft.county.is_network_enabled = False
    public_draft.county.save(update_fields=("is_network_enabled",))
    assert not public_autos_listings().filter(pk=public_draft.pk).exists()


def test_submission_and_approval_are_audited_and_public(public_draft: Listing) -> None:
    submit_listing(listing_id=public_draft.id, seller=public_draft.seller)
    public_draft.refresh_from_db()
    assert public_draft.status == ListingStatus.IN_REVIEW
    assert not public_autos_listings().filter(pk=public_draft.pk).exists()

    moderator = User.objects.create_superuser(email="moderator@example.test", password="not-used")
    moderate_listing(
        listing_id=public_draft.id,
        actor=moderator,
        revision=public_draft.lifecycle_revision,
        outcome=ModerationActionType.APPROVED,
    )
    public_draft.refresh_from_db()
    assert public_draft.status == ListingStatus.PUBLISHED
    assert public_autos_listings().filter(pk=public_draft.pk).exists()
    assert ModerationAction.objects.filter(listing=public_draft).count() == 3


def test_rejection_requires_reason_and_stale_revision_fails(public_draft: Listing) -> None:
    submit_listing(listing_id=public_draft.id, seller=public_draft.seller)
    public_draft.refresh_from_db()
    moderator = User.objects.create_superuser(email="moderator@example.test", password="not-used")
    reason = ModerationReasonCode.objects.create(
        code="test_reason", category="Test", seller_facing_text="Fix this."
    )
    with pytest.raises(ValidationError, match="reason"):
        moderate_listing(
            listing_id=public_draft.id,
            actor=moderator,
            revision=public_draft.lifecycle_revision,
            outcome=ModerationActionType.REJECTED,
        )
    moderate_listing(
        listing_id=public_draft.id,
        actor=moderator,
        revision=public_draft.lifecycle_revision,
        outcome=ModerationActionType.REJECTED,
        reason_code=reason,
        internal_note="Private only",
    )
    with pytest.raises(ValidationError, match="stale"):
        moderate_listing(
            listing_id=public_draft.id,
            actor=moderator,
            revision=public_draft.lifecycle_revision,
            outcome=ModerationActionType.APPROVED,
        )


def test_submit_view_is_owner_only_and_staff_queue_hides_internal_notes(
    client: Client, public_draft: Listing
) -> None:
    client.force_login(public_draft.seller.user)
    response = client.post(f"/dashboard/drafts/{public_draft.id}/submit/")
    assert response.status_code == 302
    public_draft.refresh_from_db()
    assert public_draft.status == ListingStatus.IN_REVIEW

    moderator = User.objects.create_superuser(email="moderator@example.test", password="not-used")
    reason = ModerationReasonCode.objects.create(
        code="privacy_test", category="Test", seller_facing_text="Seller-safe guidance."
    )
    client.force_login(moderator)
    queue = client.get("/staff/moderation/")
    assert queue.status_code == 200
    response = client.post(
        f"/staff/moderation/{public_draft.id}/",
        {
            "revision": public_draft.lifecycle_revision,
            "outcome": ModerationActionType.CHANGES_REQUESTED,
            "reason_code": reason.id,
            "seller_facing_note": "Update the title.",
            "internal_note": "Private only",
        },
    )
    assert response.status_code == 302
    client.force_login(public_draft.seller.user)
    response = client.get(f"/dashboard/drafts/{public_draft.id}/")
    assert b"Seller-safe guidance." in response.content
    assert b"Update the title." in response.content
    assert b"Private only" not in response.content


@override_settings(DEBUG=True)
def test_moderation_reason_seed_is_idempotent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    call_command("seed_moderation_reason_codes")
    call_command("seed_moderation_reason_codes")
    assert ModerationReasonCode.objects.filter(code="prohibited_weapons", version=1).count() == 1
    assert "Moderation reason codes ready" in capsys.readouterr().out


def test_claim_scanner_and_suspension_paths(public_draft: Listing) -> None:
    reason = ModerationReasonCode.objects.create(
        code="prohibited_weapons",
        category="Prohibited content",
        seller_facing_text="Weapons are not allowed.",
        requires_escalation=True,
    )
    public_draft.title = "Antique gun cabinet"
    public_draft.save(update_fields=("title",))
    submit_listing(listing_id=public_draft.id, seller=public_draft.seller)
    public_draft.refresh_from_db()
    assert ModerationAction.objects.filter(
        listing=public_draft,
        action_type=ModerationActionType.POLICY_FLAGGED,
        reason_code=reason,
    ).exists()

    moderator = User.objects.create_superuser(email="moderator@example.test", password="not-used")
    claimed = claim_listing(
        listing_id=public_draft.id, actor=moderator, revision=public_draft.lifecycle_revision
    )
    published = moderate_listing(
        listing_id=public_draft.id,
        actor=moderator,
        revision=claimed.lifecycle_revision,
        outcome=ModerationActionType.APPROVED,
    )
    suspended = moderate_listing(
        listing_id=public_draft.id,
        actor=moderator,
        revision=published.lifecycle_revision,
        outcome=ModerationActionType.SUSPENDED,
        reason_code=reason,
        seller_facing_note="Contact support.",
    )
    assert suspended.status == ListingStatus.SUSPENDED
    assert suspended.published_at is None


def test_moderation_permissions_assignment_and_inactive_reason(public_draft: Listing) -> None:
    submit_listing(listing_id=public_draft.id, seller=public_draft.seller)
    public_draft.refresh_from_db()
    ordinary_user = User.objects.create_user(email="ordinary@example.test", password="not-used")
    with pytest.raises(PermissionDenied):
        claim_listing(
            listing_id=public_draft.id,
            actor=ordinary_user,
            revision=public_draft.lifecycle_revision,
        )

    first = User.objects.create_superuser(email="first@example.test", password="not-used")
    claimed = claim_listing(
        listing_id=public_draft.id, actor=first, revision=public_draft.lifecycle_revision
    )
    second = User.objects.create_superuser(email="second@example.test", password="not-used")
    with pytest.raises(ValidationError, match="already assigned"):
        claim_listing(listing_id=public_draft.id, actor=second, revision=claimed.lifecycle_revision)

    inactive = ModerationReasonCode.objects.create(
        code="inactive", category="Test", seller_facing_text="Inactive", is_active=False
    )
    with pytest.raises(ValidationError, match="active"):
        moderate_listing(
            listing_id=public_draft.id,
            actor=first,
            revision=claimed.lifecycle_revision,
            outcome=ModerationActionType.REJECTED,
            reason_code=inactive,
        )


def test_submission_validation_and_unsupported_moderation_outcome(public_draft: Listing) -> None:
    other_seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="other@example.test", password="not-used"),
        display_name="Other seller",
    )
    with pytest.raises(PermissionDenied, match="owner"):
        validate_submission_completeness(listing=public_draft, seller=other_seller)

    submit_listing(listing_id=public_draft.id, seller=public_draft.seller)
    public_draft.refresh_from_db()
    moderator = User.objects.create_superuser(email="moderator@example.test", password="not-used")
    with pytest.raises(ValidationError, match="Unsupported"):
        moderate_listing(
            listing_id=public_draft.id,
            actor=moderator,
            revision=public_draft.lifecycle_revision,
            outcome=ModerationActionType.ESCALATED,
        )

    action = ModerationAction.objects.filter(listing=public_draft).first()
    assert action is not None
    assert str(action).endswith(": submitted")
    reason = ModerationReasonCode.objects.create(
        code="string_test", category="Test", seller_facing_text="Test"
    )
    assert str(reason) == "string_test"


def test_closed_review_cannot_be_claimed_or_suspended(public_draft: Listing) -> None:
    submit_listing(listing_id=public_draft.id, seller=public_draft.seller)
    public_draft.refresh_from_db()
    moderator = User.objects.create_superuser(email="moderator@example.test", password="not-used")
    reason = ModerationReasonCode.objects.create(
        code="closed_review", category="Test", seller_facing_text="Test"
    )
    rejected = moderate_listing(
        listing_id=public_draft.id,
        actor=moderator,
        revision=public_draft.lifecycle_revision,
        outcome=ModerationActionType.REJECTED,
        reason_code=reason,
    )
    with pytest.raises(ValidationError, match="claimed"):
        claim_listing(
            listing_id=public_draft.id, actor=moderator, revision=rejected.lifecycle_revision
        )
    with pytest.raises(ValidationError, match="published or in-review"):
        moderate_listing(
            listing_id=public_draft.id,
            actor=moderator,
            revision=rejected.lifecycle_revision,
            outcome=ModerationActionType.SUSPENDED,
            reason_code=reason,
        )


def test_policy_acceptance_is_required_and_recorded_before_owner_submission(
    client: Client, public_draft: Listing
) -> None:
    document = PolicyDocument.objects.create(
        kind="terms",
        version=1,
        title="Marketplace Terms",
        body="Terms body.",
        status=PolicyDocumentStatus.ACTIVE,
        legal_entity_name="County Post Local Demo LLC",
    )
    client.force_login(public_draft.seller.user)

    blocked = client.post(f"/dashboard/drafts/{public_draft.id}/submit/", follow=True)
    public_draft.refresh_from_db()
    assert public_draft.status == ListingStatus.DRAFT
    assert b"Accept each current listing policy" in blocked.content

    submitted = client.post(
        f"/dashboard/drafts/{public_draft.id}/submit/",
        {"accept_listing_policies": "yes"},
    )
    assert submitted.status_code == 302
    public_draft.refresh_from_db()
    assert public_draft.status == ListingStatus.IN_REVIEW
    assert PolicyAcceptance.objects.filter(
        document=document, user=public_draft.seller.user, listing=public_draft
    ).exists()


def test_policy_submission_requires_csrf(public_draft: Listing) -> None:
    PolicyDocument.objects.create(
        kind="terms",
        version=1,
        title="Marketplace Terms",
        body="Terms body.",
        status=PolicyDocumentStatus.ACTIVE,
        legal_entity_name="County Post Local Demo LLC",
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(public_draft.seller.user)

    response = client.post(
        f"/dashboard/drafts/{public_draft.id}/submit/",
        {"accept_listing_policies": "yes"},
    )

    assert response.status_code == 403
    assert not PolicyAcceptance.objects.exists()


@pytest.mark.parametrize(
    "query",
    [
        {"q": "Mustang"},
        {"category": "1"},
        {"min_price": "20000"},
        {"max_price": "40000"},
        {"min_year": "2019"},
        {"max_year": "2021"},
        {"make": "Ford"},
        {"model": "Mustang"},
        {"min_mileage": "10000"},
        {"max_mileage": "13000"},
        {"sort": "newest"},
        {"sort": "price_asc"},
        {"sort": "price_desc"},
        {"sort": "mileage_asc"},
        {"sort": "year_desc"},
    ],
)
def test_state_browse_supports_allowlisted_filters(
    client: Client, public_draft: Listing, query: dict[str, str]
) -> None:
    publish_auto_listing(listing_id=public_draft.id)
    if query.get("category") == "1":
        query["category"] = str(public_draft.category_id)
    response = client.get("/texas/", query)
    assert response.status_code == 200
    assert b"2020 Ford Mustang" in response.content
    assert b"1HGCM82633A004352" not in response.content


def test_state_browse_rejects_foreign_county_and_preserves_canonical_redirect(
    client: Client, public_draft: Listing
) -> None:
    publish_auto_listing(listing_id=public_draft.id)
    other_state = State.objects.create(
        fips="40",
        usps_code="OK",
        name="Oklahoma",
        slug="oklahoma",
        is_active=True,
        is_network_enabled=True,
    )
    foreign = County.objects.create(
        fips="40143",
        state=other_state,
        name="Tulsa",
        slug="tulsa",
        is_active=True,
        is_network_enabled=True,
    )
    response = client.get("/texas/", {"county": foreign.pk})
    assert response.status_code == 200
    assert b"Select a valid choice" in response.content
    assert b"filters need correction, so showing all available listings" in response.content
    assert b"2020 Ford Mustang" in response.content
    redirect = client.get("/TEXAS/?q=mustang")
    assert redirect["Location"] == "/texas/?q=mustang"


def test_missing_location_renders_branded_not_found_page(client: Client) -> None:
    response = client.get("/missing-market/")

    assert response.status_code == 404
    assert b"We could not find that market page" in response.content
    assert response.content.count(b"<main") == 1


def test_public_pages_render_grid_navigation_and_safe_listing_metadata(
    client: Client, public_draft: Listing
) -> None:
    publish_auto_listing(listing_id=public_draft.id)

    home_response = client.get("/")
    browse_response = client.get("/texas/")

    assert home_response.status_code == 200
    assert b"A better way to find regional listings" in home_response.content
    assert b"Find your market" in home_response.content
    assert b"<details" in home_response.content
    assert b"All active state markets" in home_response.content
    assert b"Latest listings" in home_response.content
    assert b'class="listing-card"' in home_response.content
    assert b"$30,000.00" in home_response.content
    assert b"1HGCM82633A004352" not in home_response.content
    assert browse_response.status_code == 200
    assert b"Browse Texas counties" in browse_response.content
    assert b"Filter listings" in browse_response.content
    assert b'aria-live="polite"' in browse_response.content

    filtered_response = client.get("/texas/", {"q": "Mustang"})
    assert b'href="/texas/">Reset filters</a>' in filtered_response.content
    assert b"filtered or sorted results" in filtered_response.content


def test_authenticated_navigation_and_global_success_messages(
    client: Client, public_draft: Listing
) -> None:
    publish_auto_listing(listing_id=public_draft.id)
    client.force_login(public_draft.seller.user)

    response = client.post(
        f"/favorites/{public_draft.id}/toggle/",
        {"next": "/texas/"},
        follow=True,
    )

    assert response.status_code == 200
    assert b">Saved listings</a>" in response.content
    assert b'class="message message--success"' in response.content
    assert b"Listing saved." in response.content


@override_settings(DEBUG=True)
def test_demo_seed_is_idempotent_without_printing_credentials(
    capsys: pytest.CaptureFixture[str],
) -> None:
    call_command("seed_demo_marketplace")
    call_command("seed_demo_marketplace")
    output = capsys.readouterr().out
    assert Listing.objects.filter(status=ListingStatus.PUBLISHED).count() == 12
    assert User.objects.filter(email__endswith="@local.test").count() == 4
    assert "LocalDemoOnly" not in output


@override_settings(DEBUG=True)
def test_demo_seed_merges_credentials_without_replacing_existing_entries(tmp_path: Path) -> None:
    credentials = tmp_path / "tmp" / "test-accounts.txt"
    credentials.parent.mkdir()
    credentials.write_text("admin@local.test: user-managed-value\n", encoding="utf-8")

    with override_settings(PROJECT_ROOT=tmp_path):
        call_command("seed_demo_marketplace")

    saved = credentials.read_text(encoding="utf-8")
    assert "admin@local.test: user-managed-value" in saved
    assert "telephoneheater@local.test: LocalDemoOnly-ChangeMe-2026!" in saved
    assert saved.count("admin@local.test") == 1
