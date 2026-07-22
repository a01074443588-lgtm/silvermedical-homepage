import re
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from bs4 import BeautifulSoup, Comment
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageOps


YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
RICH_TEXT_CLASS_PATTERN = re.compile(
    r"^ql-(?:align-(?:center|right|justify)|indent-[1-8]|size-(?:small|large|huge)|font-(?:serif|monospace))$"
)
RICH_TEXT_ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "em",
    "h2",
    "h3",
    "h4",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "s",
    "span",
    "strong",
    "u",
    "ul",
}
RICH_TEXT_DROP_TAGS = {"embed", "form", "iframe", "input", "object", "script", "style"}


def validate_image_size(upload):
    if upload.size > 8 * 1024 * 1024:
        raise ValidationError("사진은 8MB 이하 파일을 사용해 주세요.")


def post_image_path(instance, filename):
    now = timezone.localtime()
    return f"posts/{now:%Y/%m}/{uuid4().hex}{Path(filename).suffix.lower()}"


def post_gallery_image_path(instance, filename):
    now = timezone.localtime()
    return f"posts/{now:%Y/%m}/gallery/{uuid4().hex}{Path(filename).suffix.lower()}"


def optimize_uploaded_image(upload, max_size=(1600, 1600)):
    upload.open()
    with Image.open(upload) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="WEBP", quality=82, method=6)
    return ContentFile(output.getvalue()), f"{Path(upload.name).stem}.webp"


def _safe_link(value):
    parsed = urlparse((value or "").strip())
    if parsed.scheme and parsed.scheme not in {"http", "https", "mailto", "tel"}:
        return ""
    if not parsed.scheme and not (parsed.path.startswith("/") or parsed.path.startswith("#")):
        return ""
    return value.strip()


def _safe_news_image_src(value):
    parsed = urlparse((value or "").strip())
    if parsed.scheme:
        if parsed.scheme != "https" or parsed.hostname not in {
            "silvermedical.kr",
            "www.silvermedical.kr",
            "staff.silvermedical.kr",
        }:
            return ""
        path = parsed.path
    else:
        path = parsed.path
    if not path.startswith("/news-media/") or ".." in Path(path).parts:
        return ""
    return path


def sanitize_rich_text(value):
    """Keep the editor's small formatting subset and local news images only."""
    soup = BeautifulSoup(value or "", "html.parser")
    for comment in soup.find_all(string=lambda node: isinstance(node, Comment)):
        comment.extract()

    for tag in list(soup.find_all(True)):
        if tag.name in RICH_TEXT_DROP_TAGS:
            tag.decompose()
            continue
        if tag.name not in RICH_TEXT_ALLOWED_TAGS:
            tag.unwrap()
            continue

        cleaned_attributes = {}
        allowed_classes = [
            item for item in tag.get("class", []) if RICH_TEXT_CLASS_PATTERN.fullmatch(item)
        ]
        if allowed_classes:
            cleaned_attributes["class"] = allowed_classes

        if tag.name == "a":
            href = _safe_link(tag.get("href", ""))
            if href:
                cleaned_attributes["href"] = href
                cleaned_attributes["rel"] = "noopener noreferrer"
                if href.startswith(("http://", "https://")):
                    cleaned_attributes["target"] = "_blank"
            else:
                tag.unwrap()
                continue
        elif tag.name == "img":
            src = _safe_news_image_src(tag.get("src", ""))
            if not src:
                tag.decompose()
                continue
            cleaned_attributes["src"] = src
            cleaned_attributes["alt"] = (tag.get("alt") or "센터소식 사진").strip()[:160]
            cleaned_attributes["loading"] = "lazy"
        elif tag.name == "li" and tag.get("data-list") in {
            "bullet",
            "checked",
            "ordered",
            "unchecked",
        }:
            cleaned_attributes["data-list"] = tag["data-list"]

        tag.attrs = cleaned_attributes

    return "".join(str(node) for node in soup.contents).strip()


