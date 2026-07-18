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
        ACKNOWLEDGED = "acknowledged", "접수 확인"
        ASSIGNED = "assigned", "담당자 배정"
        IN_PROGRESS = "in_progress", "연락 중"
        COMPLETED = "completed", "상담 완료"
        WAITING = "waiting", "입소 대기"
        CLOSED = "closed", "종결"

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
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_consultations",
        verbose_name="담당자",
        null=True,
        blank=True,
    )
    first_viewed_at = models.DateTimeField("최초 확인 시각", null=True, blank=True)
    first_viewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="first_viewed_consultations",
        verbose_name="최초 확인자",
        null=True,
        blank=True,
    )
    consent_version = models.CharField("동의문 버전", max_length=20, default="2026-07")
    privacy_agreed_at = models.DateTimeField("개인정보 동의 시각")
    created_at = models.DateTimeField("접수 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)
    completed_at = models.DateTimeField("상담 완료 시각", null=True, blank=True)
    contact_completed_at = models.DateTimeField("연락 완료 시각", null=True, blank=True)
    closed_at = models.DateTimeField("종결 시각", null=True, blank=True)

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


class ConsultationAssignment(models.Model):
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="assignment_history",
        verbose_name="상담",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="consultation_assignment_history",
        verbose_name="담당자",
        null=True,
        blank=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="consultation_assignments_made",
        verbose_name="지정자",
        null=True,
        blank=True,
    )
    note = models.CharField("지정 메모", max_length=200, blank=True)
    created_at = models.DateTimeField("지정 시각", auto_now_add=True)

    class Meta:
        verbose_name = "상담 담당자 지정"
        verbose_name_plural = "상담 담당자 지정 이력"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.consultation.reference_code} - {self.assigned_to or '미지정'}"


class ConsultationStatusHistory(models.Model):
    class Event(models.TextChoices):
        VIEWED = "viewed", "상담 열람"
        ACKNOWLEDGED = "acknowledged", "접수 확인"
        ASSIGNED = "assigned", "담당자 지정"
        STATUS_CHANGED = "status_changed", "상태 변경"
        NOTE_UPDATED = "note_updated", "상담 메모 변경"
        CONTACT_COMPLETED = "contact_completed", "연락 완료"
        CLOSED = "closed", "상담 종결"

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name="상담",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="consultation_status_events",
        verbose_name="처리자",
        null=True,
        blank=True,
    )
    event = models.CharField("처리 내용", max_length=30, choices=Event.choices)
    from_status = models.CharField("변경 전 상태", max_length=20, blank=True)
    to_status = models.CharField("변경 후 상태", max_length=20, blank=True)
    description = models.CharField("기록 요약", max_length=200, blank=True)
    created_at = models.DateTimeField("처리 시각", auto_now_add=True)

    class Meta:
        verbose_name = "상담 처리 이력"
        verbose_name_plural = "상담 처리 이력"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["consultation", "-created_at"], name="consult_history_created_idx")]

    def __str__(self):
        return f"{self.consultation.reference_code} - {self.get_event_display()}"
