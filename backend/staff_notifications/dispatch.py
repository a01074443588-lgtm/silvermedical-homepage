from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .kakao import KakaoApiError, send_to_me
from .models import (
    NotificationDeliveryLog,
    NotificationJob,
)
from .webpush import WebPushDeliveryError, send_web_push


RETRY_DELAYS_MINUTES = [1, 5, 15, 60, 180]


def _retry_delay(attempt_count):
    index = min(max(attempt_count - 1, 0), len(RETRY_DELAYS_MINUTES) - 1)
    return timedelta(minutes=RETRY_DELAYS_MINUTES[index])


@transaction.atomic
def claim_next_job():
    now = timezone.now()
    stale_before = now - timedelta(minutes=5)
    NotificationJob.objects.filter(
        status=NotificationJob.Status.PROCESSING,
        locked_at__lt=stale_before,
    ).update(
        status=NotificationJob.Status.RETRY,
        scheduled_at=now,
        locked_at=None,
        last_error_code="stale_worker_recovered",
        last_error_message="중단된 작업 자동 복구",
        updated_at=now,
    )
    job = (
        NotificationJob.objects.select_for_update()
        .select_related("consultation", "recipient", "recipient__user")
        .filter(
            status__in=[NotificationJob.Status.PENDING, NotificationJob.Status.RETRY],
            scheduled_at__lte=now,
        )
        .order_by("scheduled_at", "pk")
        .first()
    )
    if not job:
        return None
    job.status = NotificationJob.Status.PROCESSING
    job.locked_at = now
    job.attempt_count += 1
    job.save(update_fields=["status", "locked_at", "attempt_count", "updated_at"])
    return job


def _cancel_job(job, code, message):
    NotificationJob.objects.filter(pk=job.pk).update(
        status=NotificationJob.Status.CANCELLED,
        locked_at=None,
        last_error_code=code,
        last_error_message=message[:200],
        updated_at=timezone.now(),
    )


def _mark_sent(job):
    now = timezone.now()
    NotificationJob.objects.filter(pk=job.pk).update(
        status=NotificationJob.Status.SENT,
        locked_at=None,
        sent_at=now,
        last_error_code="",
        last_error_message="",
        updated_at=now,
    )


def _mark_failed_or_retry(job, code, message):
    now = timezone.now()
    if job.attempt_count >= job.max_attempts:
        status = NotificationJob.Status.FAILED
        scheduled_at = job.scheduled_at
    else:
        status = NotificationJob.Status.RETRY
        scheduled_at = now + _retry_delay(job.attempt_count)
    NotificationJob.objects.filter(pk=job.pk).update(
        status=status,
        scheduled_at=scheduled_at,
        locked_at=None,
        last_error_code=str(code)[:80],
        last_error_message=str(message)[:200],
        updated_at=now,
    )


def _deliver_web_push(job):
    subscriptions = list(
        job.recipient.push_subscriptions.filter(is_active=True).order_by("pk")
    )
    if not subscriptions:
        raise WebPushDeliveryError("no_active_push_subscription")

    success_count = 0
    transient_failure_count = 0
    for subscription in subscriptions:
        already_sent = NotificationDeliveryLog.objects.filter(
            job=job,
            push_subscription=subscription,
            status=NotificationDeliveryLog.Status.SENT,
        ).exists()
        if already_sent:
            success_count += 1
            continue
        try:
            response_code = send_web_push(subscription, job.safe_payload)
            subscription.last_used_at = timezone.now()
            subscription.save(update_fields=["last_used_at"])
            NotificationDeliveryLog.objects.create(
                job=job,
                push_subscription=subscription,
                status=NotificationDeliveryLog.Status.SENT,
                response_code=response_code or 201,
            )
            success_count += 1
        except WebPushDeliveryError as exc:
            if exc.expired:
                subscription.deactivate()
            else:
                transient_failure_count += 1
            NotificationDeliveryLog.objects.create(
                job=job,
                push_subscription=subscription,
                status=(
                    NotificationDeliveryLog.Status.EXPIRED
                    if exc.expired
                    else NotificationDeliveryLog.Status.FAILED
                ),
                response_code=exc.status,
                error_code=exc.code,
                detail="만료된 구독 자동 해제" if exc.expired else "웹 푸시 전송 실패",
            )
    if transient_failure_count:
        raise WebPushDeliveryError("partial_push_delivery_failed")
    if success_count == 0:
        raise WebPushDeliveryError("all_push_deliveries_failed")


def _deliver_kakao(job):
    if not job.recipient.kakao_enabled:
        raise KakaoApiError("kakao_disabled")
    if not hasattr(job.recipient, "kakao_connection"):
        raise KakaoApiError("kakao_not_connected")
    connection = job.recipient.kakao_connection
    send_to_me(connection, job.safe_payload)
    NotificationDeliveryLog.objects.create(
        job=job,
        status=NotificationDeliveryLog.Status.SENT,
        response_code=200,
    )


def process_job(job):
    if not job.recipient.is_active or not job.recipient.user.is_active:
        _cancel_job(job, "recipient_inactive", "비활성 직원 알림 취소")
        return "cancelled"
    if (
        job.kind == NotificationJob.Kind.REMINDER
        and job.consultation_id
        and job.consultation.first_viewed_at is not None
    ):
        _cancel_job(job, "consultation_acknowledged", "확인된 상담 재알림 취소")
        return "cancelled"

    try:
        if job.channel == NotificationJob.Channel.WEB_PUSH:
            _deliver_web_push(job)
        elif job.channel == NotificationJob.Channel.KAKAO:
            _deliver_kakao(job)
        else:
            _cancel_job(job, "unsupported_channel", "지원하지 않는 알림 채널")
            return "cancelled"
    except WebPushDeliveryError as exc:
        _mark_failed_or_retry(job, exc.code, "웹 푸시 전송 실패")
        return "retry"
    except KakaoApiError as exc:
        NotificationDeliveryLog.objects.create(
            job=job,
            status=NotificationDeliveryLog.Status.FAILED,
            response_code=exc.status,
            error_code=exc.code,
            detail="카카오톡 전송 실패",
        )
        _mark_failed_or_retry(job, exc.code, "카카오톡 전송 실패")
        return "retry"
    except Exception:
        _mark_failed_or_retry(job, "unexpected_delivery_error", "알림 전송 중 오류")
        return "retry"

    _mark_sent(job)
    return "sent"


def process_due_jobs(limit=20):
    counts = {"sent": 0, "retry": 0, "cancelled": 0}
    for _index in range(limit):
        job = claim_next_job()
        if not job:
            break
        result = process_job(job)
        counts[result] = counts.get(result, 0) + 1
    return counts
