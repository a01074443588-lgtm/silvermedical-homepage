from django.contrib import admin, messages

from .models import BenefitSchedule


@admin.register(BenefitSchedule)
class BenefitScheduleAdmin(admin.ModelAdmin):
    list_display = ["year", "effective_date", "publication_status", "meal_price", "snack_price", "updated_at"]
    list_filter = ["is_published"]
    search_fields = ["year", "source_note"]
    ordering = ["-year"]
    save_as = True
    readonly_fields = ["created_at", "updated_at"]
    actions = ["publish_selected", "unpublish_selected"]
    fieldsets = [
        ("연도와 공개 설정", {"fields": [("year", "effective_date"), "is_published", "source_note"]}),
        ("기관 비급여", {"fields": [("meal_price", "snack_price")]}),
        (
            "본인부담률·감경률",
            {
                "fields": [
                    ("facility_standard_percent", "facility_discount40_percent", "facility_discount60_percent"),
                    ("home_standard_percent", "home_discount40_percent", "home_discount60_percent"),
                ]
            },
        ),
        ("재가급여 월 한도액", {"classes": ["collapse"], "fields": [("home_limit_1", "home_limit_2", "home_limit_3", "home_limit_4", "home_limit_5")]}),
        ("시설급여 1일 수가", {"fields": [("facility_rate_1", "facility_rate_2", "facility_rate_3", "facility_rate_4", "facility_rate_5")]}),
        (
            "주야간보호 시간·등급별 수가",
            {
                "classes": ["collapse"],
                "fields": [
                    ("daycare_3_6_1", "daycare_3_6_2", "daycare_3_6_3", "daycare_3_6_4", "daycare_3_6_5"),
                    ("daycare_6_8_1", "daycare_6_8_2", "daycare_6_8_3", "daycare_6_8_4", "daycare_6_8_5"),
                    ("daycare_8_10_1", "daycare_8_10_2", "daycare_8_10_3", "daycare_8_10_4", "daycare_8_10_5"),
                    ("daycare_10_13_1", "daycare_10_13_2", "daycare_10_13_3", "daycare_10_13_4", "daycare_10_13_5"),
                    ("daycare_13_plus_1", "daycare_13_plus_2", "daycare_13_plus_3", "daycare_13_plus_4", "daycare_13_plus_5"),
                ],
                "description": "각 행은 3~6시간, 6~8시간, 8~10시간, 10~13시간, 13시간 초과 순서입니다.",
            },
        ),
        (
            "방문요양 시간별 수가",
            {
                "classes": ["collapse"],
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
