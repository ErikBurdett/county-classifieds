from __future__ import annotations

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.MarketplaceLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("seller-profile/", views.seller_profile, name="seller_profile"),
    path(
        "sellers/<uuid:public_id>/",
        views.public_seller_profile_view,
        name="public_seller_profile",
    ),
    path(
        "sellers/<uuid:public_id>/avatar/",
        views.public_seller_avatar,
        name="public_seller_avatar",
    ),
    path("password-reset/", views.MarketplacePasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        views.MarketplacePasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
