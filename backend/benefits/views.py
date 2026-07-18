from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .models import BenefitSchedule


@never_cache
@require_GET
def published_schedules(request):
    schedules = BenefitSchedule.objects.filter(is_published=True).order_by("year")
    response = JsonResponse({"schedules": [item.as_public_data() for item in schedules]})
    response["Cache-Control"] = "no-store, max-age=0"
    return response
