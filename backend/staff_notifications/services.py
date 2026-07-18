import logging
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from consultations.models import Consultation, ConsultationStatusHistory

from .models import (
    NotificationConfiguration,
    NotificationJob,
    StaffNotificationProfile,
)


logger = logging.getLogger(__name__)


def mask_name(name):
    cleaned = (name or "").strip()
    if not cleaned:
        return "미입력"
    if len(cleaned) == 1:
        return f"{cleaned}○"
    return f"{cleaned[0]}{'○' * (len(cleaned) - 1)}"


def phone_last_four(phone):
    digits = "".join(character for character in (phone or "") if character.isdigit())
    return digits[-4:] if len(digits) >= 4 else "확인 필요"


def build_consultation_payload(consultation, kind, sequence=0):
    local_created = timezone.localtime(consultation.created_at)
    prefix = "미확인 재알림" if kind == NotificationJob.Kind.REMINDER else "신규"
    title = f"[{prefix} {consultation.get_category_display()} 상담]"
    body = "\n".join(
        [
            f"신청자: {mask_name(consultation.guardian_name)}",
            f"연락처 끝자리: {phone_last_four(consultation.phone)}",
            f"접수 시각: {local_created:%Y-%m-%d %H:%M}",
            "상세 내용은 상담관리에서 확인하세요.",
        ]
    )
    return {
        "title": title,
        "body": body,
        "url": (
            "https://staff.silvermedical.kr/staff/consultations/"
            f"consultation/{consultation.pk}/change/"
        ),
        "tag": f"consultation-{consultation.reference_code}-{kind}-{sequence}",
        "consultation_id": consultation.pk,
    }


def _create_job(consultation, profile, channel, kind, sequence, scheduled_at, max_attempts):
    key = f"consultation:{consultation.pk}:recipient:{profile.pk}:{channel}:{kind}:{sequence}"
    payload = build_consultation_payload(consultation, kind, sequence)
    NotificationJob.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "consultation": consultation,
            "recipient": profile,
            "channel": channel,
            "kind": kind,
            "sequence": sequence,
            "safe_payload": payload,
            "scheduled_at": scheduled_at,
            "max_attempts": max_attempts,
        },
    )


def enqueue_consultation_notifications(consultation):
    configuration = NotificationConfiguration.current()
    profiles = StaffNotificationProfile.objects.select_related("user").filter(
        is_active=True,
        user__is_active=True,
        user__is_staff=True,
    )
    now = timezone.now()
    for profile in profiles:
        if not profile.accepts_category(consultation.category):
            continue
        channels = []
        if profile.web_push_enabled:
            channels.append(NotificationJob.Channel.WEB_PUSH)
        if profile.kakao_enabled:
            channels.append(NotificationJob.Channel.KAKAO)
        for channel in channels:
            _create_job(
                consultation,
                profile,
                channel,
                NotificationJob.Kind.INITIAL,
                0,
                now,
                configuration.max_delivery_attempts,
            )
            if profile.reminder_enabled:
                for sequence, delay in enumerate(configuration.reminder_delays(), start=1):
                    _create_job(
                        consultation,
                        profile,
                        channel,
                        NotificationJob.Kind.REMINDER,
                        sequence,
                        consultation.created_at + timedelta(minutes=delay),
                        configuration.max_delivery_attempts,
                    )


def safe_enqueue_consultation_notifications(consultation_id):
    try:
        consultation = Consultation.objects.get(pk=consultation_id)
        enqueue_consultation_notifications(consultation)
    except Exception:
        logger.exception(
            "Notification jobs could not be created for consultation id=%s",
            consultation_id,
        )


def enqueue_test_notification(profile, channel):
    token = secrets.token_urlsafe(12)
    payload = {
        "title": "[실버메디컬 시험 알림]",
        "body": "알림 연결이 정상입니다. 상담 상세 내용은 관리자 화면에서만 확인합니다.",
        "url": "https://staff.silvermedical.kr/staff/notifications/",
        "tag": f"notification-test-{token}",
    }
    return NotificationJob.objects.create(
        recipient=profile,
        channel=channel,
        kind=NotificationJob.Kind.TEST,
        idempotency_key=f"test:{profile.pk}:{channel}:{token}",
        safe_payload=payload,
        scheduled_at=timezone.now(),
        max_attempts=NotificationConfiguration.current().max_delivery_attempts,
    )


@transaction.atomic
def acknowledge_consultation(consultation_id, user, event=ConsultationStatusHistory.Event.ACKNOWLEDGED):
    consultation = Consultation.objects.select_for_update().get(pk=consultation_id)
    now = timezone.now()
    old_status = consultation.status
    update_fields = []
    if consultation.first_viewed_at is None:
        consultation.first_viewed_at = now
        consultation.first_viewed_by = user
        update_fields.extend(["first_viewed_at", "first_viewed_by"])
    if (
        event == ConsultationStatusHistory.Event.ACKNOWLEDGED
        and consultation.status == Consultation.Status.NEW
    ):
        consultation.status = Consultation.Status.ACKNOWLEDGED
        update_fields.append("status")
    if update_fields:
        update_fields.append("updated_at")
        consultation.save(update_fields=update_fields)
    ConsultationStatusHistory.objects.create(
        consultation=consultation,
        actor=user,
        event=event,
        from_status=old_status,
        to_status=consultation.status,
        description=(
            "접수 확인 처리"
            if event == ConsultationStatusHistory.Event.ACKNOWLEDGED
            else "관리자 화면에서 상담을 열람함"
        ),
    )
    NotificationJob.objects.filter(
        consultation=consultation,
        kind=NotificationJob.Kind.REMINDER,
        status__in=[NotificationJob.Status.PENDING, NotificationJob.Status.RETRY],
    ).update(
        status=NotificationJob.Status.CANCELLED,
        last_error_code="consultation_acknowledged",
        last_error_message="상담 확인으로 재알림 취소",
        updated_at=now,
    )
    return consultation
