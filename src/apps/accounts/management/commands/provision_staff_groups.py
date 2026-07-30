from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

ROLE_PERMISSIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "moderator": (
        ("listings", "moderate_listing"),
        ("listings", "view_listing"),
        ("listings", "view_moderationaction"),
        ("reports", "triage_listingreport"),
        ("reports", "view_listingreport"),
        ("reports", "view_listingreportaction"),
        ("accounts", "view_user"),
    ),
    "support": (
        ("accounts", "view_user"),
        ("accounts", "change_user"),
        ("accounts", "view_accountsecurityevent"),
        ("listings", "view_listing"),
    ),
    "finance": (
        ("billing", "view_order"),
        ("billing", "change_order"),
        ("billing", "view_paymentevent"),
        ("listings", "view_listing"),
    ),
    "operations": (
        ("catalog", "view_category"),
        ("catalog", "change_category"),
        ("locations", "view_county"),
        ("locations", "change_county"),
        ("policies", "view_policydocument"),
        ("core", "view_outboxevent"),
    ),
}


class Command(BaseCommand):
    help = "Create or reconcile least-privilege marketplace staff groups; does not assign users."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("provision_staff_groups may only run with DEBUG enabled.")
        for role, permission_keys in ROLE_PERMISSIONS.items():
            permissions = list(
                Permission.objects.filter(
                    content_type__app_label__in=[
                        app_label for app_label, _codename in permission_keys
                    ]
                ).filter(codename__in=[codename for _app_label, codename in permission_keys])
            )
            found_keys = {
                (permission.content_type.app_label, permission.codename)
                for permission in permissions
            }
            missing = set(permission_keys) - found_keys
            if missing:
                missing_text = ", ".join(f"{app}.{codename}" for app, codename in sorted(missing))
                raise RuntimeError(f"Missing required permissions: {missing_text}")
            group, _created = Group.objects.get_or_create(name=role)
            group.permissions.set(permissions)
            self.stdout.write(f"{role}: {len(permissions)} permissions reconciled")
