from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.tasks.models import Task
from apps.tasks.services import cancel_task, create_task_from_text, find_active_tasks, format_task


class HomeViewTests(TestCase):
    def test_homepage_renders_task_summary(self):
        Task.objects.create(title="Review client proposal")

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CEO Copilot MVP")
        self.assertContains(response, "Review client proposal")
        self.assertContains(response, "Open tasks")

    def test_health_endpoint(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})


class TaskCaptureTests(TestCase):
    @patch("apps.tasks.services.generate_json")
    def test_create_task_uses_ai_extraction_when_available(self, mocked_generate_json):
        due_date = timezone.now().replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
        mocked_generate_json.return_value = {
            "title": "Approve Hue integration direction",
            "description": "Engineering decision needed before implementation continues.",
            "category": "ENGINEERING",
            "priority": "HIGH",
            "owner_name": "Nour",
            "due_date": due_date,
        }

        task = create_task_from_text("/add decide Hue integration plan tomorrow")

        self.assertEqual(task.title, "Approve Hue integration direction")
        self.assertEqual(task.category, Task.Category.ENGINEERING)
        self.assertEqual(task.priority, Task.Priority.HIGH)
        self.assertEqual(task.owner_name, "Nour")
        self.assertEqual(task.reminders.count(), 1)

    @patch("apps.tasks.services.generate_json")
    def test_keyword_category_overrides_weak_ai_category(self, mocked_generate_json):
        wrong_ai_due_date = (timezone.now() + timezone.timedelta(days=2)).isoformat()
        mocked_generate_json.return_value = {
            "title": "urgent",
            "category": "PERSONAL",
            "priority": "MEDIUM",
            "owner_name": "Nour",
            "due_date": wrong_ai_due_date,
        }

        task = create_task_from_text("/add urgent client follow up with Sara tomorrow")

        self.assertEqual(task.category, Task.Category.CLIENT)
        self.assertEqual(task.priority, Task.Priority.URGENT)
        self.assertEqual(task.title, "urgent client follow up with Sara tomorrow")
        self.assertEqual(task.due_date.date(), (timezone.localdate() + timezone.timedelta(days=1)))

    def test_find_active_tasks_returns_clear_best_match(self):
        ahmed = Task.objects.create(title="Follow up with Ahmed tomorrow")
        Task.objects.create(title="Urgent client follow up")

        matches = find_active_tasks("Ahmed follow up")

        self.assertEqual(matches, [ahmed])

    def test_cancel_task_cancels_pending_reminders(self):
        task = Task.objects.create(title="Follow up with Ahmed tomorrow", due_date=timezone.now())
        reminder = task.reminders.create(remind_at=timezone.now())

        cancel_task(task)

        task.refresh_from_db()
        reminder.refresh_from_db()
        self.assertEqual(task.status, Task.Status.CANCELLED)
        self.assertEqual(reminder.status, "CANCELLED")

    def test_format_task_displays_local_time(self):
        due = timezone.datetime(2026, 6, 2, 7, 0, tzinfo=dt_timezone.utc)
        task = Task.objects.create(title="Clean trello board", due_date=due)

        self.assertIn("Due: 2026-06-02 10:00", format_task(task))
