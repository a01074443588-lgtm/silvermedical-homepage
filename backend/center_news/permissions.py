from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def ensure_content_editor_group(sender, **kwargs):
    if sender.label != "center_news":
        return

    group, _ = Group.objects.get_or_create(name="콘텐츠 담당자")
    permissions = Permission.objects.filter(
        content_type__app_label="center_news",
        codename__in=("add_post", "change_post", "delete_post", "view_post"),
    )
    group.permissions.set(permissions)
