from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Max
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Post, PostImage, sanitize_rich_text


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    max_editor_images = 150
    list_display = ["title", "category", "publication_status", "is_pinned", "published_at", "updated_at"]
    list_filter = ["category", "status", "is_pinned"]
    search_fields = ["title", "summary", "body"]
    ordering = ["-is_pinned", "-published_at", "-created_at"]
    date_hierarchy = "published_at"
    list_editable = ["is_pinned"]
    readonly_fields = ["cover_preview", "created_by", "updated_by", "created_at", "updated_at"]
    actions = ["publish_selected", "move_to_draft"]
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
        css = {
            "all": (
                "center_news/vendor/quill.snow.css",
                "center_news/admin-editor.css",
            )
        }
        js = (
            "center_news/vendor/quill.js",
            "center_news/admin-editor.js",
        )

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="center_news_post_preview",
            ),
            path(
                "<path:object_id>/editor-image-upload/",
                self.admin_site.admin_view(self.editor_image_upload),
                name="center_news_post_editor_image_upload",
            ),
            path(
                "<path:object_id>/editor-image-delete/",
                self.admin_site.admin_view(self.editor_image_delete),
                name="center_news_post_editor_image_delete",
            ),
        ]
        return custom_urls + super().get_urls()

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        assets = []
        if obj:
            if obj.cover_image:
                assets.append(
                    {
                        "id": None,
                        "url": obj.cover_image.url,
                        "alt": obj.image_alt or "대표 사진",
                        "is_cover": True,
                    }
                )
            assets.extend(
                {
                    "id": image.pk,
                    "url": image.image.url,
                    "alt": image.image_alt,
                    "is_cover": False,
                }
                for image in obj.gallery_images.all()
                if image.image
            )
            context["editor_upload_url"] = reverse(
                "admin:center_news_post_editor_image_upload", args=[obj.pk]
            )
            context["editor_delete_url"] = reverse(
                "admin:center_news_post_editor_image_delete", args=[obj.pk]
            )
        context["editor_assets"] = assets
        context["editor_image_limit"] = self.max_editor_images
        return super().render_change_form(request, context, add, change, form_url, obj)

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

    def editor_image_upload(self, request, object_id):
        if request.method != "POST":
            return JsonResponse({"error": "사진 업로드는 POST 요청만 허용됩니다."}, status=405)
        post = get_object_or_404(Post, pk=object_id)
        if not self.has_change_permission(request, post):
            raise PermissionDenied
        if post.gallery_images.count() >= self.max_editor_images:
            return JsonResponse(
                {"error": f"게시글 한 개에는 사진을 최대 {self.max_editor_images}장까지 보관할 수 있습니다."},
                status=400,
            )
        upload = request.FILES.get("image")
        if not upload:
            return JsonResponse({"error": "추가할 사진을 선택해 주세요."}, status=400)
        alt = (request.POST.get("alt") or upload.name.rsplit(".", 1)[0] or "센터소식 사진")[:160]
        next_order = (post.gallery_images.aggregate(value=Max("sort_order"))["value"] or 0) + 10
        try:
            image = PostImage.objects.create(
                post=post,
                image=upload,
                image_alt=alt,
                sort_order=next_order,
            )
        except ValidationError as exc:
            return JsonResponse({"error": " ".join(exc.messages)}, status=400)
        self.log_change(request, post, f"편집기에서 사진 1장을 추가했습니다: {image.image_alt}")
        return JsonResponse(
            {
                "id": image.pk,
                "url": image.image.url,
                "alt": image.image_alt,
                "count": post.gallery_images.count(),
            }
        )

    def editor_image_delete(self, request, object_id):
        if request.method != "POST":
            return JsonResponse({"error": "사진 삭제는 POST 요청만 허용됩니다."}, status=405)
        post = get_object_or_404(Post, pk=object_id)
        if not self.has_change_permission(request, post):
            raise PermissionDenied
        image = get_object_or_404(PostImage, post=post, pk=request.POST.get("image_id"))
        image_url = image.image.url
        image_alt = image.image_alt

        if post.body_format == Post.BodyFormat.RICH and post.body:
            target_path = urlparse(image_url).path
            soup = BeautifulSoup(post.body, "html.parser")
            for image_node in list(soup.find_all("img")):
                if urlparse(image_node.get("src", "")).path != target_path:
                    continue
                parent = image_node.parent
                image_node.decompose()
                if (
                    parent
                    and parent.name == "p"
                    and not parent.get_text(strip=True)
                    and not parent.find("img")
                ):
                    parent.decompose()
            post.body = sanitize_rich_text("".join(str(node) for node in soup.contents))
            post.updated_by = request.user
            post.save(update_fields=["body", "updated_by", "updated_at"])

        image.delete()
        self.log_change(request, post, f"편집기 사진을 삭제했습니다: {image_alt}")
        return JsonResponse({"deleted": True, "url": image_url})

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
        obj.body_format = Post.BodyFormat.RICH
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
