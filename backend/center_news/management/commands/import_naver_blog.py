import re
from io import BytesIO
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import requests
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from center_news.models import Post, PostImage
from center_news.naver_import import parse_post_list, render_imported_body


POST_LIST_URL = "https://blog.naver.com/PostList.naver"
BLOG_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
MAX_IMAGE_SIZE = 8 * 1024 * 1024
ALLOWED_IMAGE_HOSTS = {"postfiles.pstatic.net", "blogfiles.pstatic.net"}
MAX_IMAGES_PER_POST = 150


class Command(BaseCommand):
    help = "네이버 블로그 글을 센터 이야기의 작성 중 게시글로 가져옵니다."

    def add_arguments(self, parser):
        parser.add_argument("--blog-id", default="sil3307")
        parser.add_argument("--cutoff", default="2025-07-16", help="YYYY-MM-DD, 해당 날짜 포함")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--username", default="silveradmin")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-images", action="store_true")
        parser.add_argument(
            "--refresh-content",
            action="store_true",
            help="기존 글의 본문도 네이버 원문의 문단·사진 순서로 다시 구성합니다.",
        )

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

        existing_posts = {
            post.naver_blog_url: post
            for post in Post.objects.filter(
                naver_blog_url__in=[item.source_url for item in candidates]
            )
        }
        new_posts = [item for item in candidates if item.source_url not in existing_posts]

        self.stdout.write(
            f"대상 {len(candidates)}개 / 이미 등록됨 {len(candidates) - len(new_posts)}개 / 새 글 {len(new_posts)}개"
        )
        for item in candidates:
            mode = "새 글" if item.source_url not in existing_posts else "사진 동기화"
            self.stdout.write(
                f"- {item.published_at:%Y-%m-%d} | {mode} | 사진 {len(item.image_urls)}장 | {item.title}"
            )

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("미리보기만 완료했습니다. 데이터는 변경하지 않았습니다."))
            return

        author = self._find_author(options["username"])
        created = 0
        synchronized = 0
        cover_added = 0
        gallery_added = 0
        image_skipped = 0
        for item in candidates:
            with transaction.atomic():
                post = existing_posts.get(item.source_url)
                is_new = post is None
                if is_new:
                    post = Post(
                        category=Post.Category.STORY,
                        title=item.title,
                        summary=item.summary,
                        body="",
                        body_format=Post.BodyFormat.RICH,
                        youtube_url=item.youtube_url,
                        naver_blog_url=item.source_url,
                        status=Post.Status.DRAFT,
                        published_at=timezone.make_aware(item.published_at),
                        created_by=author,
                        updated_by=author,
                    )

                added_for_post = 0
                cover_added_for_post = False
                image_urls = item.image_urls[:MAX_IMAGES_PER_POST]
                if image_urls and not options["skip_images"] and not post.cover_image:
                    try:
                        image_content, image_name = self._download_image(
                            session,
                            image_urls[0],
                            f"naver-{item.log_no}-cover",
                        )
                        image_content.name = image_name
                        post.cover_image = image_content
                        post.image_alt = f"{item.title} 관련 대표 사진"
                        cover_added += 1
                        cover_added_for_post = True
                    except (requests.RequestException, ValueError) as exc:
                        image_skipped += 1
                        self.stderr.write(
                            self.style.WARNING(f"대표 사진 건너뜀 {item.log_no}: {exc}")
                        )

                if is_new:
                    post.save()
                    created += 1
                elif cover_added_for_post:
                    post.updated_by = author
                    post.save(
                        update_fields=["cover_image", "image_alt", "updated_by", "updated_at"]
                    )
                elif post.cover_image and not post.image_alt:
                    post.image_alt = f"{item.title} 관련 대표 사진"
                    post.updated_by = author
                    post.save(update_fields=["image_alt", "updated_by", "updated_at"])

                gallery_by_source = {
                    image.source_url: image
                    for image in post.gallery_images.exclude(source_url="")
                }
                if not options["skip_images"]:
                    for index, image_url in enumerate(image_urls, start=1):
                        sort_order = index * 10
                        if image_url in gallery_by_source:
                            gallery_image = gallery_by_source[image_url]
                            if gallery_image.sort_order != sort_order:
                                gallery_image.sort_order = sort_order
                                gallery_image.save(update_fields=["sort_order"])
                            continue
                        try:
                            image_content, image_name = self._download_image(
                                session,
                                image_url,
                                f"naver-{item.log_no}-{index}",
                            )
                            gallery_image = PostImage(
                                post=post,
                                image_alt=f"{item.title} 관련 사진 {index}",
                                sort_order=sort_order,
                                source_url=image_url,
                            )
                            image_content.name = image_name
                            gallery_image.image = image_content
                            gallery_image.save()
                            gallery_by_source[image_url] = gallery_image
                            added_for_post += 1
                            gallery_added += 1
                        except (requests.RequestException, ValueError) as exc:
                            image_skipped += 1
                            self.stderr.write(
                                self.style.WARNING(
                                    f"추가 사진 건너뜀 {item.log_no}-{index}: {exc}"
                                )
                            )

                refresh_content = is_new or options["refresh_content"]
                if refresh_content:
                    local_image_urls = {
                        source_url: image.image.url
                        for source_url, image in gallery_by_source.items()
                        if image.image
                    }
                    post.body = render_imported_body(
                        item.body_html,
                        image_urls,
                        local_image_urls,
                    )
                    post.body_format = Post.BodyFormat.RICH
                    post.updated_by = author
                    post.save(update_fields=["body", "body_format", "updated_by", "updated_at"])

                total_added_for_post = added_for_post + int(cover_added_for_post)
                if not is_new and total_added_for_post:
                    synchronized += 1
                self._record_admin_history(
                    post,
                    author,
                    is_new,
                    total_added_for_post,
                    refresh_content,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"임시저장 새 글 {created}개, 기존 글 사진 보충 {synchronized}개, "
                f"대표사진 추가 {cover_added}장, 추가사진 저장 {gallery_added}장, "
                f"사진 건너뜀 {image_skipped}장. 공개 전 반드시 모든 사진을 확인해 주세요."
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

    def _record_admin_history(self, post, author, is_new, added_images, refreshed_content=False):
        if not author:
            return
        content_type = ContentType.objects.get_for_model(Post)
        history = LogEntry.objects.filter(
            content_type=content_type,
            object_id=str(post.pk),
        )
        if not is_new and not added_images and not refreshed_content and history.exists():
            return

        if is_new:
            message = "네이버 블로그에서 임시저장 글로 가져왔습니다."
            action_flag = ADDITION
        elif added_images or refreshed_content:
            details = []
            if added_images:
                details.append(f"사진 {added_images}장 추가")
            if refreshed_content:
                details.append("글·사진 순서 재구성")
            message = "네이버 블로그에서 " + ", ".join(details) + " 작업을 완료했습니다."
            action_flag = CHANGE
        else:
            message = "네이버 블로그 가져오기 상태를 확인했습니다."
            action_flag = CHANGE
        LogEntry.objects.log_action(
            user_id=author.pk,
            content_type_id=content_type.pk,
            object_id=post.pk,
            object_repr=str(post),
            action_flag=action_flag,
            change_message=message,
        )

    def _download_image(self, session, image_url, file_stem):
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
        safe_stem = re.sub(r"[^A-Za-z0-9_-]", "-", file_stem).strip("-") or "naver-image"
        if extension in {".jpg", ".jpeg", ".png", ".webp"}:
            return ContentFile(response.content), f"{safe_stem}{extension}"

        # 움직이는 GIF 등은 첫 화면을 대표 사진용 PNG로 변환합니다.
        with Image.open(BytesIO(response.content)) as source:
            frame = source.convert("RGBA" if "transparency" in source.info else "RGB")
            output = BytesIO()
            frame.save(output, format="PNG")
        return ContentFile(output.getvalue()), f"{safe_stem}.png"
