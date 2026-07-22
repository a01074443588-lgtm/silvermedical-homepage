from django.urls import path

from . import views


app_name = "staff_resources"

urlpatterns = [
    path("", views.resource_list, name="list"),
    path("<str:slug>/", views.resource_detail, name="detail"),
    path("<str:slug>/download/", views.resource_download, name="download"),
]
