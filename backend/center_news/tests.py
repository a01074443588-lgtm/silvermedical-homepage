from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Post, PostImage, extract_youtube_id, sanitize_rich_text
from .naver_import import (
    NaverBlogPost,
    build_summary,
    parse_post_list,
    render_imported_body,
    rewrite_title,
)
from .templatetags.news_content import render_news_body


class CenterNewsModelTests(TestCase):
    def test_youtube_id_supports_common_urls(self):
        self.assertEqual(extract_youtube_id("https://youtu.be/abcDEF_1234"), "abcDEF_1234")
        self.assertEqual(extract_youtube_id("https://www.youtube.com/watch?v=abcDEF_1234"), "abcDEF_1234")
        self.assertEqual(extract_youtube_id("https://www.youtube.com/shorts/abcDEF_1234"), "abcDEF_1234")
        self.assertEqual(extract_youtube_id("https://example.com/watch?v=abcDEF_1234"), "")

    def test_published_post_without_date_gets_current_time(self):
        post = Post(
            category=Post.Category.NOTICE,
            title="이용 안내",
            summary="센터 이용에 필요한 내용을 안내합니다.",
            status=Post.Status.PUBLISHED,
        )
        post.save()
        self.assertIsNotNone(post.published_at)
        self.assertTrue(post.is_public_now)

    def test_cover_image_requires_alt_text(self):
        post = Post(
            category=Post.Category.STORY,
            title="프로그램 이야기",
            summary="프로그램 소식입니다.",
        )
        post.cover_image = SimpleUploadedFile("example.jpg", b"test-image", content_type="image/jpeg")
        with self.assertRaises(ValidationError) as error:
            post.clean()
        self.assertIn("image_alt", error.exception.message_dict)

    def test_cover_image_is_optimized_to_webp(self):
        source = BytesIO()
        Image.new("RGB", (2000, 1200), "#dfead2").save(source, format="JPEG")
        upload = SimpleUploadedFile("program.jpg", source.getvalue(), content_type="image/jpeg")

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            post = Post.objects.create(
                category=Post.Category.STORY,
                title="사진 최적화 확인",
                summary="대표 사진이 화면용 파일로 저장되는지 확인합니다.",
                cover_image=upload,
                image_alt="밝은 프로그램실",
            )
            self.assertTrue(post.cover_image.name.endswith(".webp"))
            with Image.open(post.cover_image.path) as optimized:
                self.assertLessEqual(max(optimized.size), 1600)
                self.assertEqual(optimized.format, "WEBP")
            post.delete()

    def test_gallery_image_is_optimized_to_webp(self):
        source = BytesIO()
        Image.new("RGB", (2100, 1300), "#e9dfc8").save(source, format="JPEG")
        upload = SimpleUploadedFile("activity.jpg", source.getvalue(), content_type="image/jpeg")

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            post = Post.objects.create(
                category=Post.Category.STORY,
                title="여러 사진 확인",
                summary="추가 사진 최적화를 확인합니다.",
            )
            gallery = PostImage.objects.create(
                post=post,
                image=upload,
                image_alt="프로그램에 참여하는 손 모습",
                sort_order=10,
            )
            self.assertTrue(gallery.image.name.endswith(".webp"))
            with Image.open(gallery.image.path) as optimized:
                self.assertLessEqual(max(optimized.size), 1600)
                self.assertEqual(optimized.format, "WEBP")
            post.delete()

    def test_rich_body_sanitizer_keeps_editor_format_and_local_images_only(self):
        cleaned = sanitize_rich_text(
            '<script>alert(1)</script><p class="ql-align-center bad" onclick="alert(2)">안내</p>'
            '<hr><img src="/news-media/posts/example.webp" alt="프로그램 사진">'
            '<img src="https://outside.example/photo.jpg">'
        )
        self.assertNotIn("script", cleaned)
        self.assertNotIn("onclick", cleaned)
        self.assertNotIn("outside.example", cleaned)
        self.assertIn('class="ql-align-center"', cleaned)
        self.assertIn('<hr/>', cleaned)
        self.assertIn('/news-media/posts/example.webp', cleaned)


