import html
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag


BLOG_POST_URL = "https://blog.naver.com/{blog_id}/{log_no}"
WHITESPACE_PATTERN = re.compile(r"\s+")
YOUTUBE_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s\"'<>\\]+",
    re.IGNORECASE,
)
RELATED_READS_PATTERN = re.compile(r"(?:같이|함께)\s*읽으면\s*좋은\s*글")


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
    body_html: str = ""
    image_urls: tuple[str, ...] = ()
    youtube_url: str = ""

    @property
    def image_url(self):
        return self.image_urls[0] if self.image_urls else ""


def normalize_text(value):
    value = value.replace("\u200b", " ").replace("\ufeff", " ").replace("\xa0", " ")
    return WHITESPACE_PATTERN.sub(" ", value).strip()


def _is_related_reads_component(component):
    text = normalize_text(component.get_text(" ", strip=True))
    return bool(RELATED_READS_PATTERN.search(text))


def _content_components(container):
    components = container.select(":scope > .se-component")
    if not components:
        components = [node for node in container.children if isinstance(node, Tag)]
    return [component for component in components if not _is_related_reads_component(component)]


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
        component = paragraph.find_parent(class_=lambda classes: classes and "se-component" in classes)
        if component and _is_related_reads_component(component):
            continue
        text = normalize_text(paragraph.get_text(" ", strip=True))
        if not text or (paragraphs and paragraphs[-1] == text):
            continue
        if paragraph.find_parent("li"):
            text = f"• {text}"
        elif paragraph.find(["b", "strong"]) and len(text) <= 120:
            text = f"## {text}"
        paragraphs.append(text)
    return paragraphs


def _normalize_image_url(image_url):
    parts = urlsplit(image_url)
    query = "type=w966" if parts.netloc.endswith("pstatic.net") else parts.query
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def _extract_image_urls(container, components=None):
    candidates = []
    components = components if components is not None else _content_components(container)
    images = []
    for component in components:
        if component.name == "img" and "se-image-resource" in component.get("class", []):
            images.append(component)
        else:
            images.extend(component.select("img.se-image-resource"))

    for image in images:
        image_url = image.get("data-lazy-src") or image.get("src") or ""
        if not image_url:
            continue
        try:
            width = int(image.get("data-width") or 0)
        except (TypeError, ValueError):
            width = 0
        candidates.append((image_url, width))

    if not candidates:
        return ()

    # Keep every article photo in its visual order while excluding known tiny
    # placeholders. SmartEditor sometimes omits data-width, so those images are
    # retained and validated again when downloaded.
    eligible = [candidate for candidate in candidates if candidate[1] == 0 or candidate[1] >= 320]
    if not eligible:
        eligible = [max(candidates, key=lambda candidate: candidate[1])]

    image_urls = []
    seen = set()
    for image_url, _ in eligible:
        normalized_url = _normalize_image_url(image_url)
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        image_urls.append(normalized_url)
    return tuple(image_urls)


def _alignment_class(node):
    current = node
    while current and current is not node.parent.parent:
        classes = " ".join(current.get("class", [])) if isinstance(current, Tag) else ""
        style = current.get("style", "") if isinstance(current, Tag) else ""
        combined = f"{classes} {style}".lower()
        if "center" in combined:
            return " ql-align-center"
        if "right" in combined:
            return " ql-align-right"
        if "justify" in combined:
            return " ql-align-justify"
        current = current.parent
    return ""


def _paragraph_to_html(paragraph):
    text = normalize_text(paragraph.get_text(" ", strip=True))
    if not text:
        return ""
    escaped = html.escape(text)
    alignment = _alignment_class(paragraph)
    class_attribute = f' class="{alignment.strip()}"' if alignment else ""
    style_text = " ".join(
        [paragraph.get("style", "")]
        + [node.get("style", "") for node in paragraph.find_all(True)]
    ).lower()
    is_heading = bool(paragraph.find(["b", "strong"])) or "font-weight" in style_text
    if is_heading and len(text) <= 120:
        return f"<h2{class_attribute}>{escaped}</h2>"
    if paragraph.find_parent("li"):
        return f"<ul><li>{escaped}</li></ul>"
    return f"<p{class_attribute}>{escaped}</p>"


def _extract_rich_body(container):
    components = _content_components(container)
    image_urls = list(_extract_image_urls(container, components))
    eligible_images = set(image_urls)
    image_indexes = {url: index for index, url in enumerate(image_urls, start=1)}
    used_images = set()
    blocks = []

    for component in components:
        classes = set(component.get("class", []))
        if "se-horizontalLine" in classes:
            blocks.append("<hr>")
            continue

        component_images = []
        candidates = (
            [component]
            if component.name == "img" and "se-image-resource" in component.get("class", [])
            else component.select("img.se-image-resource")
        )
        for image_node in candidates:
            image_url = image_node.get("data-lazy-src") or image_node.get("src") or ""
            if not image_url:
                continue
            normalized_url = _normalize_image_url(image_url)
            if normalized_url not in eligible_images or normalized_url in used_images:
                continue
            used_images.add(normalized_url)
            component_images.append((normalized_url, normalize_text(image_node.get("alt", ""))))

        for image_url, alt_text in component_images:
            token = f"__NAVER_IMAGE_{image_indexes[image_url]}__"
            alt = html.escape(alt_text or "센터소식 사진", quote=True)
            blocks.append(
                f'<p class="ql-align-center"><img src="{token}" alt="{alt}"></p>'
            )
        if component_images:
            continue

        paragraphs = (
            [component]
            if "se-text-paragraph" in component.get("class", [])
            else component.select(".se-text-paragraph")
        )
        if paragraphs:
            blocks.extend(filter(None, (_paragraph_to_html(item) for item in paragraphs)))
            continue

        if "se-quotation" in classes:
            quote = normalize_text(component.get_text(" ", strip=True))
            if quote:
                blocks.append(f"<blockquote>{html.escape(quote)}</blockquote>")

    return "".join(blocks), tuple(image_urls)


def render_imported_body(body_html, image_urls, local_image_urls):
    rendered = body_html or ""
    for index, image_url in enumerate(image_urls, start=1):
        rendered = rendered.replace(
            f"__NAVER_IMAGE_{index}__",
            html.escape(local_image_urls.get(image_url, ""), quote=True),
        )

    soup = BeautifulSoup(rendered, "html.parser")
    for image in list(soup.find_all("img")):
        if not image.get("src"):
            parent = image.parent
            image.decompose()
            if parent and parent.name == "p" and not parent.get_text(strip=True) and not parent.find("img"):
                parent.decompose()
    return "".join(str(node) for node in soup.contents)


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
        body_html, image_urls = _extract_rich_body(content_node)
        posts.append(
            NaverBlogPost(
                log_no=log_no,
                title=title,
                original_title=original_title,
                published_at=_parse_published_at(date_node.get_text(" ", strip=True)),
                body="\n\n".join(paragraphs),
                summary=build_summary(paragraphs, title),
                source_url=BLOG_POST_URL.format(blog_id=blog_id, log_no=log_no),
                body_html=body_html,
                image_urls=image_urls,
                youtube_url=_extract_youtube_url(content_node),
            )
        )

    return posts
