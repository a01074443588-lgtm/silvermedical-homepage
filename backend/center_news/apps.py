from django.apps import AppConfig


class CenterNewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "center_news"
    verbose_name = "콘텐츠 관리"

    def ready(self):
        from . import permissions  # noqa: F401
