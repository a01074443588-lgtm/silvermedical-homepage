import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand, CommandError


def base64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class Command(BaseCommand):
    help = "Generate VAPID and token-encryption secrets for the notification service."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)
        parser.add_argument("--subject", default="mailto:sil3307@naver.com")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        output = Path(options["output"])
        if output.exists() and not options["force"]:
            raise CommandError("Output file already exists. Use --force only for initial reset.")
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_der = private_key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        contents = "\n".join(
            [
                f"WEBPUSH_VAPID_PRIVATE_KEY={base64url(private_der)}",
                f"WEBPUSH_VAPID_PUBLIC_KEY={base64url(public_bytes)}",
                f"WEBPUSH_VAPID_SUBJECT={options['subject']}",
                f"NOTIFICATION_TOKEN_ENCRYPTION_KEY={Fernet.generate_key().decode('ascii')}",
                "KAKAO_REST_API_KEY=",
                "KAKAO_CLIENT_SECRET=",
                "KAKAO_REDIRECT_URI=https://staff.silvermedical.kr/staff/notifications/kakao/callback/",
                "",
            ]
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(contents, encoding="utf-8")
        os.chmod(output, 0o600)
        self.stdout.write(self.style.SUCCESS(f"Notification secrets written to {output}"))
