from django.urls import path

from . import views


app_name = "benefits"

urlpatterns = [
    path("", views.published_schedules, name="published-schedules"),
]
