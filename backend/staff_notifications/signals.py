from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import StaffNotificationProfile


@receiver(post_save, sender=get_user_model())
def maintain_staff_notification_profile(sender, instance, created, **kwargs):
    if not instance.is_staff or not instance.is_active:
        if hasattr(instance, "notification_profile"):
            profile = instance.notification_profile
            profile.is_active = False
            profile.save(update_fields=["is_active", "updated_at"])
            profile.push_subscriptions.filter(is_active=True).update(
                is_active=False,
                deactivated_at=timezone.now(),
            )
            if hasattr(profile, "kakao_connection"):
                profile.kakao_connection.is_active = False
                profile.kakao_connection.reconnect_required = True
                profile.kakao_connection.save(
                    update_fields=["is_active", "reconnect_required"]
                )
        return

    defaults = {
        "display_name": instance.get_full_name().strip() or instance.username,
        "role_title": "",
        "is_active": instance.is_active,
    }
    profile, profile_created = StaffNotificationProfile.objects.get_or_create(
        user=instance,
        defaults=defaults,
    )
