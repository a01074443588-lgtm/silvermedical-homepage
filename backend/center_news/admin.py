from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Post, PostImage


class PostImageInline(admin.StackedInline):
    model = PostImage
    extra = 3
    fields = ["image", "image_preview", "image_alt", "caption", "sort_order"]
    readonly_fields = ["image_preview"]

    @admin.display(description="현재 사진")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "새 사진을 선택해 주세요."
        return format_html(
            '<img src="{}" alt="" style="width:240px;max-height:180px;object-fit:contain;border-radius:6px">',
            obj.image.url,
        )


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
    inlines = [PostImageInline]
    save_on_top = True
    change_form_template = "admin/center_news/post/change_form.html"
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

    class Media:
        css = {"all": ("center_news/admin-editor.css",)}
        js = ("center_news/admin-editor.js",)

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="center_news_post_preview",
            )
        ]
        return custom_urls + super().get_urls()

    def view_on_site(self, obj):
        return reverse("admin:center_news_post_preview", args=[obj.pk])

    def preview_view(self, request, object_id):
        post = get_object_or_404(Post.objects.prefetch_related("gallery_images"), pk=object_id)
        if not self.has_view_permission(request, post):
            raise PermissionDenied

        response = render(
            request,
            "center_news/detail.html",
            {
                "post": post,
                "related_posts": [],
                "previous_post": None,
                "next_post": None,
                "selected_category": "",
                "page_number": "1",
                "list_url": reverse("center_news:list"),
                "is_preview": True,
                "admin_change_url": reverse("admin:center_news_post_change", args=[post.pk]),
            },
        )
        response["Cache-Control"] = "no-store, max-age=0"
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

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

    def response_change(self, request, obj):
        if "_preview" in request.POST:
            self.message_user(request, "저장했습니다. 완성 화면 미리보기를 표시합니다.", messages.SUCCESS)
            return HttpResponseRedirect(reverse("admin:center_news_post_preview", args=[obj.pk]))
        return super().response_change(request, obj)

    @admin.action(description="선택한 글을 지금 공개")
    def publish_selected(self, request, queryset):
        count = 0
        for post in queryset:
            if not post.published_at:
                post.published_at = timezone.now()
            post.status = Post.Status.PUBLISHED
            post.updated_by = request.user
            post.save(update_fields=["status", "published_at", "updated_by", "updated_at"])
            self.log_change(request, post, "목록에서 선택하여 공개 상태로 변경했습니다.")
            count += 1
        self.message_user(request, f"{count}개 게시글을 공개했습니다.", messages.SUCCESS)

    @admin.action(description="선택한 글을 작성 중으로 변경")
    def move_to_draft(self, request, queryset):
        count = 0
        for post in queryset:
            post.status = Post.Status.DRAFT
            post.updated_by = request.user
            post.save(update_fields=["status", "updated_by", "updated_at"])
            self.log_change(request, post, "목록에서 선택하여 작성 중 상태로 변경했습니다.")
            count += 1
        self.message_user(request, f"{count}개 게시글을 작성 중으로 변경했습니다.", messages.SUCCESS)
