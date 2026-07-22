from django.urls import path

from . import views


app_name = "center_news"

urlpatterns = [
    path("", views.post_list, name="list"),
    path("api/latest/", views.latest_posts, name="latest"),
    path("sitemap.xml", views.news_sitemap, name="sitemap"),
    path("<str:slug>/", views.post_detail, name="detail"),
]
