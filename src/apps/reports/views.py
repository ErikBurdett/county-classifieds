from __future__ import annotations

from contextlib import suppress
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.listings.selectors import public_listings

from .forms import PublicListingReportForm, TriageListingReportForm
from .models import ListingReport
from .selectors import triage_metrics, triage_queue
from .services import (
    ReportSubmission,
    ReportSubmissionSuppressedError,
    submit_listing_report,
    transition_listing_report,
)


def _receipt(request: HttpRequest) -> HttpResponse:
    return render(request, "reports/receipt.html")


@require_http_methods(["GET", "POST"])
def report_listing(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    if request.method == "GET":
        if not public_listings().filter(pk=listing_id).exists():
            raise Http404("Listing not found.")
        return render(
            request,
            "reports/report_form.html",
            {"form": PublicListingReportForm(), "listing_id": listing_id},
        )

    form = PublicListingReportForm(request.POST)
    if not form.is_valid():
        # Retain safe validation feedback only when the listing remains public.
        if public_listings().filter(pk=listing_id).exists():
            return render(
                request,
                "reports/report_form.html",
                {"form": form, "listing_id": listing_id},
                status=400,
            )
        return _receipt(request)
    reporter = (
        request.user if isinstance(request.user, User) and request.user.is_authenticated else None
    )
    with suppress(ReportSubmissionSuppressedError):
        submit_listing_report(
            submission=ReportSubmission(
                listing_id=listing_id,
                reason=form.cleaned_data["reason"],
                description=form.cleaned_data["description"],
                reporter_email=form.cleaned_data["email"],
                source_ip=request.META.get("REMOTE_ADDR", ""),
                reporter=reporter,
            )
        )
    return _receipt(request)


@login_required
@permission_required("reports.triage_listingreport", raise_exception=True)
def queue(request: HttpRequest) -> HttpResponse:
    reports = triage_queue()
    return render(
        request,
        "reports/queue.html",
        {
            "report_rows": [
                {
                    "report": report,
                    "form": TriageListingReportForm(prefix=str(report.id)),
                }
                for report in reports
            ],
            "metrics": triage_metrics(),
            "can_moderate_listings": request.user.has_perm("listings.moderate_listing"),
        },
    )


@login_required
@permission_required("reports.triage_listingreport", raise_exception=True)
@require_http_methods(["POST"])
def triage(request: HttpRequest, report_id: UUID) -> HttpResponse:
    form = TriageListingReportForm(request.POST, prefix=str(report_id))
    if not form.is_valid():
        messages.error(
            request,
            "The report action was not recorded. Select a valid action and correct any errors.",
        )
        return redirect("reports:queue")
    try:
        transition_listing_report(
            report_id=report_id,
            actor=request.user,  # type: ignore[arg-type]
            action=form.cleaned_data["action"],
            internal_note=form.cleaned_data["internal_note"],
        )
    except ListingReport.DoesNotExist:
        messages.error(request, "That report is no longer available for review.")
    except PermissionDenied:
        messages.error(request, "You do not have permission to record this report action.")
    except ValidationError:
        messages.error(
            request, "This report cannot be changed because it is already closed or stale."
        )
    else:
        messages.success(request, "Report action recorded.")
    return redirect("reports:queue")
