from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.reminders.models import Reminder
from apps.reminders.tasks import send_due_reminders
from apps.tasks.models import Task


class ReminderTaskTests(TestCase):
    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    @patch("apps.reminders.tasks.send_message", return_value=False)
    def test_failed_telegram_delivery_keeps_reminder_pending(self, _mock_send):
        task = Task.objects.create(title="Follow up with client")
        reminder = Reminder.objects.create(task=task, remind_at=timezone.now())

        send_due_reminders()

        reminder.refresh_from_db()
        self.assertEqual(reminder.status, Reminder.Status.PENDING)
        self.assertIsNone(reminder.sent_at)

    @override_settings(TELEGRAM_ALLOWED_CHAT_ID="local-test")
    @patch("apps.reminders.tasks.send_message", return_value=True)
    def test_successful_telegram_delivery_marks_reminder_sent(self, _mock_send):
        task = Task.objects.create(title="Follow up with client")
        reminder = Reminder.objects.create(task=task, remind_at=timezone.now())

        send_due_reminders()

        reminder.refresh_from_db()
        self.assertEqual(reminder.status, Reminder.Status.SENT)
        self.assertIsNotNone(reminder.sent_at)
