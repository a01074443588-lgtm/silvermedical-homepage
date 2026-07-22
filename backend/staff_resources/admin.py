from django.contrib import admin, messages
from django.utils import timezone

from .models import StaffResource


@admin.register(StaffResource)
class StaffResourceAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "is_published", "published_at", "updated_at"]
    list_filter = ["category", "is_published"]
    search_fields = ["title", "summary", "body"]
    ordering = ["-published_at", "-created_at"]
    readonly_fields = ["created_by", "updated_by", "created_at", "updated_at"]
    actions = ["publish_selected", "hide_selected"]
    save_on_top = True
    fieldsets = [
        (
            "자료 내용",
            {"fields": ["category", "title", "summary", "body"]},
        ),
        (
            "파일·링크",
            {
                "fields": ["attachment", "external_url"],
                "description": "개인정보나 수급자 자료는 외부 링크에 올리지 말고 내부 보안 기준을 확인해 주세요.",
            },
        ),
        (
            "직원 공개 설정",
            {"fields": [("is_published", "published_at")]},
        ),
        (
            "기록",
            {
                "classes": ["collapse"],
                "fields": [("created_by", "updated_by"), ("created_at", "updated_at")],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="선택한 자료를 직원에게 공개")
    def publish_selected(self, request, queryset):
        queryset.filter(published_at__isnull=True).update(published_at=timezone.now())
        count = queryset.update(is_published=True)
        self.message_user(request, f"{count}개 자료를 공개했습니다.", messages.SUCCESS)

    @admin.action(description="선택한 자료를 비공개")
    def hide_selected(self, request, queryset):
        count = queryset.update(is_published=False)
        self.message_user(request, f"{count}개 자료를 비공개로 변경했습니다.", messages.SUCCESS)
