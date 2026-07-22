from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import StaffResource


class StaffResourceTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            "staff-resource-user",
            "staff-resource@example.com",
            "long-test-password",
            is_staff=True,
        )
        self.resource = StaffResource.objects.create(
            category=StaffResource.Category.GUIDE,
            title="야간 업무 안내",
            summary="야간 업무에 필요한 내용을 안내합니다.",
            body="근무 전 확인해 주세요.",
            is_published=True,
        )

    def test_anonymous_user_is_redirected_to_staff_login(self):
        response = self.client.get(reverse("staff_resources:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/staff/login/", response.url)

    def test_staff_user_can_read_published_resource(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.resource.get_absolute_url())
        self.assertContains(response, self.resource.title)

    def test_unpublished_resource_is_not_visible(self):
        draft = StaffResource.objects.create(
            category=StaffResource.Category.FORM,
            title="작성 중 서식",
            summary="아직 공개하지 않은 자료입니다.",
            body="작성 중입니다.",
        )
        self.client.force_login(self.staff)
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_staff_can_download_published_attachment(self):
        resource = StaffResource.objects.create(
            category=StaffResource.Category.FORM,
            title="교육자료 파일",
            summary="직원 교육자료입니다.",
            attachment=SimpleUploadedFile("training.pdf", b"safe-test-file"),
            is_published=True,
        )
        self.client.force_login(self.staff)
        response = self.client.get(reverse("staff_resources:download", args=[resource.slug]))
        self.assertEqual(response.status_code, 200)
        resource.delete()

    def test_admin_dashboard_does_not_repeat_the_navigation_menu(self):
        administrator = get_user_model().objects.create_superuser(
            "dashboard-administrator",
            "dashboard@example.com",
            "long-test-password",
        )
        self.client.force_login(administrator)

        response = self.client.get(reverse("admin:index"))

        self.assertContains(response, "자주 하는 업무를 바로 시작하세요")
        self.assertNotContains(response, "전체 관리 메뉴")
