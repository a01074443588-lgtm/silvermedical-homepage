import center_news.models
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Post",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("notice", "공지사항"), ("story", "센터 이야기"), ("video", "영상 소식")], max_length=20, verbose_name="분류")),
                ("title", models.CharField(max_length=120, verbose_name="제목")),
                ("slug", models.SlugField(allow_unicode=True, blank=True, max_length=150, unique=True, verbose_name="게시물 주소")),
                ("summary", models.CharField(help_text="목록과 검색 결과에 표시할 내용을 2~3문장 이내로 작성해 주세요.", max_length=220, verbose_name="목록용 짧은 설명")),
                ("body", models.TextField(blank=True, help_text="문단 사이에 빈 줄을 넣으면 공개 화면에서도 문단이 나뉩니다.", verbose_name="본문")),
                ("cover_image", models.ImageField(blank=True, help_text="JPG, PNG, WebP 형식의 8MB 이하 사진을 사용해 주세요. 자동으로 화면용 크기로 줄어듭니다.", upload_to=center_news.models.post_image_path, validators=[django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), center_news.models.validate_image_size], verbose_name="대표 사진")),
                ("image_alt", models.CharField(blank=True, help_text="사진을 보지 못하는 이용자도 내용을 이해할 수 있도록 간단히 설명해 주세요.", max_length=160, verbose_name="사진 설명")),
                ("youtube_url", models.URLField(blank=True, help_text="youtube.com 또는 youtu.be 영상 주소를 입력하면 홈페이지에서 바로 재생됩니다.", verbose_name="유튜브 주소")),
                ("naver_blog_url", models.URLField(blank=True, help_text="관련 블로그 글이 있을 때만 입력해 주세요. 새 창으로 연결됩니다.", verbose_name="네이버 블로그 원문 주소")),
                ("is_pinned", models.BooleanField(default=False, verbose_name="목록 상단 고정")),
                ("status", models.CharField(choices=[("draft", "작성 중"), ("published", "공개")], default="draft", max_length=20, verbose_name="공개 상태")),
                ("published_at", models.DateTimeField(blank=True, help_text="미래 시각을 선택하면 해당 시각부터 자동으로 공개됩니다.", null=True, verbose_name="공개 시각")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="작성 시각")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="수정 시각")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_center_posts", to=settings.AUTH_USER_MODEL, verbose_name="작성자")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_center_posts", to=settings.AUTH_USER_MODEL, verbose_name="마지막 수정자")),
            ],
            options={
                "verbose_name": "센터소식 게시글",
                "verbose_name_plural": "센터소식 게시글",
                "ordering": ["-is_pinned", "-published_at", "-created_at"],
            },
        ),
    ]
