import json
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .kakao import (
    KakaoApiError,
    exchange_authorization_code,
    kakao_is_configured,
    unlink_connection,
)
from .models import (
    KakaoConnection,
    NotificationJob,
    PushSubscription,
    StaffNotificationProfile,
)
from .services import enqueue_test_notification
from .webpush import webpush_is_configured


def _profile_for(user):
    profile, _created = StaffNotificationProfile.objects.get_or_create(
        user=user,
        defaults={
            "display_name": user.get_full_name().strip() or user.username,
            "is_active": user.is_active,
        },
    )
    return profile


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


@staff_member_required
@never_cache
def dashboard(request):
    profile = _profile_for(request.user)
    connection = getattr(profile, "kakao_connection", None)
    context = {
        **admin.site.each_context(request),
        "title": "내 알림 설정",
        "profile": profile,
        "push_subscriptions": profile.push_subscriptions.filter(is_active=True),
        "kakao_connection": connection,
        "kakao_configured": kakao_is_configured(),
        "webpush_configured": webpush_is_configured(),
    }
    return render(request, "staff_notifications/dashboard.html", context)


@staff_member_required
@never_cache
def iphone_guide(request):
    return render(
        request,
        "staff_notifications/iphone_guide.html",
        {**admin.site.each_context(request), "title": "아이폰 알림 설치 안내"},
    )


@staff_member_required
@require_GET
@never_cache
def notification_status(request):
    profile = _profile_for(request.user)
    connection = getattr(profile, "kakao_connection", None)
    return JsonResponse(
        {
            "pushConfigured": webpush_is_configured(),
            "activeDeviceCount": profile.active_push_device_count,
            "webPushEnabled": profile.web_push_enabled,
            "kakaoConfigured": kakao_is_configured(),
            "kakaoEnabled": profile.kakao_enabled,
            "kakaoConnected": bool(connection and connection.is_active),
            "kakaoReconnectRequired": bool(connection and connection.reconnect_required),
            "reminderEnabled": profile.reminder_enabled,
        }
    )


@staff_member_required
@require_GET
@never_cache
def push_config(request):
    return JsonResponse(
        {
            "configured": webpush_is_configured(),
            "publicKey": settings.WEBPUSH_VAPID_PUBLIC_KEY if webpush_is_configured() else "",
        }
    )


@staff_member_required
@require_POST
def push_subscribe(request):
    data = _json_body(request)
    if not data or not webpush_is_configured():
        return JsonResponse({"ok": False, "error": "push_not_configured"}, status=503)
    endpoint = str(data.get("endpoint", "")).strip()
    keys = data.get("keys") or {}
    p256dh = str(keys.get("p256dh", "")).strip()
    auth = str(keys.get("auth", "")).strip()
    if not endpoint.startswith("https://") or not p256dh or not auth:
        return JsonResponse({"ok": False, "error": "invalid_subscription"}, status=400)
    if len(endpoint) > 4096 or len(p256dh) > 1024 or len(auth) > 1024:
        return JsonResponse({"ok": False, "error": "subscription_too_large"}, status=400)
    profile = _profile_for(request.user)
    now = timezone.now()
    subscription, _created = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "profile": profile,
            "p256dh": p256dh,
            "auth": auth,
            "device_name": str(data.get("deviceName", ""))[:100],
            "browser": str(data.get("browser", ""))[:80],
            "is_active": True,
            "last_used_at": now,
            "deactivated_at": None,
        },
    )
    profile.web_push_enabled = True
    profile.last_notification_connected_at = now
    profile.save(update_fields=["web_push_enabled", "last_notification_connected_at", "updated_at"])
    return JsonResponse({"ok": True, "subscriptionId": subscription.pk})


@staff_member_required
@require_POST
def push_unsubscribe(request):
    data = _json_body(request)
    endpoint = str((data or {}).get("endpoint", "")).strip()
    if not endpoint:
        return JsonResponse({"ok": False, "error": "endpoint_required"}, status=400)
    profile = _profile_for(request.user)
    updated = profile.push_subscriptions.filter(endpoint=endpoint, is_active=True).update(
        is_active=False,
        deactivated_at=timezone.now(),
    )
    return JsonResponse({"ok": True, "updated": updated})


@staff_member_required
@require_POST
def push_device_remove(request, subscription_id):
    profile = _profile_for(request.user)
    updated = profile.push_subscriptions.filter(pk=subscription_id, is_active=True).update(
        is_active=False,
        deactivated_at=timezone.now(),
    )
    if updated:
        messages.success(request, "선택한 알림 기기를 해제했습니다.")
    return redirect("staff_notifications:dashboard")


