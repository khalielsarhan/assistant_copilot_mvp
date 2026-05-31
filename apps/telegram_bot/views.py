import json
import re
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from apps.telegram_bot.client import send_message
from apps.tasks.models import Project, Task
from apps.tasks.services import (
    add_reminder_for_task_from_text,
    cancel_all_open_tasks,
    cancel_pending_reminders,
    cancel_task,
    complete_task,
    create_project_from_text,
    create_task_from_text,
    find_active_tasks,
    format_task,
    list_projects,
    parse_due_date,
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
/projects
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
    if _is_question(text):
        return False
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


def _is_question(text: str) -> bool:
    lower = text.lower().strip()
    question_starts = (
        'what ', 'what\'s ', 'whats ', 'which ', 'who ', 'when ', 'where ', 'why ', 'how ',
        'do we ', 'did we ', 'are there ', 'is there ', 'can you show ', 'show me ',
        'list ', 'give me ',
    )
    return lower.endswith('?') or lower.startswith(question_starts)


def _is_cancel_all_request(text: str) -> bool:
    lower = ' '.join(text.lower().replace('-', ' ').split())
    cancel_words = ['remove', 'delete', 'cancel', 'clear']
    target_phrases = ['all open tasks', 'all tasks', 'everything']
    return any(lower.startswith(word) for word in cancel_words) and any(phrase in lower for phrase in target_phrases)


def _is_project_request(text: str) -> bool:
    lower = text.lower()
    return 'project' in lower and any(word in lower for word in ['called', 'named', 'folder'])


def _is_reminder_request(text: str) -> bool:
    lower = text.lower()
    return 'reminder' in lower and ('task' in lower or '#' in lower)


def _is_reminder_cleanup_request(text: str) -> bool:
    lower = ' '.join(text.lower().replace('-', ' ').split())
    cleanup_words = ['clean', 'clear', 'remove', 'delete', 'cancel']
    return any(lower.startswith(word) for word in cleanup_words) and 'reminder' in lower


def _extract_except_query(text: str) -> str:
    lower = text.lower()
    marker = ' except '
    if marker not in lower:
        return ''
    start = lower.index(marker) + len(marker)
    return text[start:].strip()


def _numbered_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        match = re.match(r'^\s*(?:[-*]|\d+[.)])\s+(.+?)\s*$', line)
        if match:
            item = match.group(1).strip()
            if item:
                items.append(item)
    return items


def _split_command_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    command_lines = [line for line in lines if line.startswith('/')]
    if len(command_lines) >= 2 and len(command_lines) == len(lines):
        return command_lines
    return []


def _format_created_tasks(tasks: list[Task]) -> str:
    return '\n\n'.join(format_task(task) for task in tasks)


def _extract_project_from_query(text: str) -> Project | None:
    lower = text.lower()
    for project in Project.objects.all():
        if re.search(rf'\b{re.escape(project.name.lower())}\b', lower):
            return project
    return None


def _date_window_from_query(text: str):
    lower = text.lower()
    now = timezone.localtime()
    if 'tomorrow' in lower:
        start = (now + timezone.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
        label = 'tomorrow'
        return start, end, label
    if 'today' in lower:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        label = 'today'
        return start, end, label
    due = parse_due_date(text)
    if due:
        due = timezone.localtime(due)
        start = due.replace(hour=0, minute=0, second=0, microsecond=0)
        end = due.replace(hour=23, minute=59, second=59, microsecond=999999)
        label = due.strftime('%Y-%m-%d')
        return start, end, label
    return None, None, ''


def _is_status_query(text: str) -> bool:
    lower = text.lower()
    status_markers = [
        'what do we have',
        'what have we got',
        'what is pending',
        'what\'s pending',
        'whats pending',
        'show me',
        'list',
        'give me',
        'regarding',
        'for tomorrow',
        'for today',
    ]
    return _is_question(text) and any(marker in lower for marker in status_markers)


def _answer_status_query(text: str) -> str:
    project = _extract_project_from_query(text)
    start, end, date_label = _date_window_from_query(text)
    qs = Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING])
    scope = []
    if project:
        qs = qs.filter(project=project)
        scope.append(project.name)
    if start and end:
        qs = qs.filter(due_date__gte=start, due_date__lte=end)
        scope.append(date_label)
    qs = qs.order_by('due_date', '-updated_at')[:10]

    heading = ' '.join(scope) if scope else 'open tasks'
    if not qs:
        return f'No open tasks found for {heading}.'
    return f'Open tasks for {heading}:\n\n' + '\n\n'.join(format_task(task) for task in qs)


