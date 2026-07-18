from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .models import BenefitSchedule, FacilityFeeSettings


@never_cache
@require_GET
def published_schedules(request):
    schedules = BenefitSchedule.objects.filter(is_published=True).order_by("year")
    facility_fees = FacilityFeeSettings.objects.filter(pk=1).first()
    if facility_fees is None:
        facility_fees = FacilityFeeSettings(meal_price=3500, snack_price=1000)
    response = JsonResponse(
        {
            "food": {
                "meal": facility_fees.meal_price,
                "snack": facility_fees.snack_price,
            },
            "schedules": [item.as_public_data() for item in schedules],
        }
    )
    response["Cache-Control"] = "no-store, max-age=0"
    return response
