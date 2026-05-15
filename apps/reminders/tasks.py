from django.conf import settings
from django.utils import timezone
from config.celery import app
from apps.reminders.models import Reminder
from apps.telegram_bot.client import send_message


@app.task
def send_due_reminders():
    due = Reminder.objects.filter(status=Reminder.Status.PENDING, remind_at__lte=timezone.now()).select_related('task')[:20]
    count = 0
    for reminder in due:
        send_message(settings.TELEGRAM_ALLOWED_CHAT_ID, f'Reminder: {reminder.task.title}')
        reminder.status = Reminder.Status.SENT
        reminder.sent_at = timezone.now()
        reminder.save(update_fields=['status', 'sent_at'])
        count += 1
    return f'Sent {count} reminders.'
