import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if len(SECRET_KEY) < 32:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must contain at least 32 characters.")

DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost,192.168.30.2",
)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "benefits.apps.BenefitsConfig",
    "consultations.apps.ConsultationsConfig",
    "staff_notifications.apps.StaffNotificationsConfig",
    "center_news.apps.CenterNewsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "consultation_service.middleware.StaffSessionSafetyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "consultation_service.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "consultation_service.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DJANGO_DATABASE_PATH", "/data/consultations.sqlite3"),
        "OPTIONS": {"timeout": 20},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/staff-assets/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/news-media/"
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", "/data/news-media"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/staff/login/"
LOGIN_REDIRECT_URL = "/staff/"
LOGOUT_REDIRECT_URL = "/staff/login/"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
CONSULTATION_RETENTION_DAYS = int(os.getenv("CONSULTATION_RETENTION_DAYS", "365"))

WEBPUSH_VAPID_PRIVATE_KEY = os.getenv("WEBPUSH_VAPID_PRIVATE_KEY", "").strip()
WEBPUSH_VAPID_PUBLIC_KEY = os.getenv("WEBPUSH_VAPID_PUBLIC_KEY", "").strip()
WEBPUSH_VAPID_SUBJECT = os.getenv(
    "WEBPUSH_VAPID_SUBJECT",
    "mailto:sil3307@naver.com",
).strip()
NOTIFICATION_TOKEN_ENCRYPTION_KEY = os.getenv(
    "NOTIFICATION_TOKEN_ENCRYPTION_KEY",
    "",
).strip()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "").strip()
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "").strip()
KAKAO_REDIRECT_URI = os.getenv(
    "KAKAO_REDIRECT_URI",
    "https://staff.silvermedical.kr/staff/notifications/kakao/callback/",
).strip()
