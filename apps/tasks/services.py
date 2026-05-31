import re
from datetime import timedelta
from dateutil.parser import parse
from django.utils import timezone
from apps.tasks.models import Project, Task
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
    now = timezone.localtime()
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
    clean = re.sub(r'\s+for\s+project\s+[a-zA-Z0-9][a-zA-Z0-9_-]*', ' ', clean, flags=re.IGNORECASE)
    project = extract_project_reference(clean)
    if project:
        clean = re.sub(rf'\s+for\s+{re.escape(project.name)}\b', ' ', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bremind\s+me\b.*$', ' ', clean, flags=re.IGNORECASE)
    clean = ' '.join(clean.split())
    return clean


def extract_task_details(text: str) -> dict:
    clean = _strip_capture_prefix(text)
    if not clean:
        clean = 'Untitled task'
    today = timezone.localdate().isoformat()
    prompt = f"""
Extract one CEO assistant task from this message.
Today is {today}. Return only JSON with these keys:
title, description, category, priority, owner_name, due_date.

Allowed category values: CEO, ENGINEERING, HR, FINANCE, SALES, CLIENT, PERSONAL.
Allowed priority values: LOW, MEDIUM, HIGH, URGENT.
due_date must be ISO 8601 with timezone when present, otherwise null.
owner_name defaults to Nour unless another owner is explicit.
Do not include command words like /add, "remind me", project names, or due dates in the title.
The title should be a short action phrase.

Message: {clean}
"""
    ai = generate_json(prompt, timeout=5)
    parsed_due = parse_due_date(text)
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
    if not title.strip():
        title = clean
    return {
        'title': title[:255],
        'description': ai.get('description') or '',
        'category': category,
        'priority': priority,
        'owner_name': ai.get('owner_name') or 'Nour',
        'due_date': parsed_due if parsed_due else due,
    }


def extract_project_reference(text: str) -> Project | None:
    match = re.search(r'\bfor\s+project\s+([a-zA-Z0-9][a-zA-Z0-9_-]*)', text, flags=re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        try:
            return Project.objects.get(name__iexact=name)
        except Project.DoesNotExist:
            return None

    for project in Project.objects.all():
        if re.search(rf'\bfor\s+{re.escape(project.name)}\b', text, flags=re.IGNORECASE):
            return project
    return None


def create_task_from_text(text: str) -> Task:
    details = extract_task_details(text)
    project = extract_project_reference(text)
    task = Task.objects.create(
        title=details['title'],
        description=details['description'],
        category=details['category'],
        due_date=details['due_date'],
        priority=details['priority'],
        owner_name=details['owner_name'],
        project=project,
        source='telegram',
    )
    if details['due_date']:
        Reminder.objects.create(task=task, remind_at=details['due_date'])
    return task


def format_task(task: Task) -> str:
    due = task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'No due date'
    project = f' | Project: {task.project.name}' if task.project else ''
    return f'#{task.id} [{task.status}] {task.title}\nCategory: {task.category}{project} | Due: {due}'


def extract_project_name(text: str) -> str:
    patterns = [
        r'\bproject\s+(?:called|named)\s+([a-zA-Z0-9][a-zA-Z0-9_-]*)',
        r'\bfolder\s+(?:called|named|for)\s+([a-zA-Z0-9][a-zA-Z0-9_-]*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ''


def create_project_from_text(text: str) -> tuple[Project | None, bool]:
    name = extract_project_name(text)
    if not name:
        return None, False
    project, created = Project.objects.get_or_create(
        name=name,
        defaults={'owner_name': 'Nour'},
    )
    return project, created


def format_project(project: Project) -> str:
    active_count = project.tasks.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING]).count()
    return f'#{project.id} {project.name} [{project.status}] Health: {project.health} | Open tasks: {active_count}'


def list_projects(limit: int = 10) -> str:
    projects = Project.objects.order_by('-updated_at')[:limit]
    return '\n'.join(format_project(project) for project in projects) or 'No projects yet.'


def attach_project_to_task(task: Task, project: Project) -> Task:
    task.project = project
    task.save(update_fields=['project', 'updated_at'])
    return task


def extract_task_id(text: str) -> int | None:
    match = re.search(r'(?:task\s*#?|#)\s*(\d+)\b', text, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def parse_reminder_date(text: str, task_id: int):
    cleaned = re.sub(rf'(?:task\s*#?|#)\s*{task_id}\b', ' ', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(add|set|create|a|the|reminder|for|to|on|task|can|you|please)\b', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = ' '.join(cleaned.split())
    return parse_due_date(cleaned) if cleaned else None


def add_reminder_for_task_from_text(text: str) -> tuple[Reminder | None, str]:
    task_id = extract_task_id(text)
    if not task_id:
        return None, 'Which task should I remind you about? Example: add reminder for task 15 tomorrow 10am'
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return None, f'Task #{task_id} was not found.'
    if task.status not in [Task.Status.OPEN, Task.Status.WAITING]:
        return None, f'Task #{task.id} is {task.status.lower()}, so I did not add a reminder.'

    remind_at = parse_reminder_date(text, task_id)
    if not remind_at:
        return None, f'When should I remind you about task #{task.id}? Example: add reminder for task {task.id} tomorrow 10am'

    reminder = Reminder.objects.create(task=task, remind_at=remind_at)
    return reminder, f'Reminder added for task #{task.id}: {task.title}\nAt: {remind_at.strftime("%Y-%m-%d %H:%M")}'


def _matches_query(title: str, query: str) -> bool:
    normalized_title = _normalize_lookup_text(title)
    normalized_query = _normalize_lookup_text(query)
    tokens = _lookup_tokens(normalized_query)
    if not tokens:
        return False
    if normalized_query and normalized_query in normalized_title:
        return True
    return tokens <= set(normalized_title.split())


def cancel_pending_reminders(except_query: str = '') -> int:
    pending = Reminder.objects.filter(status=Reminder.Status.PENDING).select_related('task')
    count = 0
    for reminder in pending:
        if except_query and _matches_query(reminder.task.title, except_query):
            continue
        reminder.status = Reminder.Status.CANCELLED
        reminder.save(update_fields=['status'])
        count += 1
    return count


def _normalize_lookup_text(text: str) -> str:
    lower = text.lower().strip()
    for phrase in [
        'please',
        'the task',
        'task',
        'reminder',
        'remind me to',
        'follow-up',
    ]:
        lower = lower.replace(phrase, ' ')
    for char in '#,.:;!?':
        lower = lower.replace(char, ' ')
    return ' '.join(lower.split())


def _lookup_tokens(text: str) -> set[str]:
    stop_words = {
        'a', 'an', 'and', 'for', 'me', 'my', 'of', 'on', 'the', 'to', 'with',
        'follow', 'up', 'followup',
        'remove', 'delete', 'cancel', 'drop', 'done', 'complete', 'finish',
        'finished', 'mark', 'as',
    }
    return {word for word in _normalize_lookup_text(text).split() if word not in stop_words}


def find_active_tasks(query: str, limit: int = 5):
    query = _normalize_lookup_text(query)
    tokens = _lookup_tokens(query)
    if not tokens:
        return []

    active = Task.objects.filter(
        status__in=[Task.Status.OPEN, Task.Status.WAITING],
    ).order_by('due_date', '-updated_at')

    matches = []
    for task in active:
        title = _normalize_lookup_text(task.title)
        title_tokens = set(title.split())
        if query and query in title:
            score = 100 + len(query)
        else:
            overlap = tokens & title_tokens
            if not overlap:
                continue
            score = len(overlap) * 10
            if tokens <= title_tokens:
                score += 25
        matches.append((score, task))

    matches.sort(key=lambda item: item[0], reverse=True)
    if not matches:
        return []
    if len(matches) == 1 or matches[0][0] > matches[1][0]:
        return [matches[0][1]]
    top_score = matches[0][0]
    return [task for score, task in matches[:limit] if score == top_score]


def cancel_task(task: Task) -> Task:
    task.status = Task.Status.CANCELLED
    task.save(update_fields=['status', 'updated_at'])
    task.reminders.filter(status=Reminder.Status.PENDING).update(status=Reminder.Status.CANCELLED)
    return task


def complete_task(task: Task) -> Task:
    task.status = Task.Status.DONE
    task.save(update_fields=['status', 'updated_at'])
    task.reminders.filter(status=Reminder.Status.PENDING).update(status=Reminder.Status.CANCELLED)
    return task


def cancel_all_open_tasks() -> int:
    tasks = Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING])
    task_ids = list(tasks.values_list('id', flat=True))
    if not task_ids:
        return 0
    count = tasks.update(status=Task.Status.CANCELLED)
    Reminder.objects.filter(
        task_id__in=task_ids,
        status=Reminder.Status.PENDING,
    ).update(status=Reminder.Status.CANCELLED)
    return count
