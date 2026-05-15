from django.conf import settings
from django.utils import timezone
from config.celery import app
from apps.briefing.models import DailyBriefing
from apps.briefing.services import build_briefing
from apps.telegram_bot.client import send_message


@app.task
def send_daily_briefing():
    now = timezone.localtime()
    if now.hour != settings.BRIEFING_HOUR or now.minute != settings.BRIEFING_MINUTE:
        return 'Not briefing time.'
    briefing, created = DailyBriefing.objects.get_or_create(
        briefing_date=now.date(),
        defaults={'content': build_briefing()},
    )
    if briefing.sent_at:
        return 'Already sent.'
    send_message(settings.TELEGRAM_ALLOWED_CHAT_ID, briefing.content)
    briefing.sent_at = timezone.now()
    briefing.save(update_fields=['sent_at'])
    return 'Sent.'
