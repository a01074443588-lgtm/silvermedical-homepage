from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


MONEY_VALIDATORS = [MinValueValidator(1)]
PERCENT_VALIDATORS = [MinValueValidator(0), MaxValueValidator(100)]


class BenefitSchedule(models.Model):
    year = models.PositiveSmallIntegerField(
        "기준연도",
        unique=True,
        validators=[MinValueValidator(2020), MaxValueValidator(2100)],
        help_text="기존 연도를 연 뒤 '새 항목으로 저장'을 사용하면 다음 연도 자료를 쉽게 만들 수 있습니다.",
    )
    effective_date = models.DateField("적용 시작일")
    is_published = models.BooleanField(
        "홈페이지 공개",
        default=False,
        help_text="선택한 자료만 홈페이지 계산기의 연도 목록에 표시됩니다.",
    )
    source_note = models.TextField(
        "근거·확인 메모",
        blank=True,
        help_text="공단 고시명, 확인일 또는 내부 검토 내용을 기록해 주세요.",
    )

    meal_price = models.PositiveIntegerField("식사 1끼", validators=MONEY_VALIDATORS)
    snack_price = models.PositiveIntegerField("간식 1회", validators=MONEY_VALIDATORS)

    facility_standard_percent = models.DecimalField(
        "시설 일반 본인부담률(%)", max_digits=5, decimal_places=2, validators=PERCENT_VALIDATORS
    )
    facility_discount40_percent = models.DecimalField(
        "시설 40% 감경 본인부담률(%)", max_digits=5, decimal_places=2, validators=PERCENT_VALIDATORS
    )
    facility_discount60_percent = models.DecimalField(
        "시설 60% 감경 본인부담률(%)", max_digits=5, decimal_places=2, validators=PERCENT_VALIDATORS
    )
    home_standard_percent = models.DecimalField(
        "재가 일반 본인부담률(%)", max_digits=5, decimal_places=2, validators=PERCENT_VALIDATORS
    )
    home_discount40_percent = models.DecimalField(
        "재가 40% 감경 본인부담률(%)", max_digits=5, decimal_places=2, validators=PERCENT_VALIDATORS
    )
    home_discount60_percent = models.DecimalField(
        "재가 60% 감경 본인부담률(%)", max_digits=5, decimal_places=2, validators=PERCENT_VALIDATORS
    )

    home_limit_1 = models.PositiveIntegerField("1등급 월 한도액", validators=MONEY_VALIDATORS)
    home_limit_2 = models.PositiveIntegerField("2등급 월 한도액", validators=MONEY_VALIDATORS)
    home_limit_3 = models.PositiveIntegerField("3등급 월 한도액", validators=MONEY_VALIDATORS)
    home_limit_4 = models.PositiveIntegerField("4등급 월 한도액", validators=MONEY_VALIDATORS)
    home_limit_5 = models.PositiveIntegerField("5등급 월 한도액", validators=MONEY_VALIDATORS)

    facility_rate_1 = models.PositiveIntegerField("시설 1등급 1일 수가", validators=MONEY_VALIDATORS)
    facility_rate_2 = models.PositiveIntegerField("시설 2등급 1일 수가", validators=MONEY_VALIDATORS)
    facility_rate_3 = models.PositiveIntegerField("시설 3등급 1일 수가", validators=MONEY_VALIDATORS)
    facility_rate_4 = models.PositiveIntegerField("시설 4등급 1일 수가", validators=MONEY_VALIDATORS)
    facility_rate_5 = models.PositiveIntegerField("시설 5등급 1일 수가", validators=MONEY_VALIDATORS)

    daycare_3_6_1 = models.PositiveIntegerField("3~6시간 1등급", validators=MONEY_VALIDATORS)
    daycare_3_6_2 = models.PositiveIntegerField("3~6시간 2등급", validators=MONEY_VALIDATORS)
    daycare_3_6_3 = models.PositiveIntegerField("3~6시간 3등급", validators=MONEY_VALIDATORS)
    daycare_3_6_4 = models.PositiveIntegerField("3~6시간 4등급", validators=MONEY_VALIDATORS)
    daycare_3_6_5 = models.PositiveIntegerField("3~6시간 5등급", validators=MONEY_VALIDATORS)
    daycare_6_8_1 = models.PositiveIntegerField("6~8시간 1등급", validators=MONEY_VALIDATORS)
    daycare_6_8_2 = models.PositiveIntegerField("6~8시간 2등급", validators=MONEY_VALIDATORS)
    daycare_6_8_3 = models.PositiveIntegerField("6~8시간 3등급", validators=MONEY_VALIDATORS)
    daycare_6_8_4 = models.PositiveIntegerField("6~8시간 4등급", validators=MONEY_VALIDATORS)
    daycare_6_8_5 = models.PositiveIntegerField("6~8시간 5등급", validators=MONEY_VALIDATORS)
    daycare_8_10_1 = models.PositiveIntegerField("8~10시간 1등급", validators=MONEY_VALIDATORS)
    daycare_8_10_2 = models.PositiveIntegerField("8~10시간 2등급", validators=MONEY_VALIDATORS)
    daycare_8_10_3 = models.PositiveIntegerField("8~10시간 3등급", validators=MONEY_VALIDATORS)
    daycare_8_10_4 = models.PositiveIntegerField("8~10시간 4등급", validators=MONEY_VALIDATORS)
    daycare_8_10_5 = models.PositiveIntegerField("8~10시간 5등급", validators=MONEY_VALIDATORS)
    daycare_10_13_1 = models.PositiveIntegerField("10~13시간 1등급", validators=MONEY_VALIDATORS)
    daycare_10_13_2 = models.PositiveIntegerField("10~13시간 2등급", validators=MONEY_VALIDATORS)
    daycare_10_13_3 = models.PositiveIntegerField("10~13시간 3등급", validators=MONEY_VALIDATORS)
    daycare_10_13_4 = models.PositiveIntegerField("10~13시간 4등급", validators=MONEY_VALIDATORS)
    daycare_10_13_5 = models.PositiveIntegerField("10~13시간 5등급", validators=MONEY_VALIDATORS)
    daycare_13_plus_1 = models.PositiveIntegerField("13시간 초과 1등급", validators=MONEY_VALIDATORS)
    daycare_13_plus_2 = models.PositiveIntegerField("13시간 초과 2등급", validators=MONEY_VALIDATORS)
    daycare_13_plus_3 = models.PositiveIntegerField("13시간 초과 3등급", validators=MONEY_VALIDATORS)
    daycare_13_plus_4 = models.PositiveIntegerField("13시간 초과 4등급", validators=MONEY_VALIDATORS)
    daycare_13_plus_5 = models.PositiveIntegerField("13시간 초과 5등급", validators=MONEY_VALIDATORS)

    visit_30 = models.PositiveIntegerField("방문요양 30분", validators=MONEY_VALIDATORS)
    visit_60 = models.PositiveIntegerField("방문요양 60분", validators=MONEY_VALIDATORS)
    visit_90 = models.PositiveIntegerField("방문요양 90분", validators=MONEY_VALIDATORS)
    visit_120 = models.PositiveIntegerField("방문요양 120분", validators=MONEY_VALIDATORS)
    visit_150 = models.PositiveIntegerField("방문요양 150분", validators=MONEY_VALIDATORS)
    visit_180 = models.PositiveIntegerField("방문요양 180분", validators=MONEY_VALIDATORS)
    visit_210 = models.PositiveIntegerField("방문요양 210분", validators=MONEY_VALIDATORS)
    visit_240 = models.PositiveIntegerField("방문요양 240분", validators=MONEY_VALIDATORS)

    regular_care_hourly_pay = models.PositiveIntegerField("일반요양 시급", validators=MONEY_VALIDATORS)
    family60_hourly_pay = models.PositiveIntegerField("가족요양 60분 시급", validators=MONEY_VALIDATORS)
    family90_hourly_pay = models.PositiveIntegerField("가족요양 90분 시급", validators=MONEY_VALIDATORS)

    created_at = models.DateTimeField("등록 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    class Meta:
        verbose_name = "연도별 급여비용 설정"
        verbose_name_plural = "연도별 급여비용 설정"
        ordering = ["-year"]

    def clean(self):
        super().clean()
        if self.effective_date and self.year and self.effective_date.year != self.year:
            raise ValidationError({"effective_date": "적용 시작일의 연도와 기준연도를 같게 입력해 주세요."})

    @staticmethod
    def _rate(percent):
        return float(Decimal(percent) / Decimal("100"))

    @staticmethod
    def _percent_text(percent):
        return format(Decimal(percent).normalize(), "f")

    def as_public_data(self):
        grades = range(1, 6)
        today = timezone.localdate()
        return {
            "year": str(self.year),
            "effectiveDate": self.effective_date.isoformat(),
            "isFuture": self.effective_date > today,
            "food": {"meal": self.meal_price, "snack": self.snack_price},
            "discounts": {
                "facility": [
                    {"key": "standard", "label": "일반", "rate": self._rate(self.facility_standard_percent)},
                    {"key": "facility40", "label": f"시설 40% 감경 ({self._percent_text(self.facility_discount40_percent)}%)", "rate": self._rate(self.facility_discount40_percent)},
                    {"key": "facility60", "label": f"시설 60% 감경 ({self._percent_text(self.facility_discount60_percent)}%)", "rate": self._rate(self.facility_discount60_percent)},
                    {"key": "basic", "label": "기초수급 (0%)", "rate": 0},
                ],
                "home": [
                    {"key": "standard", "label": "일반", "rate": self._rate(self.home_standard_percent)},
                    {"key": "home40", "label": f"재가 40% 감경 ({self._percent_text(self.home_discount40_percent)}%)", "rate": self._rate(self.home_discount40_percent)},
                    {"key": "home60", "label": f"재가 60% 감경 ({self._percent_text(self.home_discount60_percent)}%)", "rate": self._rate(self.home_discount60_percent)},
                    {"key": "basic", "label": "기초수급 (0%)", "rate": 0},
                ],
            },
            "regularCare": {
                "label": "일반요양",
                "hourlyPay": self.regular_care_hourly_pay,
                "defaultDays": 20,
            },
            "familyCare": {
                "family60": {"label": "가족 60분", "hourlyPay": self.family60_hourly_pay, "hours": 1, "defaultDays": 20},
                "family90": {"label": "가족 90분", "hourlyPay": self.family90_hourly_pay, "hours": 1.5, "defaultDays": 31},
            },
            "data": {
                "homeLimit": {str(grade): getattr(self, f"home_limit_{grade}") for grade in grades},
                "facility": {str(grade): getattr(self, f"facility_rate_{grade}") for grade in grades},
                "daycare": {
                    "3-6": {str(grade): getattr(self, f"daycare_3_6_{grade}") for grade in grades},
                    "6-8": {str(grade): getattr(self, f"daycare_6_8_{grade}") for grade in grades},
                    "8-10": {str(grade): getattr(self, f"daycare_8_10_{grade}") for grade in grades},
                    "10-13": {str(grade): getattr(self, f"daycare_10_13_{grade}") for grade in grades},
                    "13+": {str(grade): getattr(self, f"daycare_13_plus_{grade}") for grade in grades},
                },
                "visit": {str(minutes): getattr(self, f"visit_{minutes}") for minutes in (30, 60, 90, 120, 150, 180, 210, 240)},
            },
        }

    def __str__(self):
        status = "공개" if self.is_published else "작성 중"
        return f"{self.year}년 급여비용 ({status})"
