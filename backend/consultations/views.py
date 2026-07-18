from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ConsultationForm
from staff_notifications.services import safe_enqueue_consultation_notifications


def no_store(response):
    response["Cache-Control"] = "no-store, private, max-age=0"
    response["Pragma"] = "no-cache"
    return response


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@never_cache
@require_http_methods(["GET", "POST"])
def create_consultation(request):
    if request.method == "POST" and request.POST.get("website"):
        return HttpResponse(status=204)

    form = ConsultationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        consultation = form.save(commit=False)
        consultation.privacy_agreed_at = timezone.now()
        consultation.save()
        transaction.on_commit(
            lambda consultation_id=consultation.pk: safe_enqueue_consultation_notifications(
                consultation_id
            )
        )

        request.session.cycle_key()
        request.session["consultation_receipt"] = {
            "reference_code": consultation.reference_code,
            "category": consultation.get_category_display(),
            "preferred_contact_time": consultation.get_preferred_contact_time_display(),
        }
        return redirect("consultations:success")

    return no_store(render(request, "consultations/form.html", {"form": form}))


@never_cache
@require_GET
def consultation_success(request):
    receipt = request.session.get("consultation_receipt")
    if not receipt:
        return redirect("consultations:create")
    return no_store(render(request, "consultations/success.html", {"receipt": receipt}))
