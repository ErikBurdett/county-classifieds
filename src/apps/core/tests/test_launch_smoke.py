from __future__ import annotations

import pytest
from django.core.management import call_command
from django.test import override_settings

pytestmark = pytest.mark.django_db


@override_settings(ALLOWED_HOSTS=["localhost", "127.0.0.1"])
def test_local_launch_smoke_command_uses_local_allowed_host() -> None:
    call_command("launch_smoke")
