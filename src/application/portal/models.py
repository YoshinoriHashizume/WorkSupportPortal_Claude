from __future__ import annotations

from django.conf import settings
from django.db import models

from application.portal.domain.value_objects.access_status import (
    ACCESS_STATUS_APPROVED,
    ACCESS_STATUS_PENDING,
    ACCESS_STATUS_REJECTED,
)
from application.portal.domain.value_objects.usage_record import (
    USAGE_TYPE_EXPORT,
    USAGE_TYPE_LABELS,
    USAGE_TYPE_VIEW,
)


class UserFavoriteMenu(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_menus")
    menu_key = models.CharField(max_length=80)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "menu_key"], name="unique_user_favorite_menu"),
        ]
        indexes = [
            models.Index(fields=["user", "sort_order"], name="favorite_menu_user_order_idx"),
        ]


class UserAccessRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = ACCESS_STATUS_PENDING, "承認待ち"
        APPROVED = ACCESS_STATUS_APPROVED, "許可"
        REJECTED = ACCESS_STATUS_REJECTED, "拒否"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_request")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_access_requests",
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["status", "-requested_at"]
        indexes = [
            models.Index(fields=["status", "-requested_at"], name="access_req_status_idx"),
        ]


class PortalMenuGroupAccess(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portal_menu_group_accesses")
    group_key = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["group_key"]
        constraints = [
            models.UniqueConstraint(fields=["user", "group_key"], name="unique_user_menu_group_access"),
        ]
        indexes = [
            models.Index(fields=["user", "group_key"], name="menu_group_access_user_idx"),
        ]


class PortalNotice(models.Model):
    title = models.CharField(max_length=120)
    body = models.TextField()
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_portal_notices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="portal_notice_created_idx"),
            models.Index(fields=["is_published", "-created_at"], name="portal_notice_pub_idx"),
        ]


class MenuUsageLog(models.Model):
    """メニュー利用ログ（E-601）。追記のみ。"""

    class UsageType(models.TextChoices):
        VIEW = USAGE_TYPE_VIEW, USAGE_TYPE_LABELS[USAGE_TYPE_VIEW]
        EXPORT = USAGE_TYPE_EXPORT, USAGE_TYPE_LABELS[USAGE_TYPE_EXPORT]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portal_menu_usage_logs",
    )
    menu_key = models.CharField(max_length=80)
    usage_type = models.CharField(max_length=10, choices=UsageType.choices)
    used_at = models.DateTimeField()

    class Meta:
        ordering = ["-used_at"]
        indexes = [
            models.Index(fields=["used_at"], name="menu_usage_used_at_idx"),
            models.Index(fields=["menu_key", "-used_at"], name="menu_usage_menu_key_idx"),
            models.Index(fields=["user", "-used_at"], name="menu_usage_user_idx"),
            models.Index(fields=["usage_type", "-used_at"], name="menu_usage_type_idx"),
        ]
