from django.contrib import admin
from django.urls import path

from thsr_bot.views import callback

urlpatterns = [
    path("admin/", admin.site.urls),
    path("callback", callback, name="callback"),
]
