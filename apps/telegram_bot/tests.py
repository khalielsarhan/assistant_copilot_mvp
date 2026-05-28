import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.reminders.models import Reminder
from apps.tasks.models import Project, Task


class TelegramWebhookTests(TestCase):
    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test", TELEGRAM_BOT_TOKEN="replace-me")
    @patch("apps.tasks.services.generate_json", return_value={})
    def test_webhook_creates_task_and_returns_reply(self, mocked_generate_json):
        payload = {
            "message": {
                "chat": {"id": "local-test"},
                "text": "/add Follow up with Ahmed tomorrow",
            }
        }

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertIn("Created task", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 1)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_webhook_rejects_unknown_chat(self):
        payload = {"message": {"chat": {"id": "wrong-chat"}, "text": "/tasks"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    @patch("apps.telegram_bot.views.build_ceo_suggestions", return_value="Top action: follow up with client.")
    def test_suggest_command_returns_ai_suggestions(self, mocked_suggestions):
        payload = {"message": {"chat": {"id": "local-test"}, "text": "/suggest"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Top action", response.json()["reply"])
        mocked_suggestions.assert_called_once()

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    @patch("apps.telegram_bot.views.build_followup_draft", return_value="Hi team, quick follow-up.")
    def test_draft_followup_command_returns_draft(self, mocked_draft):
        payload = {"message": {"chat": {"id": "local-test"}, "text": "/draft_followup"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("quick follow-up", response.json()["reply"])
        mocked_draft.assert_called_once()

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_natural_language_remove_cancels_matching_task(self):
        task = Task.objects.create(title="Follow up with Ahmed tomorrow")
        Task.objects.create(title="Urgent client follow up")
        payload = {"message": {"chat": {"id": "local-test"}, "text": "Remove follow up with ahmed"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        task.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"Removed: #{task.id}", response.json()["reply"])
        self.assertEqual(task.status, Task.Status.CANCELLED)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_remove_does_not_match_generic_follow_up_tasks_when_name_missing(self):
        Task.objects.create(title="Urgent client follow up")
        payload = {"message": {"chat": {"id": "local-test"}, "text": "Remove follow up with ahmed"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("could not find", response.json()["reply"])
        self.assertEqual(Task.objects.filter(status=Task.Status.OPEN).count(), 1)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_remove_all_open_tasks_cancels_every_open_task(self):
        Task.objects.create(title="Urgent client follow up")
        Task.objects.create(title="Review Hue integration", status=Task.Status.WAITING)
        Task.objects.create(title="Already done", status=Task.Status.DONE)
        payload = {"message": {"chat": {"id": "local-test"}, "text": "Remove all open tasks"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Removed 2 open tasks", response.json()["reply"])
        self.assertEqual(Task.objects.filter(status__in=[Task.Status.OPEN, Task.Status.WAITING]).count(), 0)
        self.assertEqual(Task.objects.filter(status=Task.Status.DONE).count(), 1)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_remove_all_open_tasks_when_empty(self):
        payload = {"message": {"chat": {"id": "local-test"}, "text": "Remove all open tasks"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("No open tasks", response.json()["reply"])

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_project_request_creates_project_not_task(self):
        payload = {
            "message": {
                "chat": {"id": "local-test"},
                "text": "I have a project called IOLO i want you to create a folder for it and attach tasks to it and reminders",
            }
        }

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Created project folder: IOLO", response.json()["reply"])
        self.assertEqual(Project.objects.filter(name="IOLO").count(), 1)
        self.assertEqual(Task.objects.count(), 0)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_reminder_request_without_due_date_asks_when(self):
        task = Task.objects.create(title="Create IOLO task folder")
        payload = {"message": {"chat": {"id": "local-test"}, "text": f"Can you add a reminder for task {task.id}"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("When should I remind you", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Reminder.objects.count(), 0)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_reminder_request_with_due_date_creates_reminder_not_task(self):
        task = Task.objects.create(title="Create IOLO task folder")
        payload = {"message": {"chat": {"id": "local-test"}, "text": f"add reminder for task {task.id} tomorrow"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(f"Reminder added for task #{task.id}", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Reminder.objects.count(), 1)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    @patch("apps.tasks.services.generate_json", return_value={})
    def test_add_task_can_attach_to_project(self, mocked_generate_json):
        project = Project.objects.create(name="IOLO")
        payload = {"message": {"chat": {"id": "local-test"}, "text": "/add prepare kickoff for project IOLO tomorrow"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        task = Task.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(task.project, project)
        self.assertEqual(task.title, "prepare kickoff tomorrow")
        self.assertIn("Project: IOLO", response.json()["reply"])

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_done_command_can_match_title(self):
        task = Task.objects.create(title="Review Hue integration direction")
        payload = {"message": {"chat": {"id": "local-test"}, "text": "/done Hue integration"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        task.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"Done: #{task.id}", response.json()["reply"])
        self.assertEqual(task.status, Task.Status.DONE)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_empty_message_does_not_create_task(self):
        payload = {"message": {"chat": {"id": "local-test"}, "text": ""}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("/help", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 0)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_greeting_does_not_create_task(self):
        payload = {"message": {"chat": {"id": "local-test"}, "text": "Hi"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("/help", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 0)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_random_text_does_not_create_task(self):
        payload = {"message": {"chat": {"id": "local-test"}, "text": "how are you"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("did not create", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 0)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_add_without_text_returns_usage(self):
        payload = {"message": {"chat": {"id": "local-test"}, "text": "/add"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Usage", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 0)
