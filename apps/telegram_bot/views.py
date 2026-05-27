import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from apps.telegram_bot.client import send_message
from apps.tasks.models import Task
from apps.tasks.services import create_task_from_text, format_task
from apps.briefing.services import build_briefing, build_ceo_suggestions, build_followup_draft
from apps.integrations.gitlab import radar_summary

HELP = """CEO Copilot commands:
/help
/add Follow up with Ahmed tomorrow
/tasks
/today
/overdue
/done 12
/briefing
/suggest
/gitlab
/draft_followup
"""


def _authorized(chat_id: str) -> bool:
    return str(chat_id) == str(settings.TELEGRAM_ALLOWED_CHAT_ID)


def handle_message(chat_id: str, text: str) -> str:
    text = (text or '').strip()
    if text in ['/start', '/help']:
        return HELP

    if text.startswith('/add') or text.lower().startswith('remind me to'):
        task = create_task_from_text(text)
        return 'Created task:\n' + format_task(task)

    if text == '/tasks':
        qs = Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING]).order_by('due_date', '-updated_at')[:10]
        return '\n\n'.join(format_task(t) for t in qs) or 'No open tasks.'

    if text == '/today':
        now = timezone.now()
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        qs = Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING], due_date__lte=end).order_by('due_date')[:10]
        return '\n\n'.join(format_task(t) for t in qs) or 'No tasks due today.'

    if text == '/overdue':
        qs = [t for t in Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING]).order_by('due_date') if t.is_overdue()]
        return '\n\n'.join(format_task(t) for t in qs[:10]) or 'No overdue tasks.'

    if text.startswith('/done'):
        parts = text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return 'Usage: /done task_id'
        try:
            task = Task.objects.get(id=int(parts[1]))
        except Task.DoesNotExist:
            return 'Task not found.'
        task.status = Task.Status.DONE
        task.save(update_fields=['status', 'updated_at'])
        return f'Done: #{task.id} {task.title}'

    if text == '/briefing':
        return build_briefing()

    if text == '/suggest':
        return build_ceo_suggestions()

    if text == '/gitlab':
        return radar_summary()

    if text == '/draft_followup':
        return build_followup_draft()

    # Fallback: capture as task by default to reduce friction.
    task = create_task_from_text(text)
    return 'Captured as task:\n' + format_task(task)


@csrf_exempt
def telegram_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'ok': True})
    payload = json.loads(request.body.decode('utf-8'))
    message = payload.get('message') or payload.get('edited_message') or {}
    chat = message.get('chat') or {}
    chat_id = str(chat.get('id', ''))
    if not _authorized(chat_id):
        return HttpResponseForbidden('Unauthorized chat')
    text = message.get('text', '')
    reply = handle_message(chat_id, text)
    send_message(chat_id, reply[:3900])
    return JsonResponse({'ok': True, 'reply': reply})
