from django.urls import path

from . import views


app_name = "staff_notifications"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("guide/iphone/", views.iphone_guide, name="iphone_guide"),
    path("api/status/", views.notification_status, name="status"),
    path("api/push/config/", views.push_config, name="push_config"),
    path("api/push/subscribe/", views.push_subscribe, name="push_subscribe"),
    path("api/push/unsubscribe/", views.push_unsubscribe, name="push_unsubscribe"),
    path(
        "api/push/devices/<int:subscription_id>/remove/",
        views.push_device_remove,
        name="push_device_remove",
    ),
    path("api/test/", views.test_notification, name="test_notification"),
    path("kakao/connect/", views.kakao_connect, name="kakao_connect"),
    path("kakao/callback/", views.kakao_callback, name="kakao_callback"),
    path("kakao/disconnect/", views.kakao_disconnect, name="kakao_disconnect"),
]
