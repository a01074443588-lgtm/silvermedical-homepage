from django.contrib import admin
from django.urls import include, path

from staff_notifications import views as notification_views


admin.site.site_header = "실버메디컬 운영 관리"
admin.site.site_title = "실버메디컬 운영 관리"
admin.site.index_title = "상담 접수와 급여비용 설정"
admin.site.site_url = "https://silvermedical.kr/"

urlpatterns = [
    path("benefits-data/", include("benefits.urls")),
    path("consult/", include("consultations.urls")),
    path(
        "staff/notification-manifest.json",
        notification_views.notification_manifest,
        name="notification_manifest",
    ),
    path(
        "staff/notification-sw.js",
        notification_views.notification_service_worker,
        name="notification_service_worker",
    ),
    path("staff/notifications/", include("staff_notifications.urls")),
    path("staff/", admin.site.urls),
]
