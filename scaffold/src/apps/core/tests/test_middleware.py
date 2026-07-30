from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from apps.core.middleware import RequestIdFilter, RequestIdMiddleware, get_request_id


def _response(_request: HttpRequest) -> HttpResponse:
    assert get_request_id() != "-"
    return HttpResponse("ok")


def test_request_id_middleware_accepts_safe_identifier() -> None:
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID="request-123")
    response = RequestIdMiddleware(_response)(request)
    assert response["X-Request-ID"] == "request-123"
    assert get_request_id() == "-"


def test_request_id_middleware_replaces_unsafe_identifier() -> None:
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID="unsafe\nlog")
    response = RequestIdMiddleware(_response)(request)
    assert response["X-Request-ID"] != "unsafe\nlog"


def test_request_id_filter_populates_log_record() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
    assert RequestIdFilter().filter(record)
    assert record.__dict__["request_id"] == "-"


def test_request_id_context_resets_after_exception() -> None:
    def failing_response(_request: HttpRequest) -> HttpResponse:
        assert get_request_id() != "-"
        raise RuntimeError("expected test failure")

    request = RequestFactory().get("/")
    try:
        RequestIdMiddleware(failing_response)(request)
    except RuntimeError as exc:
        assert str(exc) == "expected test failure"
    else:
        raise AssertionError("middleware did not propagate the response exception")
    assert get_request_id() == "-"