class NaverImportTests(TestCase):
    sample_html = """
    <div id="post-view224338474405">
      <div class="se-module se-module-text se-title-text">
        청주 요양원 실버메디컬복지센터 삼겹살 파티 - 고기 냄새가 어르신의 저녁을 바꾼 날 🥓
      </div>
      <span class="se_publishDate pcol2">2026. 7. 6. 21:30</span>
      <div class="se-main-container">
        <p class="se-text-paragraph">어르신들과 함께 삼겹살을 구워 먹었습니다.</p>
        <p class="se-text-paragraph">즐거운 저녁 시간이 되었습니다.</p>
        <img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/sample.jpg?type=w773">
        <script class="__se_module_data" data-module-v2='{"inputUrl":"https://youtu.be/abcDEF_1234"}'></script>
      </div>
    </div>
    """

    def test_parses_naver_post_content(self):
        posts = parse_post_list(self.sample_html, "sil3307")
        self.assertEqual(len(posts), 1)
        post = posts[0]
        self.assertEqual(post.log_no, "224338474405")
        self.assertEqual(post.title, "고기 굽는 향기로 더 즐거워진 저녁, 삼겹살 파티")
        self.assertEqual(post.published_at.strftime("%Y-%m-%d %H:%M"), "2026-07-06 21:30")
        self.assertIn("삼겹살을 구워", post.body)
        self.assertEqual(post.image_url, "https://postfiles.pstatic.net/sample.jpg?type=w966")
        self.assertEqual(post.youtube_url, "https://youtu.be/abcDEF_1234")
        self.assertIn("__NAVER_IMAGE_1__", post.body_html)

    def test_rich_import_preserves_component_order(self):
        html = self.sample_html.replace(
            '<p class="se-text-paragraph">어르신들과 함께 삼겹살을 구워 먹었습니다.</p>',
            '<div class="se-component se-image"><img class="se-image-resource" '
            'data-lazy-src="https://postfiles.pstatic.net/first.jpg?type=w773" data-width="800"></div>'
            '<div class="se-component se-text"><p class="se-text-paragraph">첫 문단입니다.</p></div>'
            '<div class="se-component se-horizontalLine"></div>'
            '<div class="se-component se-image"><img class="se-image-resource" '
            'data-lazy-src="https://postfiles.pstatic.net/second.jpg?type=w773" data-width="800"></div>',
        )
        post = parse_post_list(html, "sil3307")[0]
        rendered = render_imported_body(
            post.body_html,
            post.image_urls,
            {
                "https://postfiles.pstatic.net/first.jpg?type=w966": "/news-media/first.webp",
                "https://postfiles.pstatic.net/second.jpg?type=w966": "/news-media/second.webp",
            },
        )
        self.assertLess(rendered.index("first.webp"), rendered.index("첫 문단"))
        self.assertLess(rendered.index("첫 문단"), rendered.index("<hr"))
        self.assertLess(rendered.index("<hr"), rendered.index("second.webp"))

    def test_related_reads_component_is_excluded_from_import(self):
        html = self.sample_html.replace(
            '<p class="se-text-paragraph">즐거운 저녁 시간이 되었습니다.</p>',
            '<div class="se-component se-text"><p class="se-text-paragraph">본문 마지막 문단입니다.</p></div>'
            '<div class="se-component se-text"><p class="se-text-paragraph">같이 읽으면 좋은 글</p>'
            '<p class="se-text-paragraph"><a href="https://blog.naver.com/sil3307/111">추천 글 제목</a></p></div>'
            '<div class="se-component se-text"><p class="se-text-paragraph">함께 읽으면 좋은 글</p>'
            '<p class="se-text-paragraph"><a href="https://blog.naver.com/sil3307/222">다른 추천 글</a></p></div>'
            '<div class="se-component se-text"><p class="se-text-paragraph">센터 연락처 안내</p></div>',
        )
        post = parse_post_list(html, "sil3307")[0]

        self.assertIn("본문 마지막 문단", post.body_html)
        self.assertIn("센터 연락처 안내", post.body_html)
        self.assertNotIn("같이 읽으면 좋은 글", post.body_html)
        self.assertNotIn("추천 글 제목", post.body_html)
        self.assertNotIn("함께 읽으면 좋은 글", post.body_html)
        self.assertNotIn("다른 추천 글", post.body_html)
        self.assertNotIn("같이 읽으면 좋은 글", post.body)
        self.assertNotIn("추천 글 제목", post.body)
        self.assertNotIn("함께 읽으면 좋은 글", post.body)
        self.assertNotIn("다른 추천 글", post.body)

    def test_bold_short_paragraph_becomes_heading(self):
        html = self.sample_html.replace(
            '<p class="se-text-paragraph">즐거운 저녁 시간이 되었습니다.</p>',
            '<p class="se-text-paragraph"><b>1. 함께한 저녁</b></p>',
        )
        post = parse_post_list(html, "sil3307")[0]
        self.assertIn("## 1. 함께한 저녁", post.body)

    def test_image_picker_skips_small_placeholder_for_wider_photo(self):
        html = self.sample_html.replace(
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/sample.jpg?type=w773">',
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/small.jpg?type=w80_blur" data-width="100">'
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/wide.jpg?type=w773" data-width="693">',
        )
        post = parse_post_list(html, "sil3307")[0]
        self.assertEqual(post.image_url, "https://postfiles.pstatic.net/wide.jpg?type=w966")

    def test_image_picker_keeps_first_full_size_article_photo(self):
        html = self.sample_html.replace(
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/sample.jpg?type=w773">',
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/first.jpg?type=w773" data-width="693">'
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/later.jpg?type=w773" data-width="2250">',
        )
        post = parse_post_list(html, "sil3307")[0]
        self.assertEqual(post.image_url, "https://postfiles.pstatic.net/first.jpg?type=w966")

    def test_image_picker_keeps_multiple_article_photos_in_order(self):
        html = self.sample_html.replace(
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/sample.jpg?type=w773">',
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/first.jpg?type=w773" data-width="693">'
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/second.jpg?type=w773" data-width="900">'
            '<img class="se-image-resource" data-lazy-src="https://postfiles.pstatic.net/first.jpg?type=w80_blur" data-width="693">',
        )
        post = parse_post_list(html, "sil3307")[0]
        self.assertEqual(
            post.image_urls,
            (
                "https://postfiles.pstatic.net/first.jpg?type=w966",
                "https://postfiles.pstatic.net/second.jpg?type=w966",
            ),
        )

    def test_import_command_adds_gallery_images_and_history_to_existing_draft(self):
        user = get_user_model().objects.create_superuser(
            "silveradmin", "import@example.com", "long-test-password"
        )
        source_url = "https://blog.naver.com/sil3307/123456789"
        original_date = timezone.now() - timedelta(days=200)
        post = Post.objects.create(
            category=Post.Category.STORY,
            title="기존 임시 글",
            summary="기존 글 내용은 그대로 둡니다.",
            naver_blog_url=source_url,
            status=Post.Status.DRAFT,
            published_at=original_date,
            created_by=user,
            updated_by=user,
        )
        item = NaverBlogPost(
            log_no="123456789",
            title="가져온 제목",
            original_title="가져온 원문 제목",
            published_at=timezone.localtime(original_date).replace(tzinfo=None),
            body="가져온 본문",
            summary="가져온 요약",
            source_url=source_url,
            image_urls=(
                "https://postfiles.pstatic.net/cover.jpg?type=w966",
                "https://postfiles.pstatic.net/second.jpg?type=w966",
                "https://postfiles.pstatic.net/third.jpg?type=w966",
            ),
        )
        image_bytes = BytesIO()
        Image.new("RGB", (800, 600), "#dfead2").save(image_bytes, format="JPEG")

        def fake_download(_self, _session, _url, file_stem):
            return ContentFile(image_bytes.getvalue()), f"{file_stem}.jpg"

        command_path = "center_news.management.commands.import_naver_blog.Command"
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            with patch(f"{command_path}._collect_candidates", return_value=[item]), patch(
                f"{command_path}._download_image", new=fake_download
            ):
                call_command("import_naver_blog", username=user.username)

            post.refresh_from_db()
            self.assertEqual(post.status, Post.Status.DRAFT)
            self.assertEqual(post.title, "기존 임시 글")
            self.assertEqual(post.published_at, original_date)
            self.assertTrue(post.cover_image.name.endswith(".webp"))
            self.assertEqual(post.gallery_images.count(), 3)
            self.assertTrue(
                LogEntry.objects.filter(object_id=str(post.pk), change_message__contains="사진 4장").exists()
            )

    def test_refresh_content_builds_rich_body_with_local_gallery_images(self):
        user = get_user_model().objects.create_superuser(
            "refreshadmin", "refresh@example.com", "long-test-password"
        )
        source_url = "https://blog.naver.com/sil3307/987654321"
        post = Post.objects.create(
            category=Post.Category.STORY,
            title="기존 글",
            summary="기존 요약",
            body="기존 본문",
            naver_blog_url=source_url,
            status=Post.Status.DRAFT,
            published_at=timezone.now() - timedelta(days=20),
        )
        item = NaverBlogPost(
            log_no="987654321",
            title="원문 제목",
            original_title="원문 제목",
            published_at=timezone.localtime(post.published_at).replace(tzinfo=None),
            body="첫 문단",
            summary="원문 요약",
            source_url=source_url,
            body_html='<p>첫 문단</p><p class="ql-align-center"><img src="__NAVER_IMAGE_1__" alt="사진"></p>',
            image_urls=("https://postfiles.pstatic.net/refresh.jpg?type=w966",),
        )
        image_bytes = BytesIO()
        Image.new("RGB", (800, 600), "#dfead2").save(image_bytes, format="JPEG")

        def fake_download(_self, _session, _url, file_stem):
            return ContentFile(image_bytes.getvalue()), f"{file_stem}.jpg"

        command_path = "center_news.management.commands.import_naver_blog.Command"
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            with patch(f"{command_path}._collect_candidates", return_value=[item]), patch(
                f"{command_path}._download_image", new=fake_download
            ):
                call_command(
                    "import_naver_blog",
                    username=user.username,
                    refresh_content=True,
                )
            post.refresh_from_db()
            self.assertEqual(post.body_format, Post.BodyFormat.RICH)
            self.assertIn("첫 문단", post.body)
            self.assertIn("/news-media/", post.body)
            self.assertNotIn("__NAVER_IMAGE", post.body)

    def test_summary_is_limited_to_model_length(self):
        summary = build_summary(["가" * 180, "나" * 180], "대체 제목")
        self.assertLessEqual(len(summary), 220)
        self.assertTrue(summary.endswith("..."))

    def test_fallback_title_rewrite_removes_search_prefix_and_emoji(self):
        title = rewrite_title("999", "청주 요양원 실버메디컬복지센터 따뜻한 봄날 🎶")
        self.assertEqual(title, "따뜻한 봄날")

    def test_news_body_formatter_preserves_structure_and_escapes_html(self):
        rendered = render_news_body("## 소제목\n\n• 첫 항목\n\n<script>alert(1)</script>")
        self.assertIn("<h2>소제목</h2>", rendered)
        self.assertIn("<li>첫 항목</li>", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)


