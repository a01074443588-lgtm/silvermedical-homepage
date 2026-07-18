from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import BenefitSchedule


class BenefitScheduleTests(TestCase):
    def test_seeded_2026_schedule_matches_existing_calculator(self):
        schedule = BenefitSchedule.objects.get(year=2026)
        self.assertTrue(schedule.is_published)
        self.assertEqual(schedule.meal_price, 3500)
        self.assertEqual(schedule.snack_price, 1000)
        self.assertEqual(schedule.facility_rate_1, 93070)
        self.assertEqual(schedule.visit_240, 70080)

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
        self.assertEqual(schedule["food"], {"meal": 3500, "snack": 1000})
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
