from django.apps import AppConfig


class StaffNotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "staff_notifications"
    verbose_name = "알림 관리"

    def ready(self):
        from . import signals  # noqa: F401
