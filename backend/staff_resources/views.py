from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from .models import StaffResource


@staff_member_required
@require_safe
def resource_list(request):
    category = request.GET.get("category", "").strip()
    resources = StaffResource.objects.filter(is_published=True).select_related("created_by")
    valid_categories = {value for value, _ in StaffResource.Category.choices}
    if category in valid_categories:
        resources = resources.filter(category=category)
    else:
        category = ""
    page = Paginator(resources, 12).get_page(request.GET.get("page"))
    return render(
        request,
        "staff_resources/list.html",
        {
            "page": page,
            "categories": StaffResource.Category.choices,
            "selected_category": category,
        },
    )


@staff_member_required
@require_safe
def resource_detail(request, slug):
    resource = get_object_or_404(
        StaffResource.objects.filter(is_published=True).select_related("created_by"),
        slug=slug,
    )
    return render(request, "staff_resources/detail.html", {"resource": resource})


@staff_member_required
@require_safe
def resource_download(request, slug):
    resource = get_object_or_404(StaffResource.objects.filter(is_published=True), slug=slug)
    if not resource.attachment:
        raise Http404
    return FileResponse(
        resource.attachment.open("rb"),
        as_attachment=True,
        filename=Path(resource.attachment.name).name,
    )
