from __future__ import annotations

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import Listing, ListingStatus
from apps.locations.models import County, State
from apps.reports.models import ListingReport, ListingReportAction, ListingReportState

pytestmark = pytest.mark.django_db


@pytest.fixture
def public_listing() -> Listing:
    seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="seller@example.test", password="not-used"),
        display_name="Seller",
    )
    vertical = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=vertical, name="Cars", slug="cars")
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
    return Listing.objects.create(
        seller=seller,
        vertical=vertical,
        category=category,
        state=state,
        county=county,
        city="Amarillo",
        title="Public listing",
        description="Description",
        price_minor=100,
        currency="USD",
        status=ListingStatus.PUBLISHED,
        published_at=timezone.now(),
    )


def report_payload(**overrides: str) -> dict[str, str]:
    return {
        "reason": "scam",
        "description": "Please review this listing.",
        "email": "reporter@example.test",
        **overrides,
    }


def test_anonymous_public_report_creates_hashed_audit_and_never_shows_seller(
    client: Client, public_listing: Listing
) -> None:
    response = client.post(
        reverse("reports:report_listing", args=(public_listing.id,)),
        report_payload(),
        REMOTE_ADDR="2001:0db8::1",
    )

    report = ListingReport.objects.get()
    assert response.status_code == 200
    assert b"Thank you" in response.content
    assert report.source_ip_hash != "2001:0db8::1"
    assert len(report.source_ip_hash) == 64
    assert report.reporter is None
    assert report.reporter_email == "reporter@example.test"
    assert ListingReportAction.objects.filter(report=report, action_type="submitted").exists()
    client.force_login(public_listing.seller.user)
    seller_page = client.get(reverse("listings:dashboard"))
    assert b"reporter@example.test" not in seller_page.content


def test_report_post_requires_csrf_and_hidden_listing_has_generic_receipt(
    public_listing: Listing,
) -> None:
    client = Client(enforce_csrf_checks=True)
    url = reverse("reports:report_listing", args=(public_listing.id,))
    assert client.post(url, report_payload()).status_code == 403

    public_listing.status = ListingStatus.DRAFT
    public_listing.published_at = None
    public_listing.save(update_fields=("status", "published_at"))
    response = Client().post(url, report_payload())
    assert response.status_code == 200
    assert b"Thank you" in response.content
    assert not ListingReport.objects.exists()


def test_report_templates_have_one_main_landmark(client: Client, public_listing: Listing) -> None:
    form = client.get(reverse("reports:report_listing", args=(public_listing.id,)))
    receipt = client.post(
        reverse("reports:report_listing", args=(public_listing.id,)), report_payload()
    )

    assert form.content.count(b"<main") == 1
    assert receipt.content.count(b"<main") == 1


@override_settings(
    REPORT_RATE_SOURCE_LIMIT=1, REPORT_RATE_LISTING_LIMIT=10, REPORT_RATE_USER_LIMIT=10
)
def test_duplicate_and_rate_limited_reports_have_generic_receipt(
    client: Client, public_listing: Listing
) -> None:
    url = reverse("reports:report_listing", args=(public_listing.id,))
    first = client.post(url, report_payload(), REMOTE_ADDR="192.0.2.1")
    second = client.post(url, report_payload(description="Different"), REMOTE_ADDR="192.0.2.1")

    assert first.content == second.content
    assert ListingReport.objects.count() == 1


def test_authenticated_reporter_and_staff_triage_are_permission_gated(
    client: Client, public_listing: Listing
) -> None:
    reporter = User.objects.create_user(email="reporter@example.test", password="not-used")
    client.force_login(reporter)
    client.post(
        reverse("reports:report_listing", args=(public_listing.id,)), report_payload(email="")
    )
    report = ListingReport.objects.get()
    assert report.reporter == reporter

    staff = User.objects.create_user(email="staff@example.test", password="not-used", is_staff=True)
    client.force_login(staff)
    assert client.get(reverse("reports:queue")).status_code == 403
    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="reports", codename="triage_listingreport")
    )
    assert client.get(reverse("reports:queue")).status_code == 200
    response = client.post(
        reverse("reports:triage", args=(report.id,)),
        {
            f"{report.id}-action": "acknowledge",
            f"{report.id}-internal_note": "Reviewing.",
        },
    )
    report.refresh_from_db()
    assert response.status_code == 302
    assert report.state == ListingReportState.ACKNOWLEDGED
    assert report.assigned_to == staff
    action = report.actions.last()
    assert action is not None
    assert action.internal_note == "Reviewing."


