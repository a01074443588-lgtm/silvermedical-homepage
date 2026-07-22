from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Post, extract_youtube_id
from .naver_import import build_summary, parse_post_list, rewrite_title


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
        self.assertEqual(post.image_url, "https://postfiles.pstatic.net/sample.jpg")
        self.assertEqual(post.youtube_url, "https://youtu.be/abcDEF_1234")

    def test_summary_is_limited_to_model_length(self):
        summary = build_summary(["가" * 180, "나" * 180], "대체 제목")
        self.assertLessEqual(len(summary), 220)
        self.assertTrue(summary.endswith("..."))

    def test_fallback_title_rewrite_removes_search_prefix_and_emoji(self):
        title = rewrite_title("999", "청주 요양원 실버메디컬복지센터 따뜻한 봄날 🎶")
        self.assertEqual(title, "따뜻한 봄날")


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

    def test_admin_requires_staff_login(self):
        response = self.client.get(reverse("admin:center_news_post_add"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/staff/login/", response.url)

    def test_staff_can_open_post_admin(self):
        user = get_user_model().objects.create_superuser("newsadmin", "news@example.com", "long-test-password")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:center_news_post_add"))
        self.assertEqual(response.status_code, 200)

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
            {"add_post", "change_post", "delete_post", "view_post"},
        )
