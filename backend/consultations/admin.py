from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone

from staff_notifications.services import (
    acknowledge_consultation,
    safe_enqueue_consultation_notifications,
)

from .models import (
    Consultation,
    ConsultationAssignment,
    ConsultationStatusHistory,
)


class ConsultationAssignmentInline(admin.TabularInline):
    model = ConsultationAssignment
    extra = 0
    can_delete = False
    fields = ["assigned_to", "assigned_by", "note", "created_at"]
    readonly_fields = fields
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False


class ConsultationStatusHistoryInline(admin.TabularInline):
    model = ConsultationStatusHistory
    extra = 0
    can_delete = False
    fields = ["created_at", "event", "actor", "from_status", "to_status", "description"]
    readonly_fields = fields
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    change_form_template = "admin/consultations/consultation/change_form.html"
    list_display = [
        "reference_code",
        "category",
        "guardian_name",
        "masked_phone",
        "preferred_contact_time",
        "status",
        "assigned_to",
        "first_viewed_at",
        "created_at",
    ]
    list_filter = ["status", "category", "assigned_to", "preferred_contact_time", "created_at"]
    search_fields = ["reference_code", "guardian_name", "phone", "message"]
    readonly_fields = [
        "reference_code",
        "privacy_agreed_at",
        "consent_version",
        "created_at",
        "updated_at",
        "first_viewed_at",
        "first_viewed_by",
        "completed_at",
        "contact_completed_at",
        "closed_at",
        "retention_due_display",
    ]
    fieldsets = [
        (
            "상담 접수",
            {
                "fields": [
                    "reference_code",
                    "category",
                    "guardian_name",
                    "phone",
                    "preferred_contact_time",
                    "message",
                ]
            },
        ),
        (
            "담당 및 처리",
            {
                "fields": [
                    "status",
                    "assigned_to",
                    "staff_note",
                    "first_viewed_at",
                    "first_viewed_by",
                    "contact_completed_at",
                    "completed_at",
                    "closed_at",
                    "retention_due_display",
                ]
            },
        ),
        (
            "개인정보 동의",
            {
                "classes": ["collapse"],
                "fields": ["privacy_agreed_at", "consent_version", "created_at", "updated_at"],
            },
        ),
    ]
    actions = ["mark_acknowledged", "mark_in_progress", "mark_completed", "mark_closed"]
    inlines = [ConsultationAssignmentInline, ConsultationStatusHistoryInline]
    date_hierarchy = "created_at"
    list_per_page = 30
    ordering = ["-created_at"]
    list_select_related = ["assigned_to", "first_viewed_by"]

    def get_urls(self):
        custom_urls = [
            path(
                "<int:object_id>/acknowledge/",
                self.admin_site.admin_view(self.acknowledge_view),
                name="consultation_acknowledge",
            ),
            path(
                "<int:object_id>/contact-complete/",
                self.admin_site.admin_view(self.contact_complete_view),
                name="consultation_contact_complete",
            ),
            path(
                "<int:object_id>/close-consultation/",
                self.admin_site.admin_view(self.close_view),
                name="consultation_close",
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description="연락처")
    def masked_phone(self, obj):
        digits = "".join(character for character in obj.phone if character.isdigit())
        return f"***-****-{digits[-4:]}" if len(digits) >= 4 else "확인 필요"

    @admin.display(description="파기 검토일")
    def retention_due_display(self, obj):
        return obj.retention_due_at or "상담 완료 후 계산"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.method == "GET":
            consultation = self.get_object(request, object_id)
            if consultation and self.has_view_or_change_permission(request, consultation):
                acknowledge_consultation(
                    consultation.pk,
                    request.user,
                    event=ConsultationStatusHistory.Event.VIEWED,
                )
        return super().change_view(request, object_id, form_url, extra_context)

    def _require_post(self, request):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        return None

    def _get_changeable_object(self, request, object_id, *, lock=False):
        queryset = Consultation.objects.select_for_update() if lock else Consultation.objects
        consultation = get_object_or_404(queryset, pk=object_id)
        if not self.has_change_permission(request, consultation):
            raise PermissionDenied
        return consultation

    def acknowledge_view(self, request, object_id):
        invalid = self._require_post(request)
        if invalid:
            return invalid
        consultation = self._get_changeable_object(request, object_id)
        acknowledge_consultation(consultation.pk, request.user)
        messages.success(request, "상담 접수를 확인 처리했습니다.")
        return redirect(reverse("admin:consultations_consultation_change", args=[object_id]))

    @transaction.atomic
    def contact_complete_view(self, request, object_id):
        invalid = self._require_post(request)
        if invalid:
            return invalid
        consultation = self._get_changeable_object(request, object_id, lock=True)
        old_status = consultation.status
        consultation.contact_completed_at = timezone.now()
        if consultation.status in {
            Consultation.Status.NEW,
            Consultation.Status.ACKNOWLEDGED,
            Consultation.Status.ASSIGNED,
        }:
            consultation.status = Consultation.Status.IN_PROGRESS
        consultation.save(update_fields=["contact_completed_at", "status", "updated_at"])
        ConsultationStatusHistory.objects.create(
            consultation=consultation,
            actor=request.user,
            event=ConsultationStatusHistory.Event.CONTACT_COMPLETED,
            from_status=old_status,
            to_status=consultation.status,
            description="보호자 연락 완료 처리",
        )
        messages.success(request, "보호자 연락 완료를 기록했습니다.")
        return redirect(reverse("admin:consultations_consultation_change", args=[object_id]))

    @transaction.atomic
    def close_view(self, request, object_id):
        invalid = self._require_post(request)
        if invalid:
            return invalid
        consultation = self._get_changeable_object(request, object_id, lock=True)
        old_status = consultation.status
        now = timezone.now()
        consultation.status = Consultation.Status.CLOSED
        consultation.closed_at = now
        consultation.completed_at = consultation.completed_at or now
        consultation.save(update_fields=["status", "closed_at", "completed_at", "updated_at"])
        ConsultationStatusHistory.objects.create(
            consultation=consultation,
            actor=request.user,
            event=ConsultationStatusHistory.Event.CLOSED,
            from_status=old_status,
            to_status=consultation.status,
            description="상담 종결 처리",
        )
        messages.success(request, "상담을 종결했습니다.")
        return redirect(reverse("admin:consultations_consultation_change", args=[object_id]))

    def _bulk_status_change(self, request, queryset, new_status, event, description):
        now = timezone.now()
        with transaction.atomic():
            for consultation in queryset.select_for_update():
                old_status = consultation.status
                consultation.status = new_status
                if new_status == Consultation.Status.COMPLETED:
                    consultation.completed_at = now
                elif new_status == Consultation.Status.CLOSED:
                    consultation.completed_at = consultation.completed_at or now
                    consultation.closed_at = now
                consultation.save()
                ConsultationStatusHistory.objects.create(
                    consultation=consultation,
                    actor=request.user,
                    event=event,
                    from_status=old_status,
                    to_status=new_status,
                    description=description,
                )

    @admin.action(description="선택한 상담을 '접수 확인'으로 변경")
    def mark_acknowledged(self, request, queryset):
        for consultation in queryset:
            acknowledge_consultation(consultation.pk, request.user)

    @admin.action(description="선택한 상담을 '연락 중'으로 변경")
    def mark_in_progress(self, request, queryset):
        self._bulk_status_change(
            request,
            queryset,
            Consultation.Status.IN_PROGRESS,
            ConsultationStatusHistory.Event.STATUS_CHANGED,
            "연락 중으로 상태 변경",
        )

    @admin.action(description="선택한 상담을 '상담 완료'로 변경")
    def mark_completed(self, request, queryset):
        self._bulk_status_change(
            request,
            queryset,
            Consultation.Status.COMPLETED,
            ConsultationStatusHistory.Event.STATUS_CHANGED,
            "상담 완료로 상태 변경",
        )

    @admin.action(description="선택한 상담을 '종결'로 변경")
    def mark_closed(self, request, queryset):
        self._bulk_status_change(
            request,
            queryset,
            Consultation.Status.CLOSED,
            ConsultationStatusHistory.Event.CLOSED,
            "상담 종결 처리",
        )

    def save_model(self, request, obj, form, change):
        previous = Consultation.objects.get(pk=obj.pk) if change else None
        if obj.status == Consultation.Status.COMPLETED and not obj.completed_at:
            obj.completed_at = timezone.now()
        elif obj.status not in {Consultation.Status.COMPLETED, Consultation.Status.CLOSED}:
            obj.completed_at = None
        if obj.status == Consultation.Status.CLOSED and not obj.closed_at:
            obj.closed_at = timezone.now()
        elif obj.status != Consultation.Status.CLOSED:
            obj.closed_at = None
        super().save_model(request, obj, form, change)

        if not change:
            safe_enqueue_consultation_notifications(obj.pk)
            return

        if previous.assigned_to_id != obj.assigned_to_id:
            ConsultationAssignment.objects.create(
                consultation=obj,
                assigned_to=obj.assigned_to,
                assigned_by=request.user,
            )
            ConsultationStatusHistory.objects.create(
                consultation=obj,
                actor=request.user,
                event=ConsultationStatusHistory.Event.ASSIGNED,
                from_status=previous.status,
                to_status=obj.status,
                description=(
                    f"담당자 지정: {obj.assigned_to.get_username()}"
                    if obj.assigned_to
                    else "담당자 지정 해제"
                ),
            )
        if previous.status != obj.status:
            ConsultationStatusHistory.objects.create(
                consultation=obj,
                actor=request.user,
                event=ConsultationStatusHistory.Event.STATUS_CHANGED,
                from_status=previous.status,
                to_status=obj.status,
                description="상담 진행 상태 변경",
            )
        if previous.staff_note != obj.staff_note:
            ConsultationStatusHistory.objects.create(
                consultation=obj,
                actor=request.user,
                event=ConsultationStatusHistory.Event.NOTE_UPDATED,
                from_status=obj.status,
                to_status=obj.status,
                description="직원 상담 메모 변경",
            )


@admin.register(ConsultationAssignment)
class ConsultationAssignmentAdmin(admin.ModelAdmin):
    list_display = ["consultation", "assigned_to", "assigned_by", "created_at"]
    list_filter = ["created_at", "assigned_to"]
    search_fields = ["consultation__reference_code", "assigned_to__username"]
    readonly_fields = [field.name for field in ConsultationAssignment._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ConsultationStatusHistory)
class ConsultationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["created_at", "consultation", "event", "actor", "from_status", "to_status"]
    list_filter = ["event", "created_at"]
    search_fields = ["consultation__reference_code", "actor__username"]
    readonly_fields = [field.name for field in ConsultationStatusHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