class CenterNewsPublicViewTests(TestCase):
    def setUp(self):
        self.public_post = Post.objects.create(
            category=Post.Category.NOTICE,
            title="공개 공지",
            summary="현재 공개된 공지입니다.",
            status=Post.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(minutes=1),
        )
        self.draft_post = Post.objects.create(
            category=Post.Category.STORY,
            title="작성 중 소식",
            summary="아직 공개되지 않은 소식입니다.",
        )
        self.future_post = Post.objects.create(
            category=Post.Category.VIDEO,
            title="예약 영상",
            summary="나중에 공개될 영상입니다.",
            status=Post.Status.PUBLISHED,
            published_at=timezone.now() + timedelta(days=1),
        )

    def test_list_only_shows_currently_published_posts(self):
        response = self.client.get(reverse("center_news:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.public_post.title)
        self.assertNotContains(response, self.draft_post.title)
        self.assertNotContains(response, self.future_post.title)
        self.assertContains(response, "/news-view.js?v=20260722-editor")

    def test_list_accepts_head_request(self):
        response = self.client.head(reverse("center_news:list"))
        self.assertEqual(response.status_code, 200)

    def test_latest_api_only_returns_currently_published_posts(self):
        response = self.client.get(reverse("center_news:latest"))
        self.assertEqual(response.status_code, 200)
        posts = response.json()["posts"]
        self.assertEqual([item["title"] for item in posts], [self.public_post.title])

    def test_draft_detail_returns_404(self):
        response = self.client.get(self.draft_post.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_detail_has_previous_next_and_return_navigation(self):
        older = Post.objects.create(
            category=Post.Category.NOTICE,
            title="이전 공지",
            summary="이전 공지 내용입니다.",
            status=Post.Status.PUBLISHED,
            published_at=self.public_post.published_at - timedelta(days=1),
        )
        newer = Post.objects.create(
            category=Post.Category.NOTICE,
            title="다음 공지",
            summary="다음 공지 내용입니다.",
            status=Post.Status.PUBLISHED,
            published_at=self.public_post.published_at + timedelta(minutes=1),
        )
        response = self.client.get(
            f"{self.public_post.get_absolute_url()}?category=notice&page=2"
        )
        self.assertContains(response, older.title)
        self.assertContains(response, newer.title)
        self.assertContains(response, "/news/?category=notice&amp;page=2")

    def test_admin_requires_staff_login(self):
        response = self.client.get(reverse("admin:center_news_post_add"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/staff/login/", response.url)

    def test_staff_can_open_post_admin(self):
        user = get_user_model().objects.create_superuser("newsadmin", "news@example.com", "long-test-password")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:center_news_post_add"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_preview_draft_and_open_history(self):
        user = get_user_model().objects.create_superuser(
            "previewadmin", "preview@example.com", "long-test-password"
        )
        self.client.force_login(user)
        preview_url = reverse("admin:center_news_post_preview", args=[self.draft_post.pk])
        preview = self.client.get(preview_url)
        history = self.client.get(
            reverse("admin:center_news_post_history", args=[self.draft_post.pk])
        )
        change = self.client.get(
            reverse("admin:center_news_post_change", args=[self.draft_post.pk])
        )

        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, "관리자 전용 완성 화면 미리보기")
        self.assertIn("no-store", preview["Cache-Control"])
        self.assertEqual(history.status_code, 200)
        self.assertEqual(change.status_code, 200)
        self.assertContains(change, preview_url)
        self.assertContains(change, "본문 사진 보관함")
        self.assertContains(change, "center_news/vendor/quill.")
        self.assertContains(
            change,
            reverse("admin:center_news_post_editor_image_upload", args=[self.draft_post.pk]),
        )

    def test_staff_can_upload_and_delete_editor_image(self):
        user = get_user_model().objects.create_superuser(
            "imageadmin", "image@example.com", "long-test-password"
        )
        self.client.force_login(user)
        source = BytesIO()
        Image.new("RGB", (900, 600), "#dfead2").save(source, format="JPEG")

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            upload = self.client.post(
                reverse(
                    "admin:center_news_post_editor_image_upload",
                    args=[self.draft_post.pk],
                ),
                {
                    "image": SimpleUploadedFile(
                        "activity.jpg",
                        source.getvalue(),
                        content_type="image/jpeg",
                    ),
                    "alt": "프로그램 활동 사진",
                },
            )
            self.assertEqual(upload.status_code, 200)
            payload = upload.json()
            self.assertTrue(payload["url"].endswith(".webp"))
            self.assertEqual(self.draft_post.gallery_images.count(), 1)

            self.draft_post.body_format = Post.BodyFormat.RICH
            self.draft_post.body = (
                f'<p>사진 앞 문단</p><p><img src="{payload["url"]}" alt="프로그램 활동 사진"></p>'
                '<p>사진 뒤 문단</p>'
            )
            self.draft_post.save(update_fields=["body", "body_format"])

            delete = self.client.post(
                reverse(
                    "admin:center_news_post_editor_image_delete",
                    args=[self.draft_post.pk],
                ),
                {"image_id": payload["id"]},
            )
            self.assertEqual(delete.status_code, 200)
            self.assertEqual(self.draft_post.gallery_images.count(), 0)
            self.draft_post.refresh_from_db()
            self.assertNotIn(payload["url"], self.draft_post.body)
            self.assertIn("사진 앞 문단", self.draft_post.body)
            self.assertIn("사진 뒤 문단", self.draft_post.body)

    def test_bulk_publish_preserves_imported_publication_date(self):
        user = get_user_model().objects.create_superuser(
            "publishadmin", "publish@example.com", "long-test-password"
        )
        imported_date = timezone.now() - timedelta(days=300)
        draft = Post.objects.create(
            category=Post.Category.STORY,
            title="날짜가 보존되는 블로그 글",
            summary="네이버 블로그 원문 작성일을 보존합니다.",
            status=Post.Status.DRAFT,
            published_at=imported_date,
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("admin:center_news_post_changelist"),
            {"action": "publish_selected", "_selected_action": [draft.pk]},
        )
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, Post.Status.PUBLISHED)
        self.assertEqual(draft.published_at, imported_date)

    def test_staff_without_content_permission_cannot_open_post_admin(self):
        user = get_user_model().objects.create_user(
            "regularstaff",
            "staff@example.com",
            "long-test-password",
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("admin:center_news_post_add"))
        self.assertEqual(response.status_code, 403)

    def test_content_editor_group_has_post_permissions(self):
        group = Group.objects.get(name="콘텐츠 담당자")
        codenames = set(group.permissions.values_list("codename", flat=True))
        self.assertEqual(
            codenames,
            {
                "add_post",
                "change_post",
                "delete_post",
                "view_post",
                "add_postimage",
                "change_postimage",
                "delete_postimage",
                "view_postimage",
            },
        )

    def test_public_detail_displays_all_gallery_images(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            for index in range(2):
                source = BytesIO()
                Image.new("RGB", (640, 480), "#dfead2").save(source, format="JPEG")
                PostImage.objects.create(
                    post=self.public_post,
                    image=SimpleUploadedFile(
                        f"gallery-{index}.jpg", source.getvalue(), content_type="image/jpeg"
                    ),
                    image_alt=f"현장 사진 {index + 1}",
                    sort_order=index * 10,
                )

            response = self.client.get(self.public_post.get_absolute_url())
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "현장 사진 1")
            self.assertContains(response, "현장 사진 2")

    def test_rich_detail_uses_inline_image_without_separate_gallery(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            source = BytesIO()
            Image.new("RGB", (640, 480), "#dfead2").save(source, format="JPEG")
            image = PostImage.objects.create(
                post=self.public_post,
                image=SimpleUploadedFile("inline.jpg", source.getvalue(), content_type="image/jpeg"),
                image_alt="본문 중간 사진",
            )
            self.public_post.body_format = Post.BodyFormat.RICH
            self.public_post.body = (
                f'<p>사진 앞 문단</p><p class="ql-align-center"><img src="{image.image.url}" '
                'alt="본문 중간 사진"></p><p>사진 뒤 문단</p>'
            )
            self.public_post.save()

            response = self.client.get(self.public_post.get_absolute_url())
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "사진 앞 문단")
            self.assertContains(response, "사진 뒤 문단")
            self.assertContains(response, image.image.url, count=1)
            self.assertNotContains(response, "사진으로 보는 이야기")

    def test_gallery_media_is_public_only_when_parent_post_is_public(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            source = BytesIO()
            Image.new("RGB", (640, 480), "#dfead2").save(source, format="JPEG")
            public_image = PostImage.objects.create(
                post=self.public_post,
                image=SimpleUploadedFile("public.jpg", source.getvalue(), content_type="image/jpeg"),
                image_alt="공개 사진",
            )
            draft_image = PostImage.objects.create(
                post=self.draft_post,
                image=SimpleUploadedFile("draft.jpg", source.getvalue(), content_type="image/jpeg"),
                image_alt="임시 사진",
            )

            public_response = self.client.get(
                reverse("news_media", kwargs={"path": public_image.image.name})
            )
            draft_response = self.client.get(
                reverse("news_media", kwargs={"path": draft_image.image.name})
            )
            self.assertEqual(public_response.status_code, 200)
            self.assertEqual(public_response["Cache-Control"], "public, max-age=604800")
            self.assertEqual(draft_response.status_code, 404)
            public_response.close()
