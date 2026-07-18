from django import forms

from consultations.models import Consultation

from .models import StaffNotificationProfile


class StaffNotificationProfileForm(forms.ModelForm):
    consultation_types = forms.MultipleChoiceField(
        label="알림 수신 상담 유형",
        choices=Consultation.Category.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="선택한 상담 종류만 알림을 받습니다.",
    )

    class Meta:
        model = StaffNotificationProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["consultation_types"] = self.instance.consultation_types

    def clean_consultation_types(self):
        return list(self.cleaned_data["consultation_types"])
