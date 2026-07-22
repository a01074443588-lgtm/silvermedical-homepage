from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


ALLOWED_RESOURCE_EXTENSIONS = [
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "hwp",
    "hwpx",
    "jpg",
    "jpeg",
    "png",
    "webp",
    "zip",
]


def validate_resource_size(upload):
    if upload.size > 8 * 1024 * 1024:
        raise ValidationError("첨부파일은 8MB 이하 파일을 사용해 주세요.")


def resource_file_path(instance, filename):
    now = timezone.localtime()
    suffix = Path(filename).suffix.lower()
    return f"staff-resources/{now:%Y/%m}/{uuid4().hex}{suffix}"


class StaffResource(models.Model):
    class Category(models.TextChoices):
        GUIDE = "guide", "업무 안내"
        TRAINING = "training", "직원 교육"
        FORM = "form", "서식·자료"
        VIDEO = "video", "영상 자료"

    category = models.CharField("분류", max_length=20, choices=Category.choices)
    title = models.CharField("자료명", max_length=150)
    slug = models.SlugField("자료 주소", max_length=180, unique=True, allow_unicode=True, blank=True)
    summary = models.CharField("짧은 설명", max_length=240)
    body = models.TextField("상세 안내", blank=True)
    attachment = models.FileField(
        "첨부파일",
        upload_to=resource_file_path,
        blank=True,
        validators=[
            FileExtensionValidator(ALLOWED_RESOURCE_EXTENSIONS),
            validate_resource_size,
        ],
        help_text="PDF, 한글, Word, Excel, PowerPoint, 이미지 또는 ZIP 파일을 8MB 이하로 등록해 주세요.",
    )
    external_url = models.URLField(
        "관련 링크",
        blank=True,
        help_text="내부 자료에 필요한 외부 링크가 있을 때만 입력해 주세요. 민감한 자료는 외부 서비스에 올리지 마세요.",
    )
    is_published = models.BooleanField("직원에게 공개", default=False)
    published_at = models.DateTimeField("공개 시각", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="등록자",
        related_name="created_staff_resources",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="마지막 수정자",
        related_name="updated_staff_resources",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField("등록 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    class Meta:
        verbose_name = "직원 자료"
        verbose_name_plural = "직원 자료"
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if not any([self.body.strip(), self.attachment, self.external_url.strip()]):
            raise ValidationError("상세 안내, 첨부파일 또는 관련 링크 중 하나 이상을 입력해 주세요.")
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()

    def _build_unique_slug(self):
        base = slugify(self.title, allow_unicode=True)[:150] or f"resource-{uuid4().hex[:8]}"
        candidate = base
        number = 2
        queryset = type(self).objects.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            suffix = f"-{number}"
            candidate = f"{base[:180 - len(suffix)]}{suffix}"
            number += 1
        return candidate

    def save(self, *args, **kwargs):
        previous_file = ""
        if self.pk:
            previous_file = (
                type(self).objects.filter(pk=self.pk).values_list("attachment", flat=True).first()
                or ""
            )
        if not self.slug:
            self.slug = self._build_unique_slug()
        self.full_clean()
        super().save(*args, **kwargs)
        if previous_file and previous_file != self.attachment.name:
            self.attachment.storage.delete(previous_file)

    def delete(self, *args, **kwargs):
        storage = self.attachment.storage if self.attachment else None
        file_name = self.attachment.name if self.attachment else ""
        result = super().delete(*args, **kwargs)
        if storage and file_name:
            storage.delete(file_name)
        return result

    def get_absolute_url(self):
        return reverse("staff_resources:detail", args=[self.slug])

    @property
    def attachment_name(self):
        return Path(self.attachment.name).name if self.attachment else ""
