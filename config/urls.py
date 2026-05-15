from django.contrib import admin
from django.urls import path
from apps.telegram_bot.views import telegram_webhook
from config.views import healthz, home

urlpatterns = [
    path('', home, name='home'),
    path('healthz/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    path('telegram/webhook/', telegram_webhook, name='telegram_webhook'),
]
