from django.utils import timezone
from apps.tasks.models import Task
from apps.tasks.services import format_task
from apps.integrations.gitlab import radar_summary
from apps.ai.ollama import generate


def _looks_unusable_ai_reply(text: str) -> bool:
    lower = (text or '').lower()
    if not text or len(text.strip()) < 20:
        return True
    unsafe_markers = ['[date', '[location', '[specific', '[your name]', 'at a meeting', 'gmt']
    if any(marker in lower for marker in unsafe_markers):
        return True
    return lower.strip() in ['no items.', 'no items']


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

    prompt = (
        'Create a concise CEO morning briefing from this data only. '
        'Do not invent meetings, projects, people, tools, metrics, or dates. '
        'If a section has no data, say "No items." '
        'Use sections: Top Risks, Today, Follow-ups, GitLab.\n\n'
        + '\n'.join(raw)
    )
    ai = generate(prompt)
    if ai.startswith('AI unavailable') or _looks_unusable_ai_reply(ai):
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
You are a CEO chief-of-staff assistant. Based only on the data below, suggest the next actions.
Do not invent meetings, clients, tools, projects, people, deadlines, or task details.
Refer to real tasks by their shown task ID and title.
If GitLab is not configured, only suggest configuring the GitLab token; do not describe GitLab risks.
Return a concise list with:
1. The top 3 decisions or follow-ups the CEO should handle today.
2. Delegation suggestions.
3. Risks that need escalation.
4. Draft wording for one follow-up message if useful, using only the listed overdue or high-priority tasks.
Keep it practical and approval-first. Do not invent facts.

Data:
""" + '\n'.join(raw)
    ai = generate(prompt)
    if ai.startswith('AI unavailable') or _looks_unusable_ai_reply(ai):
        return '\n'.join(raw)
    return ai


def build_followup_draft() -> str:
    overdue = [
        format_task(t)
        for t in Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING])
        if t.is_overdue()
    ]
    if not overdue:
        return 'No overdue tasks to follow up on.'

    prompt = (
        'Draft a short professional follow-up message for these overdue tasks. '
        'Ask for status, blockers, and expected completion date. Do not be aggressive.\n\n'
        + '\n'.join(overdue[:10])
    )
    ai = generate(prompt)
    if not ai.startswith('AI unavailable') and not _looks_unusable_ai_reply(ai):
        return ai

    return (
        'Hi team, quick follow-up on the pending overdue items below.\n'
        'Please send me a short update today with current status, blockers, and expected completion date.\n\n'
        + '\n\n'.join(overdue[:10])
    )
