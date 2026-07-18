import django.core.validators
from django.db import migrations, models


def split_facility_fees(apps, schema_editor):
    BenefitSchedule = apps.get_model("benefits", "BenefitSchedule")
    FacilityFeeSettings = apps.get_model("benefits", "FacilityFeeSettings")
    latest = BenefitSchedule.objects.order_by("-year").first()
    FacilityFeeSettings.objects.update_or_create(
        pk=1,
        defaults={
            "meal_price": latest.meal_price if latest else 3500,
            "snack_price": latest.snack_price if latest else 1000,
        },
    )


def restore_facility_fees(apps, schema_editor):
    BenefitSchedule = apps.get_model("benefits", "BenefitSchedule")
    FacilityFeeSettings = apps.get_model("benefits", "FacilityFeeSettings")
    settings = FacilityFeeSettings.objects.filter(pk=1).first()
    if settings:
        BenefitSchedule.objects.update(
            meal_price=settings.meal_price,
            snack_price=settings.snack_price,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("benefits", "0002_seed_2026_schedule"),
    ]

    operations = [
        migrations.CreateModel(
            name="FacilityFeeSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "meal_price",
                    models.PositiveIntegerField(
                        help_text="현재 기관에서 적용하는 식사 1끼 금액을 입력해 주세요.",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="식사 1끼",
                    ),
                ),
                (
                    "snack_price",
                    models.PositiveIntegerField(
                        help_text="현재 기관에서 적용하는 간식 1회 금액을 입력해 주세요.",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="간식 1회",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="수정 시각")),
            ],
            options={
                "verbose_name": "현재 식사·간식비 설정",
                "verbose_name_plural": "현재 식사·간식비 설정",
            },
        ),
        migrations.AlterField(
            model_name="benefitschedule",
            name="meal_price",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name="식사 1끼",
            ),
        ),
        migrations.AlterField(
            model_name="benefitschedule",
            name="snack_price",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name="간식 1회",
            ),
        ),
        migrations.RunPython(split_facility_fees, restore_facility_fees),
        migrations.RemoveField(model_name="benefitschedule", name="meal_price"),
        migrations.RemoveField(model_name="benefitschedule", name="snack_price"),
        migrations.AlterModelOptions(
            name="benefitschedule",
            options={
                "ordering": ["-year"],
                "verbose_name": "연도별 장기요양 급여수가",
                "verbose_name_plural": "연도별 장기요양 급여수가",
            },
        ),
        migrations.AlterField(
            model_name="benefitschedule",
            name="year",
            field=models.PositiveSmallIntegerField(
                help_text="기존 연도를 연 뒤 화면 아래의 '새로 저장'을 사용하면 다음 연도 자료를 쉽게 만들 수 있습니다.",
                unique=True,
                validators=[
                    django.core.validators.MinValueValidator(2020),
                    django.core.validators.MaxValueValidator(2100),
                ],
                verbose_name="기준연도",
            ),
        ),
    ]
