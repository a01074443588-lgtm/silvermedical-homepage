import json
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .crypto import decrypt_token, encrypt_token


KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_URL = "https://kapi.kakao.com/v2/user/me"
KAKAO_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
KAKAO_UNLINK_URL = "https://kapi.kakao.com/v1/user/unlink"


class KakaoApiError(Exception):
    def __init__(self, code, status=None):
        self.code = str(code or "kakao_api_error")[:80]
        self.status = status
        super().__init__(self.code)


def kakao_is_configured():
    return bool(settings.KAKAO_REST_API_KEY and settings.KAKAO_REDIRECT_URI)


def _post_form(url, data, access_token=""):
    encoded = urlencode(data).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    request = Request(url, data=encoded, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read(65536).decode("utf-8"))
    except HTTPError as exc:
        error_code = f"http_{exc.code}"
        try:
            body = json.loads(exc.read(8192).decode("utf-8"))
            error_code = body.get("code") or body.get("error") or error_code
        except (ValueError, UnicodeDecodeError):
            pass
        raise KakaoApiError(error_code, exc.code) from exc
    except (URLError, TimeoutError) as exc:
        raise KakaoApiError("network_error") from exc


def _token_request(data):
    if not kakao_is_configured():
        raise KakaoApiError("kakao_not_configured")
    payload = {
        **data,
        "client_id": settings.KAKAO_REST_API_KEY,
    }
    if settings.KAKAO_CLIENT_SECRET:
        payload["client_secret"] = settings.KAKAO_CLIENT_SECRET
    return _post_form(KAKAO_TOKEN_URL, payload)


def exchange_authorization_code(connection, code):
    token_data = _token_request(
        {
            "grant_type": "authorization_code",
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
        }
    )
    now = timezone.now()
    connection.access_token_encrypted = encrypt_token(token_data["access_token"])
    connection.refresh_token_encrypted = encrypt_token(token_data["refresh_token"])
    connection.access_token_expires_at = now + timedelta(seconds=token_data["expires_in"])
    connection.refresh_token_expires_at = now + timedelta(
        seconds=token_data["refresh_token_expires_in"]
    )
    connection.connected_at = now
    connection.last_refreshed_at = now
    connection.is_active = True
    connection.reconnect_required = False
    connection.last_error_code = ""

    user_data = _get_user(decrypt_token(connection.access_token_encrypted))
    connection.kakao_user_id = user_data.get("id")
    connection.save()
    return connection


def _get_user(access_token):
    request = Request(
        KAKAO_USER_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read(65536).decode("utf-8"))
    except HTTPError as exc:
        raise KakaoApiError(f"http_{exc.code}", exc.code) from exc
    except (URLError, TimeoutError) as exc:
        raise KakaoApiError("network_error") from exc


def refresh_connection(connection):
    refresh_token = decrypt_token(connection.refresh_token_encrypted)
    if not refresh_token:
        raise KakaoApiError("refresh_token_missing")

    token_data = _token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )
    now = timezone.now()
    connection.access_token_encrypted = encrypt_token(token_data["access_token"])
    connection.access_token_expires_at = now + timedelta(seconds=token_data["expires_in"])
    if token_data.get("refresh_token"):
        connection.refresh_token_encrypted = encrypt_token(token_data["refresh_token"])
        connection.refresh_token_expires_at = now + timedelta(
            seconds=token_data["refresh_token_expires_in"]
        )
    connection.last_refreshed_at = now
    connection.is_active = True
    connection.reconnect_required = False
    connection.last_error_code = ""
    connection.save()
    return decrypt_token(connection.access_token_encrypted)


def get_access_token(connection):
    if not connection.is_active or connection.reconnect_required:
        raise KakaoApiError("kakao_reconnect_required")
    if (
        connection.access_token_expires_at
        and connection.access_token_expires_at > timezone.now() + timedelta(minutes=5)
    ):
        return decrypt_token(connection.access_token_encrypted)
    try:
        return refresh_connection(connection)
    except KakaoApiError as exc:
        connection.is_active = False
        connection.reconnect_required = True
        connection.last_error_code = exc.code
        connection.save(update_fields=["is_active", "reconnect_required", "last_error_code"])
        raise


def send_to_me(connection, payload):
    access_token = get_access_token(connection)
    template = {
        "object_type": "text",
        "text": f"{payload['title']}\n\n{payload['body']}",
        "link": {
            "web_url": payload["url"],
            "mobile_web_url": payload["url"],
        },
        "button_title": "상담 확인하기",
    }
    return _post_form(
        KAKAO_MEMO_URL,
        {"template_object": json.dumps(template, ensure_ascii=False)},
        access_token=access_token,
    )


def unlink_connection(connection):
    if connection.is_active and connection.access_token_encrypted:
        try:
            _post_form(
                KAKAO_UNLINK_URL,
                {},
                access_token=decrypt_token(connection.access_token_encrypted),
            )
        except KakaoApiError:
            pass
    connection.access_token_encrypted = ""
    connection.refresh_token_encrypted = ""
    connection.access_token_expires_at = None
    connection.refresh_token_expires_at = None
    connection.is_active = False
    connection.reconnect_required = False
    connection.last_error_code = ""
    connection.save()
