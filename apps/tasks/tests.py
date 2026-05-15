from django.test import TestCase
from django.urls import reverse

from apps.tasks.models import Task


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