@staff_member_required
@require_POST
def test_notification(request):
    data = _json_body(request)
    channel = str((data or {}).get("channel", ""))
    if channel not in NotificationJob.Channel.values:
        return JsonResponse({"ok": False, "error": "invalid_channel"}, status=400)
    profile = _profile_for(request.user)
    if channel == NotificationJob.Channel.WEB_PUSH and not profile.push_subscriptions.filter(
        is_active=True
    ).exists():
        return JsonResponse({"ok": False, "error": "no_push_device"}, status=409)
    if channel == NotificationJob.Channel.KAKAO and not (
        hasattr(profile, "kakao_connection") and profile.kakao_connection.is_active
    ):
        return JsonResponse({"ok": False, "error": "kakao_not_connected"}, status=409)
    job = enqueue_test_notification(profile, channel)
    return JsonResponse({"ok": True, "jobId": job.pk})


@staff_member_required
@require_GET
def kakao_connect(request):
    if not kakao_is_configured():
        messages.error(request, "카카오 개발자 앱 설정이 아직 완료되지 않았습니다.")
        return redirect("staff_notifications:dashboard")
    state = secrets.token_urlsafe(32)
    request.session["kakao_oauth_state"] = state
    query = urlencode(
        {
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "response_type": "code",
            "scope": "talk_message",
            "state": state,
            "prompt": "select_account",
        }
    )
    return redirect(f"https://kauth.kakao.com/oauth/authorize?{query}")


@staff_member_required
@require_GET
def kakao_callback(request):
    expected_state = request.session.pop("kakao_oauth_state", "")
    received_state = request.GET.get("state", "")
    if not expected_state or not secrets.compare_digest(expected_state, received_state):
        messages.error(request, "카카오 연결 요청을 확인할 수 없습니다. 다시 연결해 주세요.")
        return redirect("staff_notifications:dashboard")
    if request.GET.get("error"):
        messages.error(request, "카카오 연결이 취소되었거나 동의가 완료되지 않았습니다.")
        return redirect("staff_notifications:dashboard")
    code = request.GET.get("code", "")
    if not code:
        messages.error(request, "카카오 인증 코드가 전달되지 않았습니다.")
        return redirect("staff_notifications:dashboard")
    profile = _profile_for(request.user)
    connection, _created = KakaoConnection.objects.get_or_create(profile=profile)
    try:
        exchange_authorization_code(connection, code)
    except KakaoApiError as exc:
        connection.last_error_code = exc.code
        connection.reconnect_required = True
        connection.is_active = False
        connection.save(update_fields=["last_error_code", "reconnect_required", "is_active"])
        messages.error(request, "카카오 연결에 실패했습니다. 개발자 앱 설정을 확인해 주세요.")
    else:
        profile.kakao_enabled = True
        profile.last_notification_connected_at = timezone.now()
        profile.save(update_fields=["kakao_enabled", "last_notification_connected_at", "updated_at"])
        messages.success(request, "카카오톡 나에게 보내기가 연결되었습니다.")
    return redirect("staff_notifications:dashboard")


@staff_member_required
@require_POST
def kakao_disconnect(request):
    profile = _profile_for(request.user)
    if hasattr(profile, "kakao_connection"):
        unlink_connection(profile.kakao_connection)
    profile.kakao_enabled = False
    profile.save(update_fields=["kakao_enabled", "updated_at"])
    messages.success(request, "카카오톡 알림 연결을 해제했습니다.")
    return redirect("staff_notifications:dashboard")


@require_GET
@never_cache
def notification_manifest(request):
    response = JsonResponse(
        {
            "id": "/staff/notifications/",
            "name": "실버메디컬 상담 알림",
            "short_name": "실버메디컬 알림",
            "start_url": "/staff/notifications/",
            "scope": "/staff/",
            "display": "standalone",
            "background_color": "#f7faf7",
            "theme_color": "#246b43",
            "icons": [
                {
                    "src": "/staff-assets/staff_notifications/logo.png",
                    "sizes": "420x420",
                    "type": "image/png",
                    "purpose": "any",
                },
            ],
        }
    )
    response["Content-Type"] = "application/manifest+json"
    return response


@require_GET
@never_cache
def notification_service_worker(request):
    script = r'''
self.addEventListener("push", (event) => {
  let data = { title: "실버메디컬 상담 알림", body: "새 상담을 확인해 주세요.", url: "/staff/", tag: "silvermedical" };
  if (event.data) {
    try { data = { ...data, ...event.data.json() }; } catch (_error) {}
  }
  event.waitUntil(self.registration.showNotification(data.title, {
    body: data.body,
    icon: "/staff-assets/staff_notifications/logo.png",
    badge: "/staff-assets/staff_notifications/logo.png",
    tag: data.tag,
    renotify: true,
    data: { url: data.url || "/staff/" }
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = new URL(event.notification.data.url || "/staff/", self.location.origin).href;
  event.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
    for (const windowClient of windows) {
      if (windowClient.url === targetUrl && "focus" in windowClient) return windowClient.focus();
    }
    return clients.openWindow ? clients.openWindow(targetUrl) : undefined;
  }));
});
'''
    response = HttpResponse(script, content_type="application/javascript; charset=utf-8")
    response["Service-Worker-Allowed"] = "/staff/"
    return response