def test_staff_queue_uses_unique_prefixed_forms_and_safe_reviewer_context(
    client: Client, public_listing: Listing
) -> None:
    reporter = User.objects.create_user(email="account-reporter@example.test", password="not-used")
    explicit_report = ListingReport.objects.create(
        listing=public_listing,
        reason="scam",
        reporter_email="explicit-reporter@example.test",
        source_ip_hash="a" * 64,
        duplicate_fingerprint="b" * 64,
    )
    account_report = ListingReport.objects.create(
        listing=public_listing,
        reporter=reporter,
        reason="inaccurate",
        source_ip_hash="c" * 64,
        duplicate_fingerprint="d" * 64,
    )
    hidden_listing = public_listing
    hidden_listing.status = ListingStatus.DRAFT
    hidden_listing.published_at = None
    hidden_listing.save(update_fields=("status", "published_at"))
    hidden_report = ListingReport.objects.create(
        listing=hidden_listing,
        reason="abuse_other",
        source_ip_hash="e" * 64,
        duplicate_fingerprint="f" * 64,
    )
    staff = User.objects.create_user(
        email="triager@example.test", password="not-used", is_staff=True
    )
    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="reports", codename="triage_listingreport")
    )
    client.force_login(staff)

    response = client.get(reverse("reports:queue"))
    content = response.content.decode()

    assert response.status_code == 200
    assert f'id="{explicit_report.id}-action"' not in content
    assert f'id="id_{explicit_report.id}-action"' in content
    assert f'id="id_{account_report.id}-action"' in content
    assert f'name="{explicit_report.id}-action"' in content
    assert f'name="{account_report.id}-action"' in content
    assert "explicit-reporter@example.test" in content
    assert "account-reporter@example.test" in content
    assert (
        reverse(
            "locations:listing_detail",
            args=(public_listing.state.slug, public_listing.county.slug, public_listing.id),
        )
        not in content
    )
    assert f'action="{reverse("reports:triage", args=(hidden_report.id,))}"' in content


def test_queue_links_public_listing_and_moderation_only_with_permission(
    client: Client, public_listing: Listing
) -> None:
    report = ListingReport.objects.create(
        listing=public_listing,
        reason="scam",
        source_ip_hash="a" * 64,
        duplicate_fingerprint="b" * 64,
    )
    staff = User.objects.create_user(
        email="triager@example.test", password="not-used", is_staff=True
    )
    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="reports", codename="triage_listingreport")
    )
    client.force_login(staff)

    without_moderation = client.get(reverse("reports:queue")).content.decode()
    assert "Open moderation queue" not in without_moderation
    assert (
        reverse(
            "locations:listing_detail",
            args=(public_listing.state.slug, public_listing.county.slug, report.listing_id),
        )
        in without_moderation
    )

    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="listings", codename="moderate_listing")
    )
    with_moderation = client.get(reverse("reports:queue")).content.decode()
    assert "Open moderation queue" in with_moderation
    assert reverse("listings:moderation_queue") in with_moderation


def test_triage_requires_csrf_and_reports_success_or_closed_feedback(
    public_listing: Listing,
) -> None:
    staff = User.objects.create_user(
        email="triager@example.test", password="not-used", is_staff=True
    )
    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="reports", codename="triage_listingreport")
    )
    report = ListingReport.objects.create(
        listing=public_listing,
        reason="scam",
        source_ip_hash="a" * 64,
        duplicate_fingerprint="b" * 64,
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(staff)
    triage_url = reverse("reports:triage", args=(report.id,))
    payload = {
        f"{report.id}-action": "acknowledge",
        f"{report.id}-internal_note": "Reviewing.",
    }

    assert client.post(triage_url, payload).status_code == 403
    queue = client.get(reverse("reports:queue"))
    csrf_token = queue.cookies["csrftoken"].value
    invalid = client.post(
        triage_url,
        {
            f"{report.id}-action": "not-an-action",
            f"{report.id}-internal_note": "",
            "csrfmiddlewaretoken": csrf_token,
        },
        HTTP_REFERER="http://testserver/staff/reports/",
        follow=True,
    )
    assert "was not recorded" in invalid.content.decode()
    report.refresh_from_db()
    assert report.state == ListingReportState.OPEN

    success = client.post(
        triage_url,
        {**payload, "csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER="http://testserver/staff/reports/",
        follow=True,
    )
    report.refresh_from_db()
    assert report.state == ListingReportState.ACKNOWLEDGED
    assert "Report action recorded." in success.content.decode()

    report.state = ListingReportState.RESOLVED
    report.save(update_fields=("state", "updated_at"))
    closed = client.post(
        triage_url,
        {
            f"{report.id}-action": "dismiss",
            f"{report.id}-internal_note": "",
            "csrfmiddlewaretoken": csrf_token,
        },
        HTTP_REFERER="http://testserver/staff/reports/",
        follow=True,
    )
    assert "already closed or stale" in closed.content.decode()


def test_report_actions_are_append_only(public_listing: Listing) -> None:
    report = ListingReport.objects.create(
        listing=public_listing,
        reason="scam",
        source_ip_hash="a" * 64,
        duplicate_fingerprint="b" * 64,
    )
    action = ListingReportAction.objects.create(
        report=report, action_type="submitted", from_state="open", to_state="open"
    )
    with pytest.raises(ValueError):
        action.save()
    with pytest.raises(ValueError):
        action.delete()
