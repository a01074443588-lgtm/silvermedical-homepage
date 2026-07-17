import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


REFERENCE_ALPHABET = string.ascii_uppercase.replace("I", "").replace("O", "") + "23456789"


def make_reference_code():
    date_part = timezone.localdate().strftime("%y%m%d")
    token = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
    return f"SM-{date_part}-{token}"


class Consultation(models.Model):
    class Category(models.TextChoices):
        NURSING_HOME = "nursing_home", "요양원 입소"
        DAY_CARE = "day_care", "주간보호"
        HOME_CARE = "home_care", "방문요양"
        HOME_BATH = "home_bath", "방문목욕"
        SHORT_STAY = "short_stay", "단기보호"
        INTEGRATED = "integrated", "통합재가"
        OTHER = "other", "기타 상담"

    class ContactTime(models.TextChoices):
        MORNING = "morning", "오전 9시~12시"
        AFTERNOON = "afternoon", "오후 1시~5시"
        EVENING = "evening", "오후 5시 이후"
        ANYTIME = "anytime", "시간 관계없음"

    class Status(models.TextChoices):
        NEW = "new", "신규 접수"
        IN_PROGRESS = "in_progress", "상담 중"
        COMPLETED = "completed", "상담 완료"

    reference_code = models.CharField(
        "접수번호",
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
    )
    category = models.CharField("상담 종류", max_length=20, choices=Category.choices)
    guardian_name = models.CharField("보호자 성명", max_length=30)
    phone = models.CharField("연락처", max_length=20)
    preferred_contact_time = models.CharField(
        "연락 희망 시간",
        max_length=20,
        choices=ContactTime.choices,
    )
    message = models.TextField("상담 내용", max_length=2000)
    status = models.CharField(
        "진행 상태",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    staff_note = models.TextField("직원 메모", max_length=3000, blank=True)
    consent_version = models.CharField("동의문 버전", max_length=20, default="2026-07")
    privacy_agreed_at = models.DateTimeField("개인정보 동의 시각")
    created_at = models.DateTimeField("접수 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)
    completed_at = models.DateTimeField("상담 완료 시각", null=True, blank=True)

    class Meta:
        verbose_name = "상담"
        verbose_name_plural = "상담 접수함"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="consult_status_created_idx"),
            models.Index(fields=["category", "-created_at"], name="consult_category_created_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = make_reference_code()
        super().save(*args, **kwargs)

    @property
    def retention_due_at(self):
        if not self.completed_at:
            return None
        return self.completed_at + timedelta(days=settings.CONSULTATION_RETENTION_DAYS)

    def __str__(self):
        return f"{self.reference_code} - {self.get_category_display()}"
