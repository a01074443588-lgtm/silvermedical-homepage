import re

from django import forms

from .models import Consultation


class ConsultationForm(forms.ModelForm):
    privacy_agree = forms.BooleanField(
        label="개인정보 수집·이용에 동의합니다.",
        required=True,
    )
    website = forms.CharField(
        required=False,
        label="웹사이트",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "tabindex": "-1",
            }
        ),
    )

    class Meta:
        model = Consultation
        fields = [
            "category",
            "guardian_name",
            "phone",
            "preferred_contact_time",
            "message",
        ]
        widgets = {
            "category": forms.Select(attrs={"autocomplete": "off"}),
            "guardian_name": forms.TextInput(
                attrs={"autocomplete": "name", "placeholder": "예: 홍길동"}
            ),
            "phone": forms.TextInput(
                attrs={
                    "autocomplete": "tel",
                    "inputmode": "tel",
                    "placeholder": "예: 010-1234-5678",
                }
            ),
            "preferred_contact_time": forms.Select(attrs={"autocomplete": "off"}),
            "message": forms.Textarea(
                attrs={
                    "rows": 7,
                    "placeholder": "현재 가장 걱정되는 부분과 상담받고 싶은 내용을 적어주세요.",
                }
            ),
        }

    def clean_guardian_name(self):
        name = self.cleaned_data["guardian_name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("성명을 두 글자 이상 입력해 주세요.")
        return name

    def clean_phone(self):
        digits = re.sub(r"\D", "", self.cleaned_data["phone"])
        if len(digits) not in {9, 10, 11}:
            raise forms.ValidationError("연락 가능한 전화번호를 확인해 주세요.")
        if len(digits) == 11:
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        if len(digits) == 10 and digits.startswith("02"):
            return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        return digits

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 10:
            raise forms.ValidationError("상담 내용을 10자 이상 입력해 주세요.")
        return message

    def clean_website(self):
        value = self.cleaned_data.get("website", "")
        if value:
            raise forms.ValidationError("자동 입력으로 확인되었습니다.")
        return value
