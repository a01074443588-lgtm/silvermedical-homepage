from django.urls import path

from . import views


app_name = "consultations"

urlpatterns = [
    path("", views.create_consultation, name="create"),
    path("complete/", views.consultation_success, name="success"),
    path("health/", views.health, name="health"),
]
