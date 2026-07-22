from mimetypes import guess_type
from pathlib import Path

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils._os import safe_join
from django.views.decorators.http import require_safe

from .models import Post, PostImage


@require_safe
def post_list(request):
    category = request.GET.get("category", "").strip()
    posts = Post.objects.published().select_related("created_by")
    valid_categories = {value for value, _ in Post.Category.choices}
    if category in valid_categories:
        posts = posts.filter(category=category)
    else:
        category = ""

    page = Paginator(posts, 9).get_page(request.GET.get("page"))
    return render(
        request,
        "center_news/list.html",
        {
            "page": page,
            "selected_category": category,
            "categories": Post.Category.choices,
        },
    )


@require_safe
def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.published().select_related("created_by").prefetch_related("gallery_images"),
        slug=slug,
    )
    category = request.GET.get("category", "").strip()
    valid_categories = {value for value, _ in Post.Category.choices}
    if category not in valid_categories:
        category = ""

    navigation_posts = Post.objects.published()
    if category:
        navigation_posts = navigation_posts.filter(category=category)
    previous_post = (
        navigation_posts.filter(
            Q(published_at__lt=post.published_at)
            | Q(published_at=post.published_at, pk__lt=post.pk)
        )
        .order_by("-published_at", "-pk")
        .first()
    )
    next_post = (
        navigation_posts.filter(
            Q(published_at__gt=post.published_at)
            | Q(published_at=post.published_at, pk__gt=post.pk)
        )
        .order_by("published_at", "pk")
        .first()
    )

    page_number = request.GET.get("page", "1")
    if not page_number.isdigit() or int(page_number) < 1:
        page_number = "1"
    list_query = []
    if category:
        list_query.append(f"category={category}")
    if page_number != "1":
        list_query.append(f"page={page_number}")
    list_url = reverse("center_news:list")
    if list_query:
        list_url = f"{list_url}?{'&'.join(list_query)}"

    related_posts = (
        Post.objects.published()
        .filter(category=post.category)
        .exclude(pk=post.pk)[:3]
    )
    return render(
        request,
        "center_news/detail.html",
        {
            "post": post,
            "related_posts": related_posts,
            "previous_post": previous_post,
            "next_post": next_post,
            "selected_category": category,
            "page_number": page_number,
            "list_url": list_url,
        },
    )


@require_safe
def latest_posts(request):
    posts = Post.objects.published().order_by("-published_at")[:3]
    items = [
        {
            "category": post.get_category_display(),
            "title": post.title,
            "summary": post.summary,
            "url": post.get_absolute_url(),
            "image_url": post.cover_image.url if post.cover_image else "",
            "image_alt": post.image_alt,
            "published_at": timezone.localtime(post.published_at).date().isoformat(),
            "has_video": bool(post.youtube_id),
        }
        for post in posts
    ]
    response = JsonResponse({"posts": items})
    response["Cache-Control"] = "public, max-age=60"
    return response


@require_safe
def public_media(request, path):
    is_public_image = (
        Post.objects.published().filter(cover_image=path).exists()
        or PostImage.objects.filter(
            image=path,
            post__status=Post.Status.PUBLISHED,
            post__published_at__isnull=False,
            post__published_at__lte=timezone.now(),
        ).exists()
    )
    is_staff = request.user.is_authenticated and request.user.is_staff
    if not is_public_image and not is_staff:
        raise Http404
    try:
        file_path = Path(safe_join(settings.MEDIA_ROOT, path))
    except Exception as exc:
        raise Http404 from exc
    if not file_path.is_file():
        raise Http404

    response = FileResponse(
        file_path.open("rb"),
        content_type=guess_type(file_path.name)[0] or "application/octet-stream",
    )
    response["Cache-Control"] = (
        "public, max-age=604800" if is_public_image else "private, no-store, max-age=0"
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_safe
def news_sitemap(request):
    base_url = "https://silvermedical.kr"
    urls = [
        f"  <url><loc>{base_url}{reverse('center_news:list')}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
    ]
    for post in Post.objects.published().only("slug", "updated_at"):
        modified = timezone.localtime(post.updated_at).date().isoformat()
        urls.append(
            f"  <url><loc>{base_url}{post.get_absolute_url()}</loc><lastmod>{modified}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml; charset=utf-8")
