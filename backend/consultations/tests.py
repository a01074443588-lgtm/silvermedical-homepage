from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import ConsultationForm
from .models import Consultation


VALID_DATA = {
    "category": Consultation.Category.NURSING_HOME,
    "guardian_name": "홍길동",
    "phone": "01012345678",
    "preferred_contact_time": Consultation.ContactTime.AFTERNOON,
    "message": "어머니의 요양원 입소 상담을 받고 싶습니다.",
    "privacy_agree": "on",
    "website": "",
}


class ConsultationFormTests(TestCase):
    def test_valid_form_normalizes_phone(self):
        form = ConsultationForm(data=VALID_DATA)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["phone"], "010-1234-5678")

    def test_privacy_agreement_is_required(self):
        data = {**VALID_DATA, "privacy_agree": ""}
        form = ConsultationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("privacy_agree", form.errors)

    def test_message_must_contain_at_least_ten_characters(self):
        form = ConsultationForm(data={**VALID_DATA, "message": "테스트"})
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)


class ConsultationViewTests(TestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse("consultations:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_valid_submission_creates_private_record(self):
        response = self.client.post(reverse("consultations:create"), VALID_DATA)
        self.assertRedirects(response, reverse("consultations:success"))
        consultation = Consultation.objects.get()
        self.assertRegex(consultation.reference_code, r"^SM-\d{6}-[A-HJ-NP-Z2-9]{6}$")
        self.assertEqual(consultation.phone, "010-1234-5678")
        self.assertEqual(consultation.status, Consultation.Status.NEW)

    def test_invalid_submission_shows_prominent_error_summary(self):
        response = self.client.post(
            reverse("consultations:create"),
            {**VALID_DATA, "message": "테스트"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "입력 내용을 확인해 주세요")
        self.assertContains(response, "상담 내용을 10자 이상 입력해 주세요")
        self.assertFalse(Consultation.objects.exists())

    def test_honeypot_submission_is_not_saved(self):
        response = self.client.post(
            reverse("consultations:create"),
            {**VALID_DATA, "website": "https://spam.example"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Consultation.objects.exists())

    def test_staff_page_requires_login(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/staff/login/", response.url)

    def test_staff_user_can_open_consultation_list(self):
        user = get_user_model().objects.create_superuser(
            username="staff-test",
            email="staff@example.com",
            password="A-long-test-password-2026",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("admin:consultations_consultation_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "상담 접수함")
