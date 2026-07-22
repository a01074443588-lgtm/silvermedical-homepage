import html
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup


BLOG_POST_URL = "https://blog.naver.com/{blog_id}/{log_no}"
WHITESPACE_PATTERN = re.compile(r"\s+")
YOUTUBE_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s\"'<>\\]+",
    re.IGNORECASE,
)


TITLE_REWRITES = {
    "224338474405": "고기 굽는 향기로 더 즐거워진 저녁, 삼겹살 파티",
    "224311025655": "‘저녁 차리러 가야 해요’, 어르신 마음속에 남아 있는 가족의 밥상",
    "224281978376": "웃음으로 함께한 실버메디컬 어버이날",
    "224269691225": "요양원은 병원이 아닙니다: 입소 전 알아둘 현실적인 돌봄의 기준",
    "224255367382": "요양원 입소 상담 전, 무엇을 준비해야 할까요?",
    "224255349913": "요양원과 요양병원, 우리 부모님께 맞는 선택은 무엇일까요?",
    "224248857037": "집에서의 돌봄이 한계에 다다를 때 살펴볼 신호",
    "224242890659": "우리 가족에게 맞는 돌봄 서비스는 무엇일까요?",
    "224228725229": "어르신 노래 선곡, 10년 단위로 살펴보기",
    "224220922614": "복지용구, 무엇을 빌리고 무엇을 구매해야 할까요?",
}


@dataclass(frozen=True)
class NaverBlogPost:
    log_no: str
    title: str
    original_title: str
    published_at: datetime
    body: str
    summary: str
    source_url: str
    image_url: str = ""
    youtube_url: str = ""


def normalize_text(value):
    value = value.replace("\u200b", " ").replace("\ufeff", " ").replace("\xa0", " ")
    return WHITESPACE_PATTERN.sub(" ", value).strip()


def rewrite_title(log_no, title):
    if log_no in TITLE_REWRITES:
        return TITLE_REWRITES[log_no]

    cleaned = normalize_text(title).strip('"“”')
    cleaned = re.sub(r"^청주\s+요양원\s+실버메디컬복지센터\s*", "", cleaned)
    cleaned = re.sub(r"\s*[🥓🍚🌸🍶🏡📝😞🎶🛏️🦽]+\s*$", "", cleaned).strip()
    cleaned = cleaned.replace(" - ", ": ")
    return cleaned[:120]


def build_summary(paragraphs, fallback_title):
    candidates = [line for line in paragraphs if line and not line.startswith("#")]
    summary = " ".join(candidates[:2]) or fallback_title
    if len(summary) <= 220:
        return summary
    shortened = summary[:217].rsplit(" ", 1)[0].rstrip(" ,.:;-")
    return f"{shortened}..."


def _parse_published_at(value):
    normalized = normalize_text(value)
    for pattern in ("%Y. %m. %d. %H:%M", "%Y. %m. %d. %H:%M:%S"):
        try:
            return datetime.strptime(normalized, pattern)
        except ValueError:
            continue
    raise ValueError(f"지원하지 않는 네이버 작성일 형식입니다: {normalized}")


def _extract_body_paragraphs(container):
    paragraphs = []
    for paragraph in container.select(".se-text-paragraph"):
        text = normalize_text(paragraph.get_text(" ", strip=True))
        if not text or (paragraphs and paragraphs[-1] == text):
            continue
        if paragraph.find_parent("li"):
            text = f"• {text}"
        elif paragraph.find(["b", "strong"]) and len(text) <= 120:
            text = f"## {text}"
        paragraphs.append(text)
    return paragraphs


def _extract_image_url(container):
    candidates = []
    for image in container.select("img.se-image-resource"):
        image_url = image.get("data-lazy-src") or image.get("src") or ""
        if not image_url:
            continue
        try:
            width = int(image.get("data-width") or 0)
        except (TypeError, ValueError):
            width = 0
        candidates.append((image_url, width))

    if not candidates:
        return ""
    # Keep the article's visual order while ignoring tiny placeholders.
    # Some SmartEditor images omit data-width, so fall back to the best URL.
    selected_url = next(
        (image_url for image_url, width in candidates if width >= 320),
        max(candidates, key=lambda candidate: candidate[1])[0],
    )
    parts = urlsplit(selected_url)
    # Query-free Naver image URLs return a tiny 100px thumbnail. Request the
    # largest consistently available SmartEditor rendition instead.
    query = "type=w966" if parts.netloc.endswith("pstatic.net") else parts.query
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def _extract_youtube_url(container):
    iframe = container.select_one('iframe[src*="youtube.com/embed/"]')
    if iframe:
        video_id = iframe.get("src", "").split("/embed/", 1)[-1].split("?", 1)[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

    for script in container.select("script.__se_module_data"):
        module_data = " ".join(
            filter(
                None,
                [
                    script.get("data-module", ""),
                    script.get("data-module-v2", ""),
                    script.get_text(" ", strip=True),
                ],
            )
        )
        decoded = html.unescape(module_data).replace("\\/", "/")
        match = YOUTUBE_URL_PATTERN.search(decoded)
        if match:
            url = match.group(0).rstrip(".,;)")
            if "/embed/" in url:
                video_id = url.split("/embed/", 1)[-1].split("?", 1)[0]
                return f"https://www.youtube.com/watch?v={video_id}"
            return url
    return ""


def parse_post_list(html_text, blog_id):
    soup = BeautifulSoup(html_text, "html.parser")
    posts = []

    for post_node in soup.select('div[id^="post-view"]'):
        log_no = post_node.get("id", "").removeprefix("post-view")
        title_node = post_node.select_one(".se-title-text")
        date_node = post_node.select_one(".se_publishDate")
        content_node = post_node.select_one(".se-main-container")
        if not (log_no.isdigit() and title_node and date_node and content_node):
            continue

        original_title = normalize_text(title_node.get_text(" ", strip=True))
        title = rewrite_title(log_no, original_title)
        paragraphs = _extract_body_paragraphs(content_node)
        posts.append(
            NaverBlogPost(
                log_no=log_no,
                title=title,
                original_title=original_title,
                published_at=_parse_published_at(date_node.get_text(" ", strip=True)),
                body="\n\n".join(paragraphs),
                summary=build_summary(paragraphs, title),
                source_url=BLOG_POST_URL.format(blog_id=blog_id, log_no=log_no),
                image_url=_extract_image_url(content_node),
                youtube_url=_extract_youtube_url(content_node),
            )
        )

    return posts
