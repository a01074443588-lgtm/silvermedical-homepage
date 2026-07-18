from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from consultations.models import Consultation
from staff_notifications.models import StaffNotificationProfile


class Command(BaseCommand):
    help = "Configure the initial SilverMedical notification recipient."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="silveradmin")
        parser.add_argument("--name", default="연규항")
        parser.add_argument("--role", default="대표·시설장")

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(username=options["username"])
        except get_user_model().DoesNotExist as exc:
            raise CommandError("The requested staff user does not exist.") from exc
        if not user.is_staff or not user.is_active:
            raise CommandError("The requested user must be active staff.")
        profile, _created = StaffNotificationProfile.objects.get_or_create(
            user=user,
            defaults={"display_name": options["name"]},
        )
        profile.display_name = options["name"]
        profile.role_title = options["role"]
        profile.service_scope = StaffNotificationProfile.ServiceScope.ALL
        profile.consultation_types = [value for value, _label in Consultation.Category.choices]
        profile.web_push_enabled = True
        profile.kakao_enabled = True
        profile.reminder_enabled = True
        profile.is_active = True
        profile.save()
        self.stdout.write(self.style.SUCCESS(f"Configured notification profile: {profile}"))
