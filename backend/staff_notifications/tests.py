import json
from datetime import timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from consultations.models import Consultation, ConsultationStatusHistory

from .crypto import decrypt_token, encrypt_token
from .dispatch import process_due_jobs
from .models import (
    NotificationConfiguration,
    NotificationDeliveryLog,
    NotificationJob,
    PushSubscription,
    StaffNotificationProfile,
)
from .services import acknowledge_consultation, enqueue_consultation_notifications
from .webpush import WebPushDeliveryError


def make_consultation():
    return Consultation.objects.create(
        category=Consultation.Category.NURSING_HOME,
        guardian_name="홍길동",
        phone="010-1234-5678",
        preferred_contact_time=Consultation.ContactTime.AFTERNOON,
        message="어머니의 요양원 입소 상담을 받고 싶습니다.",
        privacy_agreed_at=timezone.now(),
    )


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="notification-admin",
            email="notify@example.com",
            password="A-long-test-password-2026",
        )
        self.profile = self.user.notification_profile
        self.profile.display_name = "연규항"
        self.profile.web_push_enabled = True
        self.profile.kakao_enabled = True
        self.profile.reminder_enabled = True
        self.profile.save()
        NotificationConfiguration.objects.create(
            first_reminder_minutes=20,
            second_reminder_minutes=60,
            max_reminders=2,
        )

    def test_consultation_creates_initial_and_reminder_jobs_for_both_channels(self):
        consultation = make_consultation()

        enqueue_consultation_notifications(consultation)

        jobs = NotificationJob.objects.filter(consultation=consultation)
        self.assertEqual(jobs.count(), 6)
        self.assertEqual(jobs.filter(kind=NotificationJob.Kind.INITIAL).count(), 2)
        self.assertEqual(jobs.filter(kind=NotificationJob.Kind.REMINDER).count(), 4)
        payload = jobs.first().safe_payload
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertIn("홍○○", serialized)
        self.assertIn("5678", serialized)
        self.assertNotIn("010-1234-5678", serialized)
        self.assertNotIn(consultation.message, serialized)

    def test_enqueuing_same_consultation_is_idempotent(self):
        consultation = make_consultation()

        enqueue_consultation_notifications(consultation)
        enqueue_consultation_notifications(consultation)

        self.assertEqual(NotificationJob.objects.filter(consultation=consultation).count(), 6)

    def test_acknowledgement_records_viewer_and_cancels_reminders(self):
        consultation = make_consultation()
        enqueue_consultation_notifications(consultation)

        acknowledge_consultation(consultation.pk, self.user)

        consultation.refresh_from_db()
        self.assertEqual(consultation.status, Consultation.Status.ACKNOWLEDGED)
        self.assertEqual(consultation.first_viewed_by, self.user)
        self.assertIsNotNone(consultation.first_viewed_at)
        self.assertTrue(
            ConsultationStatusHistory.objects.filter(
                consultation=consultation,
                event=ConsultationStatusHistory.Event.ACKNOWLEDGED,
            ).exists()
        )
        self.assertFalse(
            NotificationJob.objects.filter(
                consultation=consultation,
                kind=NotificationJob.Kind.REMINDER,
                status=NotificationJob.Status.PENDING,
            ).exists()
        )

    def test_deactivating_staff_account_stops_all_notification_connections(self):
        PushSubscription.objects.create(
            profile=self.profile,
            endpoint="https://push.example/device",
            p256dh="p256dh",
            auth="auth",
        )
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_active)
        self.assertFalse(self.profile.push_subscriptions.get().is_active)


class NotificationWorkerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="worker-admin",
            email="worker@example.com",
            password="A-long-test-password-2026",
        )
        self.profile = self.user.notification_profile
        self.profile.web_push_enabled = True
        self.profile.save(update_fields=["web_push_enabled", "updated_at"])
        self.subscription = PushSubscription.objects.create(
            profile=self.profile,
            endpoint="https://push.example/device",
            p256dh="p256dh",
            auth="auth",
        )
        self.job = NotificationJob.objects.create(
            recipient=self.profile,
            channel=NotificationJob.Channel.WEB_PUSH,
            kind=NotificationJob.Kind.TEST,
            idempotency_key="worker-test-job",
            safe_payload={
                "title": "시험",
                "body": "시험 알림",
                "url": "https://staff.silvermedical.kr/staff/notifications/",
            },
            scheduled_at=timezone.now() - timedelta(seconds=1),
        )

    @patch("staff_notifications.dispatch.send_web_push")
    def test_worker_sends_and_records_delivery(self, mocked_send):
        mocked_send.return_value = 201
        result = process_due_jobs(limit=5)

        self.job.refresh_from_db()
        self.assertEqual(result["sent"], 1)
        self.assertEqual(self.job.status, NotificationJob.Status.SENT)
        self.assertEqual(
            NotificationDeliveryLog.objects.filter(
                job=self.job,
                status=NotificationDeliveryLog.Status.SENT,
            ).count(),
            1,
        )
        mocked_send.assert_called_once()

    @patch("staff_notifications.dispatch.send_web_push")
    def test_expired_push_subscription_is_deactivated(self, mocked_send):
        mocked_send.side_effect = WebPushDeliveryError(
            "push_subscription_expired",
            status=410,
            expired=True,
        )

        process_due_jobs(limit=5)

        self.subscription.refresh_from_db()
        self.job.refresh_from_db()
        self.assertFalse(self.subscription.is_active)
        self.assertEqual(self.job.status, NotificationJob.Status.RETRY)
        self.assertTrue(
            NotificationDeliveryLog.objects.filter(
                job=self.job,
                status=NotificationDeliveryLog.Status.EXPIRED,
            ).exists()
        )

    @patch("staff_notifications.dispatch.send_web_push")
    def test_partial_device_failure_retries_only_failed_device(self, mocked_send):
        second = PushSubscription.objects.create(
            profile=self.profile,
            endpoint="https://push.example/second-device",
            p256dh="second-key",
            auth="second-auth",
        )
        mocked_send.side_effect = [None, WebPushDeliveryError("network_error"), None]

        first_result = process_due_jobs(limit=1)
        self.job.refresh_from_db()
        self.assertEqual(first_result["retry"], 1)
        self.assertEqual(self.job.status, NotificationJob.Status.RETRY)

        self.job.scheduled_at = timezone.now() - timedelta(seconds=1)
        self.job.save(update_fields=["scheduled_at"])
        second_result = process_due_jobs(limit=1)

        self.job.refresh_from_db()
        self.assertEqual(second_result["sent"], 1)
        self.assertEqual(self.job.status, NotificationJob.Status.SENT)
        self.assertEqual(mocked_send.call_count, 3)
        self.assertTrue(
            NotificationDeliveryLog.objects.filter(
                job=self.job,
                push_subscription=second,
                status=NotificationDeliveryLog.Status.SENT,
            ).exists()
        )


@override_settings(
    WEBPUSH_VAPID_PRIVATE_KEY="test-private",
    WEBPUSH_VAPID_PUBLIC_KEY="test-public",
    WEBPUSH_VAPID_SUBJECT="mailto:test@example.com",
)
class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="api-admin",
            email="api@example.com",
            password="A-long-test-password-2026",
        )
        self.client.force_login(self.user)

    def test_dashboard_requires_staff_login(self):
        self.client.logout()
        response = self.client.get(reverse("staff_notifications:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/staff/login/", response.url)

    def test_push_subscription_is_stored_per_device(self):
        response = self.client.post(
            reverse("staff_notifications:push_subscribe"),
            data=json.dumps(
                {
                    "endpoint": "https://push.example/api-device",
                    "keys": {"p256dh": "device-key", "auth": "device-auth"},
                    "deviceName": "Windows Chrome",
                    "browser": "Google Chrome",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        subscription = PushSubscription.objects.get()
        self.assertEqual(subscription.profile.user, self.user)
        self.assertEqual(subscription.device_name, "Windows Chrome")

    def test_test_push_requires_registered_device(self):
        response = self.client.post(
            reverse("staff_notifications:test_notification"),
            data=json.dumps({"channel": "web_push"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "no_push_device")

    def test_manifest_and_service_worker_are_available(self):
        manifest = self.client.get(reverse("notification_manifest"))
        worker = self.client.get(reverse("notification_service_worker"))

        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.json()["display"], "standalone")
        self.assertEqual(worker.status_code, 200)
        self.assertEqual(worker["Service-Worker-Allowed"], "/staff/")

    def test_staff_without_consultation_permission_cannot_process_direct_url(self):
        consultation = make_consultation()
        user = get_user_model().objects.create_user(
            username="limited-staff",
            password="A-long-test-password-2026",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin:consultation_acknowledge", args=[consultation.pk])
        )

        self.assertEqual(response.status_code, 403)
        consultation.refresh_from_db()
        self.assertEqual(consultation.status, Consultation.Status.NEW)


class TokenEncryptionTests(TestCase):
    @override_settings(NOTIFICATION_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"))
    def test_kakao_token_is_encrypted_at_rest(self):
        raw_token = "private-kakao-token"
        encrypted = encrypt_token(raw_token)

        self.assertNotEqual(encrypted, raw_token)
        self.assertNotIn(raw_token, encrypted)
        self.assertEqual(decrypt_token(encrypted), raw_token)
