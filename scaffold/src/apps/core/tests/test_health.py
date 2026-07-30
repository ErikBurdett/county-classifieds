from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_home_page_uses_foundation_template(client: Client) -> None:
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert b"marketplace foundation is running" in response.content.lower()


def test_liveness(client: Client) -> None:
    response = client.get(reverse("core:liveness"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness(client: Client) -> None:
    response = client.get(reverse("core:readiness"))
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_hides_database_failure_details(client: Client) -> None:
    with patch("apps.core.views.connection.cursor", side_effect=RuntimeError("private detail")):
        response = client.get(reverse("core:readiness"))
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert b"private detail" not in response.content
