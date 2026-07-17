from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Consultation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference_code", models.CharField(blank=True, editable=False, max_length=20, unique=True, verbose_name="접수번호")),
                ("category", models.CharField(choices=[("nursing_home", "요양원 입소"), ("day_care", "주간보호"), ("home_care", "방문요양"), ("home_bath", "방문목욕"), ("short_stay", "단기보호"), ("integrated", "통합재가"), ("other", "기타 상담")], max_length=20, verbose_name="상담 종류")),
                ("guardian_name", models.CharField(max_length=30, verbose_name="보호자 성명")),
                ("phone", models.CharField(max_length=20, verbose_name="연락처")),
                ("preferred_contact_time", models.CharField(choices=[("morning", "오전 9시~12시"), ("afternoon", "오후 1시~5시"), ("evening", "오후 5시 이후"), ("anytime", "시간 관계없음")], max_length=20, verbose_name="연락 희망 시간")),
                ("message", models.TextField(max_length=2000, verbose_name="상담 내용")),
                ("status", models.CharField(choices=[("new", "신규 접수"), ("in_progress", "상담 중"), ("completed", "상담 완료")], default="new", max_length=20, verbose_name="진행 상태")),
                ("staff_note", models.TextField(blank=True, max_length=3000, verbose_name="직원 메모")),
                ("consent_version", models.CharField(default="2026-07", max_length=20, verbose_name="동의문 버전")),
                ("privacy_agreed_at", models.DateTimeField(verbose_name="개인정보 동의 시각")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="접수 시각")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="수정 시각")),
                ("completed_at", models.DateTimeField(blank=True, null=True, verbose_name="상담 완료 시각")),
            ],
            options={
                "verbose_name": "상담",
                "verbose_name_plural": "상담 접수함",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["status", "-created_at"], name="consult_status_created_idx"),
                    models.Index(fields=["category", "-created_at"], name="consult_category_created_idx"),
                ],
            },
        )
    ]
