from django.contrib import admin
from django.utils import timezone

from .models import Consultation


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = [
        "reference_code",
        "category",
        "guardian_name",
        "phone",
        "preferred_contact_time",
        "status",
        "created_at",
    ]
    list_filter = ["status", "category", "preferred_contact_time", "created_at"]
    search_fields = ["reference_code", "guardian_name", "phone", "message"]
    readonly_fields = [
        "reference_code",
        "privacy_agreed_at",
        "consent_version",
        "created_at",
        "updated_at",
        "completed_at",
        "retention_due_display",
    ]
    fieldsets = [
        (
            "상담 접수",
            {
                "fields": [
                    "reference_code",
                    "category",
                    "guardian_name",
                    "phone",
                    "preferred_contact_time",
                    "message",
                ]
            },
        ),
        ("처리 기록", {"fields": ["status", "staff_note", "completed_at", "retention_due_display"]}),
        (
            "개인정보 동의",
            {
                "classes": ["collapse"],
                "fields": ["privacy_agreed_at", "consent_version", "created_at", "updated_at"],
            },
        ),
    ]
    actions = ["mark_in_progress", "mark_completed"]
    date_hierarchy = "created_at"
    list_per_page = 30
    ordering = ["-created_at"]

    @admin.display(description="파기 검토일")
    def retention_due_display(self, obj):
        return obj.retention_due_at or "상담 완료 후 계산"

    @admin.action(description="선택한 상담을 '상담 중'으로 변경")
    def mark_in_progress(self, request, queryset):
        queryset.update(
            status=Consultation.Status.IN_PROGRESS,
            completed_at=None,
            updated_at=timezone.now(),
        )

    @admin.action(description="선택한 상담을 '상담 완료'로 변경")
    def mark_completed(self, request, queryset):
        now = timezone.now()
        queryset.update(
            status=Consultation.Status.COMPLETED,
            completed_at=now,
            updated_at=now,
        )

    def save_model(self, request, obj, form, change):
        if obj.status == Consultation.Status.COMPLETED and not obj.completed_at:
            obj.completed_at = timezone.now()
        elif obj.status != Consultation.Status.COMPLETED:
            obj.completed_at = None
        super().save_model(request, obj, form, change)
