import json

from django.conf import settings
from pywebpush import WebPushException, webpush


class WebPushDeliveryError(Exception):
    def __init__(self, code, status=None, expired=False):
        self.code = str(code)[:80]
        self.status = status
        self.expired = expired
        super().__init__(self.code)


def webpush_is_configured():
    return bool(
        settings.WEBPUSH_VAPID_PRIVATE_KEY
        and settings.WEBPUSH_VAPID_PUBLIC_KEY
        and settings.WEBPUSH_VAPID_SUBJECT
    )


def send_web_push(subscription, payload):
    if not webpush_is_configured():
        raise WebPushDeliveryError("webpush_not_configured")
    try:
        response = webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.WEBPUSH_VAPID_SUBJECT},
            ttl=3600,
            timeout=15,
        )
        return response.status_code
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        expired = status in {404, 410}
        raise WebPushDeliveryError(
            "push_subscription_expired" if expired else f"push_http_{status or 'error'}",
            status=status,
            expired=expired,
        ) from exc
