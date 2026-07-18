from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .forms import StaffNotificationProfileForm
from .models import (
    KakaoConnection,
    NotificationConfiguration,
    NotificationDeliveryLog,
    NotificationJob,
    PushSubscription,
    StaffNotificationProfile,
)


@admin.register(StaffNotificationProfile)
class StaffNotificationProfileAdmin(admin.ModelAdmin):
    form = StaffNotificationProfileForm
    list_display = [
        "display_name",
        "role_title",
        "service_scope",
        "web_push_enabled",
        "push_device_count",
        "kakao_status",
        "reminder_enabled",
        "is_active",
    ]
    list_filter = [
        "is_active",
        "service_scope",
        "web_push_enabled",
        "kakao_enabled",
        "reminder_enabled",
    ]
    search_fields = ["display_name", "role_title", "user__username", "user__email"]
    readonly_fields = [
        "notification_console",
        "push_device_count",
        "kakao_status",
        "last_notification_connected_at",
        "created_at",
        "updated_at",
    ]
    fieldsets = [
        (
            "직원 정보",
            {"fields": ["user", "display_name", "role_title", "service_scope", "is_active"]},
        ),
        (
            "알림 수신 설정",
            {
                "fields": [
                    "consultation_types",
                    "web_push_enabled",
                    "kakao_enabled",
                    "reminder_enabled",
                ]
            },
        ),
        (
            "연결 상태",
            {
                "fields": [
                    "notification_console",
                    "push_device_count",
                    "kakao_status",
                    "last_notification_connected_at",
                ]
            },
        ),
        ("기록", {"classes": ["collapse"], "fields": ["created_at", "updated_at"]}),
    ]

    @admin.display(description="알림 관리 화면")
    def notification_console(self, obj):
        if not obj or not obj.pk:
            return "저장 후 사용할 수 있습니다."
        return format_html(
            '<a class="button" href="{}">기기·카카오 연결 관리</a>',
            reverse("staff_notifications:dashboard"),
        )

    @admin.display(description="등록 기기 수")
    def push_device_count(self, obj):
        return obj.active_push_device_count if obj and obj.pk else 0

    @admin.display(description="카카오 연결", boolean=True)
    def kakao_status(self, obj):
        return obj.kakao_connection_active if obj and obj.pk else False

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("user", "kakao_connection")
        if request.user.is_superuser:
            return queryset
        return queryset.filter(user=request.user)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            fields.extend(["user", "display_name", "role_title", "service_scope", "is_active"])
        return fields

    def has_change_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser:
            return obj.user_id == request.user.id
        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser:
            return obj.user_id == request.user.id
        return super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["device_name", "profile", "browser", "is_active", "last_used_at"]
    list_filter = ["is_active", "browser", "created_at"]
    search_fields = ["device_name", "profile__display_name"]
    readonly_fields = [
        "profile",
        "device_name",
        "browser",
        "is_active",
        "created_at",
        "last_used_at",
        "deactivated_at",
    ]
    exclude = ["endpoint", "p256dh", "auth"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(KakaoConnection)
class KakaoConnectionAdmin(admin.ModelAdmin):
    list_display = [
        "profile",
        "is_active",
        "reconnect_required",
        "connected_at",
        "access_token_expires_at",
        "last_error_code",
    ]
    readonly_fields = [
        "profile",
        "kakao_user_id",
        "connected_at",
        "last_refreshed_at",
        "access_token_expires_at",
        "refresh_token_expires_at",
        "is_active",
        "reconnect_required",
        "last_error_code",
    ]
    exclude = ["access_token_encrypted", "refresh_token_encrypted"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationConfiguration)
class NotificationConfigurationAdmin(admin.ModelAdmin):
    fields = [
        "first_reminder_minutes",
        "second_reminder_minutes",
        "max_reminders",
        "max_delivery_attempts",
        "worker_poll_seconds",
        "updated_at",
    ]
    readonly_fields = ["updated_at"]

    def has_add_permission(self, request):
        return not NotificationConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "consultation",
        "recipient",
        "channel",
        "kind",
        "status",
        "scheduled_at",
        "attempt_count",
    ]
    list_filter = ["status", "channel", "kind", "scheduled_at"]
    search_fields = ["consultation__reference_code", "recipient__display_name", "last_error_code"]
    readonly_fields = [field.name for field in NotificationJob._meta.fields]
    actions = ["retry_failed_jobs"]

    @admin.action(description="선택한 실패 작업을 다시 시도")
    def retry_failed_jobs(self, request, queryset):
        from django.utils import timezone

        queryset.filter(status=NotificationJob.Status.FAILED).update(
            status=NotificationJob.Status.RETRY,
            scheduled_at=timezone.now(),
            attempt_count=0,
            locked_at=None,
            last_error_code="",
            last_error_message="",
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(NotificationDeliveryLog)
class NotificationDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ["attempted_at", "job", "status", "response_code", "error_code"]
    list_filter = ["status", "attempted_at"]
    search_fields = ["job__consultation__reference_code", "error_code"]
    readonly_fields = [field.name for field in NotificationDeliveryLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
