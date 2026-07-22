from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("center_news", "0002_postimage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="body",
            field=models.TextField(
                blank=True,
                help_text="완성 화면형 편집기에서 글과 사진을 원하는 순서로 배치합니다.",
                verbose_name="본문",
            ),
        ),
        migrations.AddField(
            model_name="post",
            name="body_format",
            field=models.CharField(
                choices=[("plain", "일반 본문"), ("rich", "완성 화면 편집")],
                default="plain",
                editable=False,
                max_length=10,
                verbose_name="본문 형식",
            ),
        ),
    ]
