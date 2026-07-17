from django.contrib import admin
from django.urls import include, path


admin.site.site_header = "실버메디컬 상담 관리"
admin.site.site_title = "실버메디컬 상담 관리"
admin.site.index_title = "1:1 상담 접수함"

urlpatterns = [
    path("consult/", include("consultations.urls")),
    path("staff/", admin.site.urls),
]
