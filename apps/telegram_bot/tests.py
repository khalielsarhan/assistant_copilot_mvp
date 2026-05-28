import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.tasks.models import Task


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
        payload = {"message": {"chat": {"id": "local-test"}, "text": "remove the Ahmed follow up task"}}

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
