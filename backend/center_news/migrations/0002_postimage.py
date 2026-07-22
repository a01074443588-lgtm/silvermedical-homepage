import center_news.models
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("center_news", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="PostImage",
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
                    "image",
                    models.ImageField(
                        help_text="JPG, PNG, WebP 형식의 8MB 이하 사진을 사용해 주세요.",
                        upload_to=center_news.models.post_gallery_image_path,
                        validators=[
                            django.core.validators.FileExtensionValidator(
                                ["jpg", "jpeg", "png", "webp"]
                            ),
                            center_news.models.validate_image_size,
                        ],
                        verbose_name="추가 사진",
                    ),
                ),
                (
                    "image_alt",
                    models.CharField(
                        help_text="사진을 보지 못하는 이용자도 이해할 수 있도록 내용을 설명해 주세요.",
                        max_length=160,
                        verbose_name="사진 설명",
                    ),
                ),
                (
                    "caption",
                    models.CharField(
                        blank=True,
                        max_length=200,
                        verbose_name="화면에 표시할 설명",
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(
                        db_index=True,
                        default=0,
                        help_text="작은 숫자부터 먼저 표시됩니다.",
                        verbose_name="표시 순서",
                    ),
                ),
                (
                    "source_url",
                    models.URLField(
                        blank=True,
                        editable=False,
                        max_length=1000,
                        verbose_name="원본 사진 주소",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="등록 시각")),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gallery_images",
                        to="center_news.post",
                        verbose_name="게시글",
                    ),
                ),
            ],
            options={
                "verbose_name": "게시글 추가 사진",
                "verbose_name_plural": "게시글 추가 사진",
                "ordering": ["sort_order", "pk"],
            },
        ),
    ]
