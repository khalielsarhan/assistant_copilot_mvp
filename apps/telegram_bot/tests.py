import json

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.tasks.models import Task


class TelegramWebhookTests(TestCase):
    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test", TELEGRAM_BOT_TOKEN="replace-me")
    def test_webhook_creates_task_and_returns_reply(self):
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
