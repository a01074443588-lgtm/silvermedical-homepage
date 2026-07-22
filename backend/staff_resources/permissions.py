from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def ensure_resource_editor_group(sender, **kwargs):
    if sender.label != "staff_resources":
        return

    group, _ = Group.objects.get_or_create(name="직원자료 담당자")
    permissions = Permission.objects.filter(
        content_type__app_label="staff_resources",
        codename__in=(
            "add_staffresource",
            "change_staffresource",
            "delete_staffresource",
            "view_staffresource",
        ),
    )
    group.permissions.set(permissions)
