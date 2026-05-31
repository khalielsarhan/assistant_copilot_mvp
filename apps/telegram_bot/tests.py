import json
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.telegram_bot.client import get_updates, send_message
from apps.reminders.models import Reminder
from apps.tasks.models import Project, Task


class TelegramClientTests(SimpleTestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="token")
    @patch("apps.telegram_bot.client.requests.post")
    @patch("apps.telegram_bot.client.logger.exception")
    def test_send_message_returns_false_when_telegram_rejects_request(self, _mock_logger, mock_post):
        response = Mock()
        response.raise_for_status.side_effect = requests.RequestException("bad request")
        mock_post.return_value = response

        self.assertFalse(send_message("chat-id", "hello"))

    @override_settings(TELEGRAM_BOT_TOKEN="token")
    @patch("apps.telegram_bot.client.requests.get")
    def test_get_updates_returns_result_list(self, mock_get):
        response = Mock()
        response.json.return_value = {"ok": True, "result": [{"update_id": 10}]}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        self.assertEqual(get_updates(offset=9), [{"update_id": 10}])


@override_settings(TELEGRAM_BOT_TOKEN="replace-me")
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
    def test_clean_reminders_cancels_pending_reminders_not_tasks(self):
        task = Task.objects.create(title="Urgent client follow up")
        Reminder.objects.create(task=task, remind_at=timezone.now())
        payload = {"message": {"chat": {"id": "local-test"}, "text": "Clean the reminders"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        task.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Cleaned 1 pending reminder", response.json()["reply"])
        self.assertEqual(task.status, Task.Status.OPEN)
        self.assertEqual(Reminder.objects.filter(status=Reminder.Status.PENDING).count(), 0)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_clean_reminders_except_query_keeps_matching_reminder(self):
        steering = Task.objects.create(title="Preparation of Steering Deck")
        other = Task.objects.create(title="Urgent client follow up")
        Reminder.objects.create(task=steering, remind_at=timezone.now())
        Reminder.objects.create(task=other, remind_at=timezone.now())
        payload = {"message": {"chat": {"id": "local-test"}, "text": "Clean up reminders except for steering deck"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Cleaned 1 pending reminder", response.json()["reply"])
        self.assertEqual(Reminder.objects.filter(status=Reminder.Status.PENDING).get().task, steering)

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
    @patch("apps.tasks.services.generate_json", return_value={})
    def test_add_task_can_attach_to_project_with_short_for_name(self, mocked_generate_json):
        project = Project.objects.create(name="IOLO")
        payload = {
            "message": {
                "chat": {"id": "local-test"},
                "text": "/add clean trello board for IOLO remind me tomorrow 10:00 am",
            }
        }

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        task = Task.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(task.project, project)
        self.assertEqual(task.title, "clean trello board")
        self.assertEqual(task.due_date.date(), timezone.localdate() + timezone.timedelta(days=1))
        self.assertIn("Project: IOLO", response.json()["reply"])

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    @patch("apps.tasks.services.generate_json", return_value={})
    def test_multiline_add_commands_create_multiple_tasks(self, mocked_generate_json):
        Project.objects.create(name="IOLO")
        payload = {
            "message": {
                "chat": {"id": "local-test"},
                "text": "/add clean trello board for IOLO remind me tomorrow 10:00 am\n/add brief the team remind me tomorrow 10:00 am",
            }
        }

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), 2)
        self.assertTrue(Task.objects.filter(title="clean trello board", project__name="IOLO").exists())
        self.assertTrue(Task.objects.filter(title="brief the team").exists())
        self.assertEqual(response.json()["reply"].count("Created task:"), 2)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    @patch("apps.tasks.services.generate_json", return_value={})
    def test_project_request_with_numbered_items_creates_project_tasks(self, mocked_generate_json):
        payload = {
            "message": {
                "chat": {"id": "local-test"},
                "text": "I have a project called IOLO and I want to do some work on\n1. Clean the trello board\n2. after vacation briefing",
            }
        }

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Project.objects.filter(name="IOLO").count(), 1)
        self.assertEqual(Task.objects.filter(project__name="IOLO").count(), 2)
        self.assertIn("Created 2 tasks", response.json()["reply"])

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_project_tomorrow_question_lists_tasks_instead_of_creating_task(self):
        project = Project.objects.create(name="IOLO")
        due = (timezone.localtime() + timezone.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        Task.objects.create(title="Clean trello board", project=project, due_date=due)
        Task.objects.create(title="Unrelated task", due_date=due)
        payload = {"message": {"chat": {"id": "local-test"}, "text": "What do we have regarding IOLO for tomorrow?"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Open tasks for IOLO tomorrow", response.json()["reply"])
        self.assertIn("Clean trello board", response.json()["reply"])
        self.assertNotIn("Unrelated task", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 2)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    def test_edited_message_is_ignored_to_avoid_duplicate_capture(self):
        payload = {"edited_message": {"chat": {"id": "local-test"}, "text": "What do we have regarding IOLO for tomorrow?"}}

        response = self.client.post(
            reverse("telegram_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Ignored edited message", response.json()["reply"])
        self.assertEqual(Task.objects.count(), 0)

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
