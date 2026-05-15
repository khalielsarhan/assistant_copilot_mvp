from datetime import timedelta
from dateutil.parser import parse
from django.utils import timezone
from apps.tasks.models import Task
from apps.reminders.models import Reminder

KEYWORDS = {
    'engineering': Task.Category.ENGINEERING,
    'gitlab': Task.Category.ENGINEERING,
    'client': Task.Category.CLIENT,
    'invoice': Task.Category.FINANCE,
    'payment': Task.Category.FINANCE,
    'contract': Task.Category.HR,
    'hiring': Task.Category.HR,
    'sales': Task.Category.SALES,
}


def guess_category(text: str) -> str:
    lower = text.lower()
    for key, category in KEYWORDS.items():
        if key in lower:
            return category
    return Task.Category.CEO


def parse_due_date(text: str):
    now = timezone.now()
    lower = text.lower()
    if 'tomorrow' in lower:
        return (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    if 'today' in lower:
        return now.replace(hour=18, minute=0, second=0, microsecond=0)
    if 'next week' in lower:
        return (now + timedelta(days=7)).replace(hour=10, minute=0, second=0, microsecond=0)
    try:
        dt = parse(text, fuzzy=True)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return None


def create_task_from_text(text: str) -> Task:
    clean = text.replace('/add', '', 1).strip()
    if clean.lower().startswith('remind me to '):
        clean = clean[13:].strip()
    due = parse_due_date(clean)
    task = Task.objects.create(
        title=clean[:255],
        category=guess_category(clean),
        due_date=due,
        priority=Task.Priority.MEDIUM,
        owner_name='Nour',
        source='telegram',
    )
    if due:
        Reminder.objects.create(task=task, remind_at=due)
    return task


def format_task(task: Task) -> str:
    due = task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'No due date'
    return f'#{task.id} [{task.status}] {task.title}\nCategory: {task.category} | Due: {due}'
