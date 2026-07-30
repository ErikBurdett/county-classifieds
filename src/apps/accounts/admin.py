from __future__ import annotations

from typing import cast

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from .forms import MarketplaceUserChangeForm, MarketplaceUserCreationForm
from .models import AccountSecurityEvent, AccountStatus, SellerProfile, User
from .services import change_account_status


@admin.register(User)
class MarketplaceUserAdmin(UserAdmin):  # type: ignore[type-arg]
    add_form = MarketplaceUserCreationForm
    form = MarketplaceUserChangeForm
    model = User
    ordering = ("email",)
    list_display = ("email", "account_status", "is_staff", "is_active", "date_joined")
    list_filter = ("account_status", "is_staff", "is_superuser")
    readonly_fields = ("account_status",)
    actions = ("suspend_accounts", "restore_accounts", "close_accounts")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Name", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "account_status",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    @admin.action(description="Suspend selected accounts")
    def suspend_accounts(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        for subject in queryset:
            change_account_status(
                actor=cast(User, request.user),
                subject=subject,
                status=AccountStatus.SUSPENDED,
                request=request,
            )

    @admin.action(description="Restore selected accounts")
    def restore_accounts(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        for subject in queryset:
            change_account_status(
                actor=cast(User, request.user),
                subject=subject,
                status=AccountStatus.ACTIVE,
                request=request,
            )

    @admin.action(description="Close selected accounts")
    def close_accounts(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        for subject in queryset:
            change_account_status(
                actor=cast(User, request.user),
                subject=subject,
                status=AccountStatus.CLOSED,
                request=request,
            )


@admin.register(AccountSecurityEvent)
class AccountSecurityEventAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("occurred_at", "event_type", "actor", "subject")
    list_filter = ("event_type", "occurred_at")
    search_fields = ("actor__email", "subject__email")
    readonly_fields = (
        "actor",
        "subject",
        "event_type",
        "request_ip_hash",
        "user_agent",
        "request_id",
        "occurred_at",
    )

    def has_add_permission(self, _request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, _request: HttpRequest, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: HttpRequest, _obj: object | None = None) -> bool:
        return False


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("display_name", "user", "phone_verification_state", "phone")
    list_filter = ("phone_verification_state",)
    search_fields = ("display_name", "user__email", "phone")
    readonly_fields = ("created_at", "updated_at")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )
