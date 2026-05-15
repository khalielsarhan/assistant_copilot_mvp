from django.utils import timezone
from apps.tasks.models import Task
from apps.tasks.services import format_task
from apps.integrations.gitlab import radar_summary
from apps.ai.ollama import generate


def build_briefing() -> str:
    now = timezone.now()
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    open_tasks = Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING]).order_by('due_date', '-priority')
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