def handle_message(chat_id: str, text: str) -> str:
    text = (text or '').strip()
    lower = text.lower()
    if not text:
        return 'Send /help to see commands, or /add followed by a task.'

    command_lines = _split_command_lines(text)
    if command_lines:
        replies = [handle_message(chat_id, line) for line in command_lines]
        return '\n\n'.join(replies)

    if lower in ['/start', '/help']:
        return HELP
    if _is_greeting(text):
        return 'Hi. Send /help for commands, or /add followed by a task.'

    if _is_status_query(text):
        return _answer_status_query(text)

    if lower == '/projects':
        return list_projects()

    if _is_project_request(text):
        project, created = create_project_from_text(text)
        if not project:
            return 'What is the project name? Example: create project called IOLO'
        items = _numbered_items(text)
        if items:
            tasks = [create_task_from_text(f'/add {item} for project {project.name}') for item in items]
            action = 'Created' if created else 'Found existing'
            return (
                f'{action} project folder: {project.name}\n'
                f'Created {len(tasks)} task{"s" if len(tasks) != 1 else ""}:\n\n'
                f'{_format_created_tasks(tasks)}'
            )
        action = 'Created' if created else 'Found existing'
        return (
            f'{action} project folder: {project.name}\n'
            f'Use: /add task title for project {project.name} tomorrow\n'
            f'Use: add reminder for task TASK_ID tomorrow 10am'
        )

    if _is_reminder_request(text):
        reminder, response = add_reminder_for_task_from_text(text)
        return response

    if _is_reminder_cleanup_request(text):
        except_query = _extract_except_query(text)
        count = cancel_pending_reminders(except_query=except_query)
        if count == 0:
            return 'No pending reminders to clean.'
        if except_query:
            return f'Cleaned {count} pending reminder{"s" if count != 1 else ""}. Kept reminders matching: {except_query}'
        return f'Cleaned {count} pending reminder{"s" if count != 1 else ""}.'

    if lower.startswith('/add') or lower.startswith('remind me to'):
        if text == '/add':
            return 'Usage: /add Follow up with Ahmed tomorrow'
        task = create_task_from_text(text)
        return 'Created task:\n' + format_task(task)

    if lower == '/tasks':
        qs = Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING]).order_by('due_date', '-updated_at')[:10]
        return '\n\n'.join(format_task(t) for t in qs) or 'No open tasks.'

    if lower == '/today':
        now = timezone.now()
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        qs = Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING], due_date__lte=end).order_by('due_date')[:10]
        return '\n\n'.join(format_task(t) for t in qs) or 'No tasks due today.'

    if lower == '/overdue':
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
    if 'edited_message' in payload and 'message' not in payload:
        return JsonResponse({'ok': True, 'reply': 'Ignored edited message.'})
    message = payload.get('message') or {}
    chat = message.get('chat') or {}
    chat_id = str(chat.get('id', ''))
    if not _authorized(chat_id):
        return HttpResponseForbidden('Unauthorized chat')
    text = message.get('text', '')
    reply = handle_message(chat_id, text)
    send_message(chat_id, reply[:3900])
    return JsonResponse({'ok': True, 'reply': reply})
