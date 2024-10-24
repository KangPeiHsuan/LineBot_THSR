from django.contrib import admin
from django.urls import path

from thsr_bot import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("callback/", views.callback, name="callback"),
]
