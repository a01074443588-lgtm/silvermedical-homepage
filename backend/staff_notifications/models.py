from django.conf import settings
from django.db import models
from django.utils import timezone

from consultations.models import Consultation


def default_consultation_types():
    return [choice for choice, _label in Consultation.Category.choices]


class StaffNotificationProfile(models.Model):
    class ServiceScope(models.TextChoices):
        ALL = "all", "전체"
        NURSING_HOME = "nursing_home", "요양원"
        DAY_CARE = "day_care", "주간보호"
        HOME_CARE = "home_care", "방문요양"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_profile",
        verbose_name="로그인 계정",
    )
    display_name = models.CharField("직원 이름", max_length=50)
    role_title = models.CharField("직책", max_length=80, blank=True)
    service_scope = models.CharField(
        "소속 급여종별",
        max_length=20,
        choices=ServiceScope.choices,
        default=ServiceScope.ALL,
    )
    consultation_types = models.JSONField(
        "알림 수신 상담 유형",
        default=default_consultation_types,
    )
    web_push_enabled = models.BooleanField("웹 푸시 사용", default=False)
    kakao_enabled = models.BooleanField("카카오톡 사용", default=False)
    reminder_enabled = models.BooleanField("미확인 재알림 사용", default=False)
    is_active = models.BooleanField("알림 계정 활성", default=True)
    last_notification_connected_at = models.DateTimeField(
        "마지막 알림 연결 시각",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("등록 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    class Meta:
        verbose_name = "직원 알림 설정"
        verbose_name_plural = "직원 알림 관리"
        ordering = ["display_name", "user__username"]

    @property
    def active_push_device_count(self):
        return self.push_subscriptions.filter(is_active=True).count()

    @property
    def kakao_connection_active(self):
        return hasattr(self, "kakao_connection") and self.kakao_connection.is_active

    def accepts_category(self, category):
        selected = self.consultation_types or []
        return category in selected

    def __str__(self):
        title = f" ({self.role_title})" if self.role_title else ""
        return f"{self.display_name}{title}"


class PushSubscription(models.Model):
    profile = models.ForeignKey(
        StaffNotificationProfile,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="직원",
    )
    endpoint = models.TextField("푸시 전송 주소", unique=True)
    p256dh = models.TextField("기기 공개키")
    auth = models.TextField("기기 인증키")
    device_name = models.CharField("기기 이름", max_length=100, blank=True)
    browser = models.CharField("브라우저", max_length=80, blank=True)
    is_active = models.BooleanField("사용", default=True)
    created_at = models.DateTimeField("등록 시각", auto_now_add=True)
    last_used_at = models.DateTimeField("마지막 연결 시각", default=timezone.now)
    deactivated_at = models.DateTimeField("해제 시각", null=True, blank=True)

    class Meta:
        verbose_name = "웹 푸시 기기"
        verbose_name_plural = "웹 푸시 등록 기기"
        ordering = ["-last_used_at"]
        indexes = [models.Index(fields=["profile", "is_active"], name="push_profile_active_idx")]

    def deactivate(self):
        if self.is_active:
            self.is_active = False
            self.deactivated_at = timezone.now()
            self.save(update_fields=["is_active", "deactivated_at"])

    def __str__(self):
        return self.device_name or self.browser or f"푸시 기기 {self.pk}"


class KakaoConnection(models.Model):
    profile = models.OneToOneField(
        StaffNotificationProfile,
        on_delete=models.CASCADE,
        related_name="kakao_connection",
        verbose_name="직원",
    )
    kakao_user_id = models.BigIntegerField("카카오 회원번호", null=True, blank=True)
    access_token_encrypted = models.TextField("암호화 액세스 토큰", blank=True)
    refresh_token_encrypted = models.TextField("암호화 리프레시 토큰", blank=True)
    access_token_expires_at = models.DateTimeField("액세스 토큰 만료", null=True, blank=True)
    refresh_token_expires_at = models.DateTimeField("리프레시 토큰 만료", null=True, blank=True)
    connected_at = models.DateTimeField("연결 시각", null=True, blank=True)
    last_refreshed_at = models.DateTimeField("마지막 갱신 시각", null=True, blank=True)
    is_active = models.BooleanField("연결 사용", default=False)
    reconnect_required = models.BooleanField("재연결 필요", default=False)
    last_error_code = models.CharField("최근 오류 코드", max_length=80, blank=True)

    class Meta:
        verbose_name = "카카오톡 연결"
        verbose_name_plural = "카카오톡 연결 상태"

    def __str__(self):
        return f"{self.profile} - {'연결됨' if self.is_active else '연결 안 됨'}"


class NotificationConfiguration(models.Model):
    singleton_key = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    first_reminder_minutes = models.PositiveIntegerField("1차 재알림(분)", default=20)
    second_reminder_minutes = models.PositiveIntegerField("2차 재알림(분)", default=60)
    max_reminders = models.PositiveSmallIntegerField("최대 재알림 횟수", default=2)
    max_delivery_attempts = models.PositiveSmallIntegerField("최대 발송 시도 횟수", default=5)
    worker_poll_seconds = models.PositiveSmallIntegerField("작업 확인 간격(초)", default=10)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    class Meta:
        verbose_name = "알림 운영 설정"
        verbose_name_plural = "알림 운영 설정"

    @classmethod
    def current(cls):
        configuration, _created = cls.objects.get_or_create(singleton_key=1)
        return configuration

    def reminder_delays(self):
        delays = [self.first_reminder_minutes, self.second_reminder_minutes]
        return [delay for delay in delays[: self.max_reminders] if delay > 0]

    def __str__(self):
        return "알림 운영 설정"


class NotificationJob(models.Model):
    class Channel(models.TextChoices):
        WEB_PUSH = "web_push", "웹 푸시"
        KAKAO = "kakao", "카카오톡"

    class Kind(models.TextChoices):
        INITIAL = "initial", "신규 상담"
        REMINDER = "reminder", "미확인 재알림"
        TEST = "test", "시험 알림"

    class Status(models.TextChoices):
        PENDING = "pending", "대기"
        PROCESSING = "processing", "처리 중"
        RETRY = "retry", "재시도 대기"
        SENT = "sent", "발송 완료"
        FAILED = "failed", "발송 실패"
        CANCELLED = "cancelled", "취소"

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="notification_jobs",
        verbose_name="상담",
        null=True,
        blank=True,
    )
    recipient = models.ForeignKey(
        StaffNotificationProfile,
        on_delete=models.CASCADE,
        related_name="notification_jobs",
        verbose_name="수신 직원",
    )
    channel = models.CharField("알림 채널", max_length=20, choices=Channel.choices)
    kind = models.CharField("알림 종류", max_length=20, choices=Kind.choices)
    sequence = models.PositiveSmallIntegerField("재알림 순번", default=0)
    status = models.CharField(
        "처리 상태",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    idempotency_key = models.CharField("중복 방지 키", max_length=160, unique=True)
    safe_payload = models.JSONField("최소 알림 내용", default=dict, blank=True)
    scheduled_at = models.DateTimeField("발송 예정 시각", default=timezone.now)
    locked_at = models.DateTimeField("작업 시작 시각", null=True, blank=True)
    sent_at = models.DateTimeField("발송 완료 시각", null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField("시도 횟수", default=0)
    max_attempts = models.PositiveSmallIntegerField("최대 시도 횟수", default=5)
    last_error_code = models.CharField("최근 오류 코드", max_length=80, blank=True)
    last_error_message = models.CharField("최근 오류 요약", max_length=200, blank=True)
    created_at = models.DateTimeField("생성 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    class Meta:
        verbose_name = "알림 작업"
        verbose_name_plural = "알림 작업 현황"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "scheduled_at"], name="notify_status_due_idx"),
            models.Index(fields=["consultation", "kind"], name="notify_consult_kind_idx"),
        ]

    def __str__(self):
        target = self.consultation.reference_code if self.consultation_id else "시험"
        return f"{target} / {self.recipient} / {self.get_channel_display()}"


class NotificationDeliveryLog(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "성공"
        FAILED = "failed", "실패"
        EXPIRED = "expired", "구독 만료"
        SKIPPED = "skipped", "건너뜀"

    job = models.ForeignKey(
        NotificationJob,
        on_delete=models.CASCADE,
        related_name="delivery_logs",
        verbose_name="알림 작업",
    )
    push_subscription = models.ForeignKey(
        PushSubscription,
        on_delete=models.SET_NULL,
        related_name="delivery_logs",
        verbose_name="푸시 기기",
        null=True,
        blank=True,
    )
    status = models.CharField("결과", max_length=20, choices=Status.choices)
    response_code = models.PositiveIntegerField("응답 코드", null=True, blank=True)
    error_code = models.CharField("오류 코드", max_length=80, blank=True)
    detail = models.CharField("오류 요약", max_length=200, blank=True)
    attempted_at = models.DateTimeField("시도 시각", auto_now_add=True)

    class Meta:
        verbose_name = "알림 발송 기록"
        verbose_name_plural = "알림 발송 기록"
        ordering = ["-attempted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job", "push_subscription"],
                condition=models.Q(push_subscription__isnull=False, status="sent"),
                name="unique_successful_push_delivery",
            )
        ]

    def __str__(self):
        return f"{self.job_id} - {self.get_status_display()}"
