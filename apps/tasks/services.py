from datetime import timedelta
from dateutil.parser import parse
from django.utils import timezone
from apps.tasks.models import Task
from apps.reminders.models import Reminder
from apps.ai.ollama import generate_json

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


def guess_priority(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ['urgent', 'asap', 'critical', 'blocked', 'today']):
        return Task.Priority.URGENT
    if any(word in lower for word in ['important', 'high priority', 'client', 'deadline']):
        return Task.Priority.HIGH
    if any(word in lower for word in ['low priority', 'sometime', 'later']):
        return Task.Priority.LOW
    return Task.Priority.MEDIUM


def _strip_capture_prefix(text: str) -> str:
    clean = text.replace('/add', '', 1).strip()
    if clean.lower().startswith('remind me to '):
        clean = clean[13:].strip()
    return clean


def extract_task_details(text: str) -> dict:
    clean = _strip_capture_prefix(text)
    today = timezone.localdate().isoformat()
    prompt = f"""
Extract one CEO assistant task from this message.
Today is {today}. Return only JSON with these keys:
title, description, category, priority, owner_name, due_date.

Allowed category values: CEO, ENGINEERING, HR, FINANCE, SALES, CLIENT, PERSONAL.
Allowed priority values: LOW, MEDIUM, HIGH, URGENT.
due_date must be ISO 8601 with timezone when present, otherwise null.
owner_name defaults to Nour unless another owner is explicit.

Message: {clean}
"""
    ai = generate_json(prompt, timeout=5)
    parsed_due = parse_due_date(clean)
    due = None
    if ai.get('due_date'):
        try:
            due = parse(ai['due_date'])
            if timezone.is_naive(due):
                due = timezone.make_aware(due, timezone.get_current_timezone())
        except Exception:
            due = None

    guessed_category = guess_category(clean)
    guessed_priority = guess_priority(clean)
    category = (
        guessed_category
        if guessed_category != Task.Category.CEO
        else ai.get('category') if ai.get('category') in Task.Category.values else guessed_category
    )
    priority = (
        guessed_priority
        if guessed_priority != Task.Priority.MEDIUM
        else ai.get('priority') if ai.get('priority') in Task.Priority.values else guessed_priority
    )
    ai_title = (ai.get('title') or '').strip()
    title = ai_title if len(ai_title.split()) >= 3 else clean
    return {
        'title': title[:255],
        'description': ai.get('description') or '',
        'category': category,
        'priority': priority,
        'owner_name': ai.get('owner_name') or 'Nour',
        'due_date': parsed_due if parsed_due else due,
    }


def create_task_from_text(text: str) -> Task:
    details = extract_task_details(text)
    task = Task.objects.create(
        title=details['title'],
        description=details['description'],
        category=details['category'],
        due_date=details['due_date'],
        priority=details['priority'],
        owner_name=details['owner_name'],
        source='telegram',
    )
    if details['due_date']:
        Reminder.objects.create(task=task, remind_at=details['due_date'])
    return task


def format_task(task: Task) -> str:
    due = task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'No due date'
    return f'#{task.id} [{task.status}] {task.title}\nCategory: {task.category} | Due: {due}'
