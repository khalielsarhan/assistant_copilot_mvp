import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from apps.telegram_bot.client import send_message
from apps.tasks.models import Task
from apps.tasks.services import (
    cancel_all_open_tasks,
    cancel_task,
    complete_task,
    create_task_from_text,
    find_active_tasks,
    format_task,
)
from apps.briefing.services import build_briefing, build_ceo_suggestions, build_followup_draft
from apps.integrations.gitlab import radar_summary

HELP = """CEO Copilot commands:
/help
/add Follow up with Ahmed tomorrow
/tasks
/today
/overdue
/done 12
/done Ahmed follow up
/cancel Ahmed follow up
/remove Ahmed follow up
/briefing
/suggest
/gitlab
/draft_followup
"""


def _authorized(chat_id: str) -> bool:
    return str(chat_id) == str(settings.TELEGRAM_ALLOWED_CHAT_ID)


def _lookup_response(matches, action_label: str) -> str | None:
    if not matches:
        return f'I could not find an open task matching that. Try /tasks and use the task ID.'
    if len(matches) > 1:
        options = '\n\n'.join(format_task(task) for task in matches)
        return f'I found multiple possible tasks. Please use the task ID.\n\n{options}'
    return None


def _extract_action_query(text: str, command: str, verbs: list[str]) -> str:
    lower = text.lower().strip()
    if lower.startswith(command):
        return text[len(command):].strip()
    for verb in verbs:
        if lower.startswith(verb):
            return text[len(verb):].strip()
    return text


def _is_greeting(text: str) -> bool:
    return text.lower().strip() in {
        'hi',
        'hello',
        'hey',
        'salam',
        'السلام عليكم',
        'thanks',
        'thank you',
        'ok',
        'okay',
    }


def _looks_like_task(text: str) -> bool:
    lower = text.lower()
    task_markers = [
        'follow up',
        'follow-up',
        'remind',
        'call ',
        'email ',
        'send ',
        'review ',
        'approve ',
        'check ',
        'prepare ',
        'draft ',
        'schedule ',
        'book ',
        'pay ',
        'invoice',
        'client',
        'urgent',
        'asap',
        'tomorrow',
        'today',
        'next week',
        'deadline',
    ]
    return any(marker in lower for marker in task_markers)


def _is_cancel_all_request(text: str) -> bool:
    lower = ' '.join(text.lower().replace('-', ' ').split())
    cancel_words = ['remove', 'delete', 'cancel', 'clear']
    target_phrases = ['all open tasks', 'all tasks', 'everything', 'all reminders']
    return any(lower.startswith(word) for word in cancel_words) and any(phrase in lower for phrase in target_phrases)


def handle_message(chat_id: str, text: str) -> str:
    text = (text or '').strip()
    lower = text.lower()
    if not text:
        return 'Send /help to see commands, or /add followed by a task.'
    if lower in ['/start', '/help']:
        return HELP
    if _is_greeting(text):
        return 'Hi. Send /help for commands, or /add followed by a task.'

    if lower.startswith('/add') or lower.startswith('remind me to'):
        if text == '/add':
            return 'Usage: /add Follow up with Ahmed tomorrow'
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

    if lower.startswith('/done') or lower.startswith('done ') or lower.startswith('complete ') or lower.startswith('mark ') or lower.startswith('finish '):
        parts = text.split()
        if len(parts) < 2:
            return 'Usage: /done task_id or /done task title'
        if parts[1].isdigit():
            try:
                task = Task.objects.get(id=int(parts[1]))
            except Task.DoesNotExist:
                return 'Task not found.'
        else:
            query = _extract_action_query(text, '/done', ['done', 'complete', 'mark', 'finish'])
            matches = find_active_tasks(query)
            response = _lookup_response(matches, 'complete')
            if response:
                return response
            task = matches[0]
        complete_task(task)
        return f'Done: #{task.id} {task.title}'

    if _is_cancel_all_request(text):
        count = cancel_all_open_tasks()
        if count == 0:
            return 'No open tasks to remove.'
        return f'Removed {count} open task{"s" if count != 1 else ""}.'

    if lower.startswith('/cancel') or lower.startswith('/delete') or lower.startswith('/remove') or lower.startswith('cancel ') or lower.startswith('delete ') or lower.startswith('remove ') or lower.startswith('drop '):
        parts = text.split()
        if len(parts) < 2:
            return 'Usage: /cancel task_id or /cancel task title'
        if parts[1].isdigit():
            try:
                task = Task.objects.get(id=int(parts[1]))
            except Task.DoesNotExist:
                return 'Task not found.'
        else:
            query = _extract_action_query(text, '/cancel', ['cancel', 'delete', 'remove', 'drop'])
            matches = find_active_tasks(query)
            response = _lookup_response(matches, 'cancel')
            if response:
                return response
            task = matches[0]
        cancel_task(task)
        return f'Removed: #{task.id} {task.title}'

    if lower == '/briefing':
        return build_briefing()

    if lower == '/suggest':
        return build_ceo_suggestions()

    if lower == '/gitlab':
        return radar_summary()

    if lower == '/draft_followup':
        return build_followup_draft()

    if _looks_like_task(text):
        task = create_task_from_text(text)
        return 'Captured as task:\n' + format_task(task)

    return 'I did not create a task. Use /add for tasks, /tasks to list them, or /help for commands.'


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