def extract_youtube_id(url):
    if not url:
        return ""

    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().split(":", 1)[0]
    video_id = ""

    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/", 1)[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"}:
                video_id = parts[1]

    return video_id if YOUTUBE_ID_PATTERN.fullmatch(video_id) else ""


class PublishedPostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            status=Post.Status.PUBLISHED,
            published_at__isnull=False,
            published_at__lte=timezone.now(),
        )


class Post(models.Model):
    class Category(models.TextChoices):
        NOTICE = "notice", "공지사항"
        STORY = "story", "센터 이야기"
        VIDEO = "video", "영상 소식"

    class Status(models.TextChoices):
        DRAFT = "draft", "작성 중"
        PUBLISHED = "published", "공개"

    class BodyFormat(models.TextChoices):
        PLAIN = "plain", "일반 본문"
        RICH = "rich", "완성 화면 편집"

    category = models.CharField("분류", max_length=20, choices=Category.choices)
    title = models.CharField("제목", max_length=120)
    slug = models.SlugField("게시물 주소", max_length=150, unique=True, allow_unicode=True, blank=True)
    summary = models.CharField(
        "목록용 짧은 설명",
        max_length=220,
        help_text="목록과 검색 결과에 표시할 내용을 2~3문장 이내로 작성해 주세요.",
    )
    body = models.TextField(
        "본문",
        blank=True,
        help_text="완성 화면형 편집기에서 글과 사진을 원하는 순서로 배치합니다.",
    )
    body_format = models.CharField(
        "본문 형식",
        max_length=10,
        choices=BodyFormat.choices,
        default=BodyFormat.PLAIN,
        editable=False,
    )
    cover_image = models.ImageField(
        "대표 사진",
        upload_to=post_image_path,
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_image_size,
        ],
        help_text="JPG, PNG, WebP 형식의 8MB 이하 사진을 사용해 주세요. 자동으로 화면용 크기로 줄어듭니다.",
    )
    image_alt = models.CharField(
        "사진 설명",
        max_length=160,
        blank=True,
        help_text="사진을 보지 못하는 이용자도 내용을 이해할 수 있도록 간단히 설명해 주세요.",
    )
    youtube_url = models.URLField(
        "유튜브 주소",
        blank=True,
        help_text="youtube.com 또는 youtu.be 영상 주소를 입력하면 홈페이지에서 바로 재생됩니다.",
    )
    naver_blog_url = models.URLField(
        "네이버 블로그 원문 주소",
        blank=True,
        help_text="관련 블로그 글이 있을 때만 입력해 주세요. 새 창으로 연결됩니다.",
    )
    is_pinned = models.BooleanField("목록 상단 고정", default=False)
    status = models.CharField("공개 상태", max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(
        "공개 시각",
        blank=True,
        null=True,
        help_text="미래 시각을 선택하면 해당 시각부터 자동으로 공개됩니다.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="작성자",
        related_name="created_center_posts",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="마지막 수정자",
        related_name="updated_center_posts",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField("작성 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    objects = PublishedPostQuerySet.as_manager()

    class Meta:
        verbose_name = "센터소식 게시글"
        verbose_name_plural = "센터소식 게시글"
        ordering = ["-is_pinned", "-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.body_format == self.BodyFormat.RICH:
            if len(self.body or "") > 1_000_000:
                raise ValidationError({"body": "본문이 너무 큽니다. 사진은 파일로 추가해 주세요."})
            self.body = sanitize_rich_text(self.body)
        if self.cover_image and not self.image_alt.strip():
            raise ValidationError({"image_alt": "대표 사진을 사용하면 사진 설명도 입력해 주세요."})
        if self.youtube_url and not extract_youtube_id(self.youtube_url):
            raise ValidationError({"youtube_url": "재생할 수 있는 유튜브 영상 주소를 입력해 주세요."})
        if self.naver_blog_url:
            host = urlparse(self.naver_blog_url).netloc.lower()
            if host not in {"blog.naver.com", "m.blog.naver.com"}:
                raise ValidationError({"naver_blog_url": "네이버 블로그 글 주소를 입력해 주세요."})
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

    def _build_unique_slug(self):
        base = slugify(self.title, allow_unicode=True)[:120] or f"post-{uuid4().hex[:8]}"
        candidate = base
        number = 2
        queryset = type(self).objects.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            suffix = f"-{number}"
            candidate = f"{base[:150 - len(suffix)]}{suffix}"
            number += 1
        return candidate

    def _optimize_cover_image(self):
        if not self.cover_image or getattr(self.cover_image, "_committed", True):
            return
        content, filename = optimize_uploaded_image(self.cover_image)
        self.cover_image.save(filename, content, save=False)

    def save(self, *args, **kwargs):
        previous_image = ""
        if self.pk:
            previous_image = (
                type(self).objects.filter(pk=self.pk).values_list("cover_image", flat=True).first()
                or ""
            )
        if not self.slug:
            self.slug = self._build_unique_slug()
        self.full_clean()
        self._optimize_cover_image()
        super().save(*args, **kwargs)
        if previous_image and previous_image != self.cover_image.name:
            self.cover_image.storage.delete(previous_image)

    def delete(self, *args, **kwargs):
        storage = self.cover_image.storage if self.cover_image else None
        image_name = self.cover_image.name if self.cover_image else ""
        result = super().delete(*args, **kwargs)
        if storage and image_name:
            storage.delete(image_name)
        return result

    def get_absolute_url(self):
        return reverse("center_news:detail", args=[self.slug])

    @property
    def youtube_id(self):
        return extract_youtube_id(self.youtube_url)

    @property
    def youtube_embed_url(self):
        if not self.youtube_id:
            return ""
        return f"https://www.youtube-nocookie.com/embed/{self.youtube_id}"

    @property
    def is_public_now(self):
        return bool(
            self.status == self.Status.PUBLISHED
            and self.published_at
            and self.published_at <= timezone.now()
        )


class PostImage(models.Model):
    post = models.ForeignKey(
        Post,
        verbose_name="게시글",
        related_name="gallery_images",
        on_delete=models.CASCADE,
    )
    image = models.ImageField(
        "추가 사진",
        upload_to=post_gallery_image_path,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_image_size,
        ],
        help_text="JPG, PNG, WebP 형식의 8MB 이하 사진을 사용해 주세요.",
    )
    image_alt = models.CharField(
        "사진 설명",
        max_length=160,
        help_text="사진을 보지 못하는 이용자도 이해할 수 있도록 내용을 설명해 주세요.",
    )
    caption = models.CharField(
        "화면에 표시할 설명",
        max_length=200,
        blank=True,
    )
    sort_order = models.PositiveSmallIntegerField(
        "표시 순서",
        default=0,
        db_index=True,
        help_text="작은 숫자부터 먼저 표시됩니다.",
    )
    source_url = models.URLField("원본 사진 주소", max_length=1000, blank=True, editable=False)
    created_at = models.DateTimeField("등록 시각", auto_now_add=True)

    class Meta:
        verbose_name = "게시글 추가 사진"
        verbose_name_plural = "게시글 추가 사진"
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return f"{self.post.title} - 사진 {self.sort_order}"

    def clean(self):
        super().clean()
        if self.image and not (self.image_alt or "").strip():
            raise ValidationError({"image_alt": "추가 사진의 설명을 입력해 주세요."})

    def save(self, *args, **kwargs):
        previous_image = ""
        if self.pk:
            previous_image = (
                type(self).objects.filter(pk=self.pk).values_list("image", flat=True).first()
                or ""
            )
        if self.image and not getattr(self.image, "_committed", True):
            content, filename = optimize_uploaded_image(self.image)
            self.image.save(filename, content, save=False)
        self.full_clean()
        super().save(*args, **kwargs)
        if previous_image and previous_image != self.image.name:
            self.image.storage.delete(previous_image)


@receiver(post_delete, sender=PostImage)
def delete_post_image_file(sender, instance, **kwargs):
    if instance.image and instance.image.name:
        instance.image.storage.delete(instance.image.name)
