from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse

from .models import BenefitSchedule, FacilityFeeSettings


@admin.register(FacilityFeeSettings)
class FacilityFeeSettingsAdmin(admin.ModelAdmin):
    list_display = ["meal_price", "snack_price", "updated_at"]
    readonly_fields = ["updated_at"]
    fieldsets = [
        (
            "현재 적용 식사·간식비",
            {
                "fields": [("meal_price", "snack_price"), "updated_at"],
                "description": "연도와 관계없이 계산기에 사용할 현재 기관 식사비와 간식비입니다.",
            },
        )
    ]

    def has_add_permission(self, request):
        return not FacilityFeeSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        settings = FacilityFeeSettings.current()
        return redirect(
            reverse(
                "admin:benefits_facilityfeesettings_change",
                args=[settings.pk],
            )
        )


@admin.register(BenefitSchedule)
class BenefitScheduleAdmin(admin.ModelAdmin):
    list_display = ["year", "effective_date", "publication_status", "updated_at"]
    list_filter = ["is_published"]
    search_fields = ["year", "source_note"]
    ordering = ["-year"]
    save_as = True
    readonly_fields = ["created_at", "updated_at"]
    actions = ["publish_selected", "unpublish_selected"]
    fieldsets = [
        (
            "기준연도와 공개 설정",
            {
                "fields": [("year", "effective_date"), "is_published", "source_note"],
                "description": "미래 연도 수가도 미리 입력해 공개할 수 있습니다. 공개하면 계산기에 '(예정)' 연도로 표시됩니다.",
            },
        ),
        (
            "본인부담률·감경률",
            {
                "fields": [
                    ("facility_standard_percent", "facility_discount40_percent", "facility_discount60_percent"),
                    ("home_standard_percent", "home_discount40_percent", "home_discount60_percent"),
                ]
            },
        ),
        (
            "재가급여 등급별 월 한도액",
            {
                "fields": [("home_limit_1", "home_limit_2", "home_limit_3", "home_limit_4", "home_limit_5")],
                "description": "1등급부터 5등급까지 순서대로 입력합니다.",
            },
        ),
        (
            "시설급여 등급별 1일 수가",
            {
                "fields": [("facility_rate_1", "facility_rate_2", "facility_rate_3", "facility_rate_4", "facility_rate_5")],
                "description": "1등급부터 5등급까지 시설급여 1일 수가를 입력합니다.",
            },
        ),
        (
            "주야간보호 시간·등급별 수가",
            {
                "fields": [
                    ("daycare_3_6_1", "daycare_3_6_2", "daycare_3_6_3", "daycare_3_6_4", "daycare_3_6_5"),
                    ("daycare_6_8_1", "daycare_6_8_2", "daycare_6_8_3", "daycare_6_8_4", "daycare_6_8_5"),
                    ("daycare_8_10_1", "daycare_8_10_2", "daycare_8_10_3", "daycare_8_10_4", "daycare_8_10_5"),
                    ("daycare_10_13_1", "daycare_10_13_2", "daycare_10_13_3", "daycare_10_13_4", "daycare_10_13_5"),
                    ("daycare_13_plus_1", "daycare_13_plus_2", "daycare_13_plus_3", "daycare_13_plus_4", "daycare_13_plus_5"),
                ],
                "description": "각 행은 이용시간 구간이며, 행 안에서는 1등급부터 5등급 순서입니다.",
            },
        ),
        (
            "방문요양 시간별 수가",
            {
                "fields": [
                    ("visit_30", "visit_60", "visit_90", "visit_120"),
                    ("visit_150", "visit_180", "visit_210", "visit_240"),
                ],
            },
        ),
        ("센터 요양보호사 예상급여 기준", {"classes": ["collapse"], "fields": [("regular_care_hourly_pay", "family60_hourly_pay", "family90_hourly_pay")]}),
        ("기록", {"classes": ["collapse"], "fields": [("created_at", "updated_at")]}),
    ]

    @admin.display(description="공개 상태", boolean=True)
    def publication_status(self, obj):
        return obj.is_published

    @admin.action(description="선택한 연도를 홈페이지에 공개")
    def publish_selected(self, request, queryset):
        count = queryset.update(is_published=True)
        self.message_user(request, f"{count}개 연도 자료를 공개했습니다.", messages.SUCCESS)

    @admin.action(description="선택한 연도를 작성 중으로 변경")
    def unpublish_selected(self, request, queryset):
        count = queryset.update(is_published=False)
        self.message_user(request, f"{count}개 연도 자료를 비공개로 변경했습니다.", messages.SUCCESS)
