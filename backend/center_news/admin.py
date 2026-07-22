from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "publication_status", "is_pinned", "published_at", "updated_at"]
    list_filter = ["category", "status", "is_pinned"]
    search_fields = ["title", "summary", "body"]
    ordering = ["-is_pinned", "-published_at", "-created_at"]
    date_hierarchy = "published_at"
    list_editable = ["is_pinned"]
    readonly_fields = ["cover_preview", "created_by", "updated_by", "created_at", "updated_at"]
    actions = ["publish_selected", "move_to_draft"]
    save_on_top = True
    view_on_site = True
    fieldsets = [
        (
            "게시글 내용",
            {
                "fields": ["category", "title", "summary", "body"],
                "description": "방문자에게 공개할 기관 소식과 안내 내용을 작성합니다.",
            },
        ),
        (
            "사진·외부 채널",
            {
                "fields": ["cover_image", "cover_preview", "image_alt", "youtube_url", "naver_blog_url"],
                "description": "대표 사진은 공개 가능한 자료만 사용하고, 유튜브와 블로그 주소는 필요한 경우에만 입력합니다.",
            },
        ),
        (
            "공개 설정",
            {
                "fields": [("status", "published_at"), "is_pinned"],
                "description": "작성 중인 글은 홈페이지에 보이지 않습니다. 공개 시각을 미래로 지정하면 예약 게시됩니다.",
            },
        ),
        (
            "기록",
            {
                "classes": ["collapse"],
                "fields": [("created_by", "updated_by"), ("created_at", "updated_at")],
            },
        ),
    ]

    @admin.display(description="공개 상태", boolean=True)
    def publication_status(self, obj):
        return obj.is_public_now

    @admin.display(description="현재 대표 사진")
    def cover_preview(self, obj):
        if not obj or not obj.cover_image:
            return "등록된 사진이 없습니다."
        return format_html(
            '<img src="{}" alt="" style="width:240px;max-height:160px;object-fit:cover;border-radius:6px">',
            obj.cover_image.url,
        )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="선택한 글을 지금 공개")
    def publish_selected(self, request, queryset):
        count = queryset.update(status=Post.Status.PUBLISHED, published_at=timezone.now())
        self.message_user(request, f"{count}개 게시글을 공개했습니다.", messages.SUCCESS)

    @admin.action(description="선택한 글을 작성 중으로 변경")
    def move_to_draft(self, request, queryset):
        count = queryset.update(status=Post.Status.DRAFT)
        self.message_user(request, f"{count}개 게시글을 작성 중으로 변경했습니다.", messages.SUCCESS)
