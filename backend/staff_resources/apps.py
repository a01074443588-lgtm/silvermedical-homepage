from django.apps import AppConfig


class StaffResourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "staff_resources"
    verbose_name = "직원 자료실"

    def ready(self):
        from . import permissions  # noqa: F401
