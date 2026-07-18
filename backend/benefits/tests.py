from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import BenefitSchedule, FacilityFeeSettings


class BenefitScheduleTests(TestCase):
    def test_seeded_2026_schedule_matches_existing_calculator(self):
        schedule = BenefitSchedule.objects.get(year=2026)
        self.assertTrue(schedule.is_published)
        self.assertEqual(schedule.facility_rate_1, 93070)
        self.assertEqual(schedule.visit_240, 70080)

        facility_fees = FacilityFeeSettings.current()
        self.assertEqual(facility_fees.meal_price, 3500)
        self.assertEqual(facility_fees.snack_price, 1000)

    def test_effective_date_must_match_year(self):
        schedule = BenefitSchedule.objects.get(year=2026)
        schedule.effective_date = date(2027, 1, 1)
        with self.assertRaises(ValidationError):
            schedule.full_clean()


class BenefitScheduleApiTests(TestCase):
    def test_public_api_returns_calculator_shape(self):
        response = self.client.get(reverse("benefits:published-schedules"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["schedules"]), 1)
        schedule = payload["schedules"][0]
        self.assertEqual(schedule["year"], "2026")
        self.assertEqual(payload["food"], {"meal": 3500, "snack": 1000})
        self.assertNotIn("food", schedule)
        self.assertEqual(schedule["data"]["facility"]["1"], 93070)
        self.assertEqual(schedule["data"]["daycare"]["13+"]["5"], 67240)
        self.assertNotIn("source_note", schedule)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("max-age=0", response["Cache-Control"])

    def test_unpublished_future_schedule_is_hidden(self):
        future = BenefitSchedule.objects.get(year=2026)
        future.pk = None
        future.year = 2027
        future.effective_date = date(2027, 1, 1)
        future.is_published = False
        future.save()

        response = self.client.get(reverse("benefits:published-schedules"))
        self.assertEqual([item["year"] for item in response.json()["schedules"]], ["2026"])

    def test_food_prices_are_independent_from_selected_year(self):
        facility_fees = FacilityFeeSettings.current()
        facility_fees.meal_price = 4000
        facility_fees.snack_price = 1200
        facility_fees.save()

        future = BenefitSchedule.objects.get(year=2026)
        future.pk = None
        future.year = 2027
        future.effective_date = date(2027, 1, 1)
        future.facility_rate_1 = 99999
        future.is_published = True
        future.save()

        payload = self.client.get(reverse("benefits:published-schedules")).json()
        self.assertEqual(payload["food"], {"meal": 4000, "snack": 1200})
        self.assertEqual([item["year"] for item in payload["schedules"]], ["2026", "2027"])
        self.assertEqual(payload["schedules"][1]["data"]["facility"]["1"], 99999)
