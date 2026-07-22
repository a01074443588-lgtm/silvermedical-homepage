from django.contrib import admin
from django.urls import include, path

from center_news import views as news_views
from staff_notifications import views as notification_views


admin.site.site_header = "실버메디컬 운영 관리"
admin.site.site_title = "실버메디컬 운영 관리"
admin.site.index_title = "실버메디컬 운영 대시보드"
admin.site.site_url = "https://silvermedical.kr/"

urlpatterns = [
    path("news-media/<path:path>", news_views.public_media, name="news_media"),
    path("news/", include("center_news.urls")),
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
    path("staff/resources/", include("staff_resources.urls")),
    path("staff/", admin.site.urls),
]
