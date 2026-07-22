import re
from io import BytesIO
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import requests
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from center_news.models import Post
from center_news.naver_import import parse_post_list


POST_LIST_URL = "https://blog.naver.com/PostList.naver"
BLOG_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
MAX_IMAGE_SIZE = 8 * 1024 * 1024
ALLOWED_IMAGE_HOSTS = {"postfiles.pstatic.net", "blogfiles.pstatic.net"}


class Command(BaseCommand):
    help = "네이버 블로그 글을 센터 이야기의 작성 중 게시글로 가져옵니다."

    def add_arguments(self, parser):
        parser.add_argument("--blog-id", default="sil3307")
        parser.add_argument("--cutoff", default="2025-07-16", help="YYYY-MM-DD, 해당 날짜 포함")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--username", default="silveradmin")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-images", action="store_true")

    def handle(self, *args, **options):
        blog_id = options["blog_id"].strip()
        if not BLOG_ID_PATTERN.fullmatch(blog_id):
            raise CommandError("블로그 아이디 형식이 올바르지 않습니다.")
        try:
            cutoff = date.fromisoformat(options["cutoff"])
        except ValueError as exc:
            raise CommandError("기준일은 YYYY-MM-DD 형식으로 입력해 주세요.") from exc

        limit = options["limit"]
        if limit < 1 or limit > 100:
            raise CommandError("한 번에 가져올 글 수는 1~100개로 지정해 주세요.")

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
                ),
                "Referer": f"https://blog.naver.com/{blog_id}",
            }
        )

        candidates = self._collect_candidates(session, blog_id, cutoff, limit)
        if not candidates:
            self.stdout.write(self.style.WARNING("기준일 이후에 가져올 새 글이 없습니다."))
            return

        existing_urls = set(
            Post.objects.filter(naver_blog_url__in=[post.source_url for post in candidates]).values_list(
                "naver_blog_url", flat=True
            )
        )
        new_posts = [post for post in candidates if post.source_url not in existing_urls]

        self.stdout.write(
            f"대상 {len(candidates)}개 / 이미 등록됨 {len(candidates) - len(new_posts)}개 / 새 글 {len(new_posts)}개"
        )
        for item in new_posts:
            self.stdout.write(f"- {item.published_at:%Y-%m-%d} | {item.title}")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("미리보기만 완료했습니다. 데이터는 변경하지 않았습니다."))
            return

        author = self._find_author(options["username"])
        created = 0
        image_skipped = 0
        for item in new_posts:
            image_content = None
            image_name = ""
            if item.image_url and not options["skip_images"]:
                try:
                    image_content, image_name = self._download_image(session, item.image_url, item.log_no)
                except (requests.RequestException, ValueError) as exc:
                    image_skipped += 1
                    self.stderr.write(self.style.WARNING(f"사진 건너뜀 {item.log_no}: {exc}"))

            with transaction.atomic():
                post = Post(
                    category=Post.Category.STORY,
                    title=item.title,
                    summary=item.summary,
                    body=item.body,
                    youtube_url=item.youtube_url,
                    naver_blog_url=item.source_url,
                    status=Post.Status.DRAFT,
                    published_at=timezone.make_aware(item.published_at),
                    created_by=author,
                    updated_by=author,
                )
                if image_content:
                    post.cover_image.save(image_name, image_content, save=False)
                    post.image_alt = f"{item.title} 관련 사진"
                post.save()
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"임시저장 {created}개를 가져왔습니다. 사진 건너뜀 {image_skipped}개. 공개 전 반드시 사진을 확인해 주세요."
            )
        )

    def _collect_candidates(self, session, blog_id, cutoff, limit):
        candidates = []
        for current_page in range(1, 51):
            response = session.get(
                POST_LIST_URL,
                params={
                    "blogId": blog_id,
                    "categoryNo": 0,
                    "from": "postList",
                    "currentPage": current_page,
                },
                timeout=30,
            )
            response.raise_for_status()
            posts = parse_post_list(response.text, blog_id)
            if not posts:
                break

            reached_cutoff = False
            for post in posts:
                if post.published_at.date() < cutoff:
                    reached_cutoff = True
                    continue
                candidates.append(post)
                if len(candidates) >= limit:
                    return candidates
            if reached_cutoff:
                break
        return candidates

    def _find_author(self, username):
        users = get_user_model().objects
        author = users.filter(username=username).first()
        if author:
            return author
        return users.filter(is_superuser=True).order_by("pk").first()

    def _download_image(self, session, image_url, log_no):
        image_host = urlsplit(image_url).hostname or ""
        if image_host not in ALLOWED_IMAGE_HOSTS:
            raise ValueError("허용된 네이버 사진 주소가 아닙니다.")
        response = session.get(image_url, timeout=30)
        response.raise_for_status()
        if len(response.content) > MAX_IMAGE_SIZE:
            raise ValueError("8MB를 초과합니다.")

        try:
            with Image.open(BytesIO(response.content)) as source:
                image_format = (source.format or "").upper()
                source.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("사진 파일을 판독할 수 없습니다.") from exc

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        extensions = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        format_extensions = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
        extension = (
            format_extensions.get(image_format)
            or extensions.get(content_type)
            or Path(urlsplit(image_url).path).suffix.lower()
        )
        if extension in {".jpg", ".jpeg", ".png", ".webp"}:
            return ContentFile(response.content), f"naver-{log_no}{extension}"

        # 움직이는 GIF 등은 첫 화면을 대표 사진용 PNG로 변환합니다.
        with Image.open(BytesIO(response.content)) as source:
            frame = source.convert("RGBA" if "transparency" in source.info else "RGB")
            output = BytesIO()
            frame.save(output, format="PNG")
        return ContentFile(output.getvalue()), f"naver-{log_no}.png"
