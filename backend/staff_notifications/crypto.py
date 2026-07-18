from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class TokenEncryptionError(Exception):
    pass


def get_token_cipher():
    key = settings.NOTIFICATION_TOKEN_ENCRYPTION_KEY
    if not key:
        raise ImproperlyConfigured(
            "NOTIFICATION_TOKEN_ENCRYPTION_KEY is required for Kakao connections."
        )
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "NOTIFICATION_TOKEN_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc


def encrypt_token(token):
    if not token:
        return ""
    return get_token_cipher().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_token(encrypted_token):
    if not encrypted_token:
        return ""
    try:
        return get_token_cipher().decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenEncryptionError("Stored token could not be decrypted.") from exc
