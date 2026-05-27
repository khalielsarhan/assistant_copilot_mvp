from django.utils import timezone
from apps.tasks.models import Task
from apps.tasks.services import format_task
from apps.integrations.gitlab import radar_summary
from apps.ai.ollama import generate


def _active_tasks():
    return Task.objects.filter(
        status__in=[Task.Status.OPEN, Task.Status.WAITING],
    ).order_by('due_date', '-priority', '-updated_at')


def build_briefing() -> str:
    now = timezone.now()
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    open_tasks = _active_tasks()
    overdue = [t for t in open_tasks if t.is_overdue()]
    today = open_tasks.filter(due_date__lte=today_end)[:10]
    gitlab = radar_summary()

    raw = []
    raw.append(f'Date: {now.date()}')
    raw.append(f'Overdue tasks: {len(overdue)}')
    raw.extend(format_task(t) for t in overdue[:5])
    raw.append(f'Tasks due today: {today.count()}')
    raw.extend(format_task(t) for t in today[:5])
    raw.append('GitLab radar:')
    raw.append(gitlab)

    prompt = 'Create a concise CEO morning briefing from this data. Use sections: Top Risks, Today, Follow-ups, GitLab.\n\n' + '\n'.join(raw)
    ai = generate(prompt)
    if ai.startswith('AI unavailable'):
        return '\n'.join(raw)
    return ai


def build_ceo_suggestions() -> str:
    now = timezone.now()
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    active = _active_tasks()
    overdue = [t for t in active if t.is_overdue()]
    due_today = active.filter(due_date__lte=today_end)[:10]
    high_priority = active.filter(priority__in=[Task.Priority.HIGH, Task.Priority.URGENT])[:10]
    waiting = active.filter(status=Task.Status.WAITING)[:10]

    raw = [
        f'Date: {now.date()}',
        f'Overdue count: {len(overdue)}',
        f'Due today count: {due_today.count()}',
        f'High priority count: {high_priority.count()}',
        f'Waiting count: {waiting.count()}',
        'Overdue tasks:',
        *(format_task(t) for t in overdue[:8]),
        'High priority tasks:',
        *(format_task(t) for t in high_priority[:8]),
        'Waiting tasks:',
        *(format_task(t) for t in waiting[:8]),
        'GitLab radar:',
        radar_summary(),
    ]
    prompt = """
You are a CEO chief-of-staff assistant. Based on the data below, suggest the next actions.
Return a concise list with:
1. The top 3 decisions or follow-ups the CEO should handle today.
2. Delegation suggestions.
3. Risks that need escalation.
4. Draft wording for one follow-up message if useful.
Keep it practical and approval-first. Do not invent facts.

Data:
""" + '\n'.join(raw)
    ai = generate(prompt)
    if ai.startswith('AI unavailable'):
        return '\n'.join(raw)
    return ai
